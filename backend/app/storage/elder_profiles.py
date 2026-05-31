from datetime import datetime, timezone
from uuid import uuid4

from psycopg2.extras import RealDictCursor

from app.storage.detection_repository import get_connection, initialize_storage


CREATE_ELDER_PROFILES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS elder_profiles (
    id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    age INTEGER,
    room TEXT,
    location TEXT,
    has_chronic_disease BOOLEAN DEFAULT false,
    health_notes TEXT,
    caregiver_name TEXT,
    caregiver_contact TEXT,
    family_contact TEXT,
    emergency_contact TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
"""

CREATE_ELDER_PROFILES_ACTIVE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_elder_profiles_is_active
ON elder_profiles (is_active);
"""

PROFILE_COLUMNS = [
    "id",
    "full_name",
    "age",
    "room",
    "location",
    "has_chronic_disease",
    "health_notes",
    "caregiver_name",
    "caregiver_contact",
    "family_contact",
    "emergency_contact",
    "is_active",
    "created_at",
    "updated_at",
]

CREATE_FIELDS = [
    "full_name",
    "age",
    "room",
    "location",
    "has_chronic_disease",
    "health_notes",
    "caregiver_name",
    "caregiver_contact",
    "family_contact",
    "emergency_contact",
]

UPDATE_FIELDS = CREATE_FIELDS + ["is_active"]

elder_profiles_initialized = False


def _format_timestamp(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)

        return value.isoformat().replace("+00:00", "Z")

    return str(value)


def _row_to_dict(row):
    item = dict(row)
    item["created_at"] = _format_timestamp(item.get("created_at"))
    item["updated_at"] = _format_timestamp(item.get("updated_at"))
    return item


def initialize_elder_profiles_storage():
    global elder_profiles_initialized

    if elder_profiles_initialized:
        return

    initialize_storage()

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_ELDER_PROFILES_TABLE_SQL)
            cursor.execute(CREATE_ELDER_PROFILES_ACTIVE_INDEX_SQL)
        connection.commit()

    elder_profiles_initialized = True


def create_elder_profile(data: dict) -> dict:
    initialize_elder_profiles_storage()

    record = {field: data.get(field) for field in CREATE_FIELDS}
    record["id"] = str(uuid4())

    columns = ["id"] + CREATE_FIELDS
    placeholders = ", ".join(["%s" for _ in columns])
    values = [record[column] for column in columns]

    with get_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                f"""
                INSERT INTO elder_profiles ({", ".join(columns)})
                VALUES ({placeholders})
                RETURNING {", ".join(PROFILE_COLUMNS)}
                """,
                values,
            )
            row = cursor.fetchone()
        connection.commit()

    return _row_to_dict(row)


def list_elder_profiles(active_only: bool = True) -> list[dict]:
    initialize_elder_profiles_storage()

    query = f"""
        SELECT {", ".join(PROFILE_COLUMNS)}
        FROM elder_profiles
    """
    params = []

    if active_only:
        query += " WHERE is_active IS TRUE"

    query += " ORDER BY full_name ASC, created_at DESC"

    with get_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

    return [_row_to_dict(row) for row in rows]


def get_elder_profile(elder_id: str) -> dict | None:
    initialize_elder_profiles_storage()

    with get_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                f"""
                SELECT {", ".join(PROFILE_COLUMNS)}
                FROM elder_profiles
                WHERE id = %s
                """,
                (elder_id,),
            )
            row = cursor.fetchone()

    if row is None:
        return None

    return _row_to_dict(row)


def update_elder_profile(elder_id: str, data: dict) -> dict | None:
    initialize_elder_profiles_storage()

    updates = {
        field: value
        for field, value in data.items()
        if field in UPDATE_FIELDS
    }

    if not updates:
        return get_elder_profile(elder_id)

    assignments = [f"{field} = %s" for field in updates]
    assignments.append("updated_at = now()")
    values = list(updates.values())
    values.append(elder_id)

    with get_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                f"""
                UPDATE elder_profiles
                SET {", ".join(assignments)}
                WHERE id = %s
                RETURNING {", ".join(PROFILE_COLUMNS)}
                """,
                values,
            )
            row = cursor.fetchone()
        connection.commit()

    if row is None:
        return None

    return _row_to_dict(row)


def deactivate_elder_profile(elder_id: str) -> bool:
    initialize_elder_profiles_storage()

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE elder_profiles
                SET is_active = false, updated_at = now()
                WHERE id = %s AND is_active IS TRUE
                """,
                (elder_id,),
            )
            deleted = cursor.rowcount > 0
        connection.commit()

    return deleted


def get_elder_profile_counts() -> dict:
    initialize_elder_profiles_storage()

    with get_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total_elders,
                    COUNT(*) FILTER (WHERE is_active IS TRUE) AS active_elders
                FROM elder_profiles
                """
            )
            row = cursor.fetchone()

    return dict(row)


def elder_snapshot(profile: dict | None) -> dict | None:
    if not profile:
        return None

    return {
        "id": profile.get("id"),
        "full_name": profile.get("full_name"),
        "age": profile.get("age"),
        "room": profile.get("room"),
        "location": profile.get("location"),
        "has_chronic_disease": profile.get("has_chronic_disease"),
    }
