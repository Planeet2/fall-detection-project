import json
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Optional
from uuid import uuid4

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

from app.config import DATABASE_URL, DETECTIONS_LOG_FILE, LOG_DIR


os.makedirs(LOG_DIR, exist_ok=True)


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS detections (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    status TEXT,
    is_fall BOOLEAN,
    risk_level TEXT,
    fall_probability DOUBLE PRECISION,
    fall_probability_percent DOUBLE PRECISION,
    label TEXT,
    message TEXT,
    frames_processed INTEGER,
    windows_analyzed INTEGER,
    agent_decision TEXT,
    agent_next_action TEXT
);
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_detections_created_at
ON detections (created_at DESC);
"""

COLUMNS = [
    "id",
    "filename",
    "created_at",
    "status",
    "is_fall",
    "risk_level",
    "fall_probability",
    "fall_probability_percent",
    "label",
    "message",
    "frames_processed",
    "windows_analyzed",
    "agent_decision",
    "agent_next_action",
]


class StorageUnavailable(RuntimeError):
    pass


connection_pool: Optional[SimpleConnectionPool] = None
storage_initialized = False
last_storage_error: Optional[str] = None


def _storage_error(exc: Exception) -> StorageUnavailable:
    global last_storage_error
    last_storage_error = str(exc)
    return StorageUnavailable("Detection storage is unavailable. Check PostgreSQL connection.")


def _get_connection_pool() -> SimpleConnectionPool:
    global connection_pool

    if connection_pool is not None:
        return connection_pool

    try:
        connection_pool = SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            dsn=DATABASE_URL,
        )
    except psycopg2.Error as exc:
        raise _storage_error(exc) from exc

    return connection_pool


@contextmanager
def get_connection():
    pool = _get_connection_pool()
    connection = None

    try:
        connection = pool.getconn()
        yield connection
    except psycopg2.Error as exc:
        raise _storage_error(exc) from exc
    finally:
        if connection is not None:
            pool.putconn(connection)


def init_database():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_TABLE_SQL)
            cursor.execute(CREATE_INDEX_SQL)
        connection.commit()


def initialize_storage():
    global storage_initialized, last_storage_error

    if storage_initialized:
        return

    init_database()
    migrate_json_logs_to_postgres()

    storage_initialized = True
    last_storage_error = None


def close_storage():
    global connection_pool, storage_initialized

    if connection_pool is not None:
        connection_pool.closeall()

    connection_pool = None
    storage_initialized = False


def check_storage_health():
    global last_storage_error

    try:
        initialize_storage()

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

        return {
            "ok": True,
            "error": None,
        }
    except StorageUnavailable as exc:
        return {
            "ok": False,
            "error": str(exc),
            "details": last_storage_error,
        }
    except Exception as exc:
        last_storage_error = str(exc)
        return {
            "ok": False,
            "error": "Detection storage health check failed.",
            "details": last_storage_error,
        }


def _format_created_at(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")

    return str(value)


def _row_to_dict(row):
    item = dict(row)
    item["created_at"] = _format_created_at(item.get("created_at"))
    return item


def _database_is_empty():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM detections")
            count = cursor.fetchone()[0]
            return count == 0


def _load_old_json_detections():
    if not os.path.exists(DETECTIONS_LOG_FILE):
        return []

    try:
        with open(DETECTIONS_LOG_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        return []

    if not isinstance(data, list):
        return []

    return data


def _parse_created_at(value):
    if not value:
        return datetime.now()

    if isinstance(value, datetime):
        return value

    for date_format in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(str(value), date_format)
        except ValueError:
            continue

    return datetime.now()


def migrate_json_logs_to_postgres():
    if not _database_is_empty():
        return

    old_detections = _load_old_json_detections()

    if not old_detections:
        return

    placeholders = ", ".join(["%s" for _ in COLUMNS])
    columns = ", ".join(COLUMNS)

    with get_connection() as connection:
        with connection.cursor() as cursor:
            for item in reversed(old_detections):
                record = {
                    "id": item.get("id") or str(uuid4()),
                    "filename": item.get("filename") or "unknown",
                    "created_at": _parse_created_at(item.get("created_at")),
                    "status": item.get("status"),
                    "is_fall": item.get("is_fall"),
                    "risk_level": item.get("risk_level"),
                    "fall_probability": item.get("fall_probability"),
                    "fall_probability_percent": item.get("fall_probability_percent"),
                    "label": item.get("label"),
                    "message": item.get("message"),
                    "frames_processed": item.get("frames_processed"),
                    "windows_analyzed": item.get("windows_analyzed"),
                    "agent_decision": item.get("agent_decision"),
                    "agent_next_action": item.get("agent_next_action"),
                }

                values = [record[column] for column in COLUMNS]

                cursor.execute(
                    f"INSERT INTO detections ({columns}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING",
                    values,
                )

        connection.commit()


def load_detections():
    initialize_storage()

    with get_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM detections
                ORDER BY created_at DESC, id DESC
                """
            )
            rows = cursor.fetchall()

    return [_row_to_dict(row) for row in rows]


def add_detection_log(original_filename, result):
    initialize_storage()

    detection_record = {
        "id": str(uuid4()),
        "filename": original_filename,
        "created_at": datetime.now(),
        "status": result.get("status"),
        "is_fall": result.get("is_fall"),
        "risk_level": result.get("risk_level"),
        "fall_probability": result.get("fall_probability"),
        "fall_probability_percent": result.get("fall_probability_percent"),
        "label": result.get("label"),
        "message": result.get("message"),
        "frames_processed": result.get("frames_processed"),
        "windows_analyzed": result.get("windows_analyzed"),
        "agent_decision": result.get("agent", {}).get("decision"),
        "agent_next_action": result.get("agent", {}).get("next_action"),
    }

    placeholders = ", ".join(["%s" for _ in COLUMNS])
    columns = ", ".join(COLUMNS)
    values = [detection_record[column] for column in COLUMNS]

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO detections ({columns}) VALUES ({placeholders})",
                values,
            )
        connection.commit()

    detection_record["created_at"] = _format_created_at(detection_record["created_at"])

    return detection_record


def clear_detection_logs():
    initialize_storage()

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM detections")
        connection.commit()
