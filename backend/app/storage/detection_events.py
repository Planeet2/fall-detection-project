from datetime import datetime, timezone
from uuid import uuid4

from psycopg2.extras import Json, RealDictCursor

from app.storage.detection_repository import get_connection, initialize_storage


CREATE_DETECTION_EVENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS detection_events (
    id TEXT PRIMARY KEY,
    status TEXT,
    is_fall BOOLEAN,
    confirmed_fall BOOLEAN,
    needs_manual_review BOOLEAN,
    risk_level TEXT,
    label TEXT,
    message TEXT,
    decision_reason TEXT,
    fall_probability DOUBLE PRECISION,
    fall_probability_percent DOUBLE PRECISION,
    mean_fall_probability DOUBLE PRECISION,
    mean_fall_probability_percent DOUBLE PRECISION,
    fall_window_count INTEGER,
    fall_window_ratio DOUBLE PRECISION,
    peak_fall_streak INTEGER,
    frames_processed INTEGER,
    reliable_pose_frames INTEGER,
    windows_analyzed INTEGER,
    pose_reliability_ratio DOUBLE PRECISION,
    agent JSONB,
    agent_result JSONB,
    upload_size_bytes BIGINT,
    source TEXT DEFAULT 'predict-video',
    elder_id TEXT,
    elder_snapshot JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
"""

ALTER_DETECTION_EVENTS_TABLE_SQL = """
ALTER TABLE detection_events
ADD COLUMN IF NOT EXISTS elder_snapshot JSONB;
"""

CREATE_DETECTION_EVENTS_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_detection_events_created_at
ON detection_events (created_at DESC);
"""

CREATE_DETECTION_EVENTS_STATUS_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_detection_events_status
ON detection_events (status);
"""

EVENT_COLUMNS = [
    "id",
    "status",
    "is_fall",
    "confirmed_fall",
    "needs_manual_review",
    "risk_level",
    "label",
    "message",
    "decision_reason",
    "fall_probability",
    "fall_probability_percent",
    "mean_fall_probability",
    "mean_fall_probability_percent",
    "fall_window_count",
    "fall_window_ratio",
    "peak_fall_streak",
    "frames_processed",
    "reliable_pose_frames",
    "windows_analyzed",
    "pose_reliability_ratio",
    "agent",
    "agent_result",
    "upload_size_bytes",
    "source",
    "elder_id",
    "elder_snapshot",
]

event_storage_initialized = False


def _format_created_at(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)

        return value.isoformat().replace("+00:00", "Z")

    return str(value)


def _row_to_dict(row):
    item = dict(row)
    item["created_at"] = _format_created_at(item.get("created_at"))
    return item


def initialize_detection_events_storage():
    global event_storage_initialized

    if event_storage_initialized:
        return

    initialize_storage()

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_DETECTION_EVENTS_TABLE_SQL)
            cursor.execute(ALTER_DETECTION_EVENTS_TABLE_SQL)
            cursor.execute(CREATE_DETECTION_EVENTS_INDEX_SQL)
            cursor.execute(CREATE_DETECTION_EVENTS_STATUS_INDEX_SQL)
        connection.commit()

    event_storage_initialized = True


def _event_record(event_data: dict) -> dict:
    return {
        "id": event_data.get("id") or str(uuid4()),
        "status": event_data.get("status"),
        "is_fall": event_data.get("is_fall"),
        "confirmed_fall": event_data.get("confirmed_fall"),
        "needs_manual_review": event_data.get("needs_manual_review"),
        "risk_level": event_data.get("risk_level"),
        "label": event_data.get("label"),
        "message": event_data.get("message"),
        "decision_reason": event_data.get("decision_reason"),
        "fall_probability": event_data.get("fall_probability"),
        "fall_probability_percent": event_data.get("fall_probability_percent"),
        "mean_fall_probability": event_data.get("mean_fall_probability"),
        "mean_fall_probability_percent": event_data.get("mean_fall_probability_percent"),
        "fall_window_count": event_data.get("fall_window_count"),
        "fall_window_ratio": event_data.get("fall_window_ratio"),
        "peak_fall_streak": event_data.get("peak_fall_streak"),
        "frames_processed": event_data.get("frames_processed"),
        "reliable_pose_frames": event_data.get("reliable_pose_frames"),
        "windows_analyzed": event_data.get("windows_analyzed"),
        "pose_reliability_ratio": event_data.get("pose_reliability_ratio"),
        "agent": event_data.get("agent"),
        "agent_result": event_data.get("agent_result"),
        "upload_size_bytes": event_data.get("upload_size_bytes"),
        "source": event_data.get("source") or "predict-video",
        "elder_id": event_data.get("elder_id"),
        "elder_snapshot": event_data.get("elder_snapshot"),
    }


def save_detection_event(event_data: dict) -> dict:
    try:
        initialize_detection_events_storage()

        record = _event_record(event_data)
        columns = ", ".join(EVENT_COLUMNS)
        placeholders = ", ".join(["%s" for _ in EVENT_COLUMNS])
        values = [
            Json(record[column])
            if column in {"agent", "agent_result", "elder_snapshot"} and record[column] is not None
            else record[column]
            for column in EVENT_COLUMNS
        ]

        with get_connection() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO detection_events ({columns})
                    VALUES ({placeholders})
                    RETURNING id, created_at
                    """,
                    values,
                )
                saved_event = cursor.fetchone()
            connection.commit()

        return {
            "saved": True,
            "detection_id": saved_event["id"],
            "created_at": _format_created_at(saved_event["created_at"]),
        }
    except Exception as exc:
        return {
            "saved": False,
            "error": str(exc),
        }


def check_detection_events_health() -> dict:
    try:
        initialize_detection_events_storage()

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM detection_events LIMIT 1")
                cursor.fetchone()

        return {
            "ok": True,
            "error": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": "Detection event storage is unavailable.",
            "details": str(exc),
        }


def list_detection_events(limit: int = 20, status: str | None = None) -> list[dict]:
    initialize_detection_events_storage()

    limit = max(1, min(int(limit or 20), 100))
    query = """
        SELECT *
        FROM detection_events
    """
    params = []

    if status:
        query += " WHERE status = %s"
        params.append(status)

    query += " ORDER BY created_at DESC, id DESC LIMIT %s"
    params.append(limit)

    with get_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

    return [_row_to_dict(row) for row in rows]


def get_detection_event(event_id: str) -> dict | None:
    initialize_detection_events_storage()

    with get_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM detection_events
                WHERE id = %s
                """,
                (event_id,),
            )
            row = cursor.fetchone()

    if row is None:
        return None

    return _row_to_dict(row)


def get_detection_event_stats() -> dict:
    initialize_detection_events_storage()

    with get_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total_detections,
                    COUNT(*) FILTER (WHERE status = 'fall' OR is_fall IS TRUE) AS fall_detections,
                    COUNT(*) FILTER (WHERE status IN ('safe', 'normal')) AS safe_detections,
                    COUNT(*) FILTER (WHERE status IN ('warning', 'suspicious')) AS warning_detections,
                    COUNT(*) FILTER (WHERE status IN ('safe', 'normal')) AS normal_detections,
                    COUNT(*) FILTER (WHERE status = 'suspicious') AS suspicious_detections,
                    COUNT(*) FILTER (
                        WHERE needs_manual_review IS TRUE OR agent->>'decision' = 'manual_review'
                    ) AS manual_review_count,
                    COUNT(*) FILTER (WHERE confirmed_fall IS TRUE) AS confirmed_fall_count,
                    COUNT(*) FILTER (WHERE risk_level = 'high') AS high_risk_count,
                    COUNT(*) FILTER (WHERE risk_level = 'medium') AS medium_risk_count,
                    COUNT(*) FILTER (WHERE risk_level = 'low') AS low_risk_count,
                    AVG(fall_probability_percent) AS average_fall_probability_percent
                FROM detection_events
                """
            )
            stats = dict(cursor.fetchone())

            cursor.execute(
                """
                SELECT *
                FROM detection_events
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """
            )
            latest = cursor.fetchone()

    stats["average_fall_probability_percent"] = round(
        float(stats.get("average_fall_probability_percent") or 0),
        2,
    )
    stats["latest_detection"] = _row_to_dict(latest) if latest else None

    return stats


def clear_detection_events() -> None:
    initialize_detection_events_storage()

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM detection_events")
        connection.commit()
