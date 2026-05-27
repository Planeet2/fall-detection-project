import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


def _load_env_file(env_path: Path = ENV_FILE):
    """Load simple KEY=VALUE pairs from .env without extra dependencies."""
    if not env_path.exists():
        return

    with env_path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            os.environ.setdefault(key, value)


def _get_str(name: str, default: str) -> str:
    return os.getenv(name, default)


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)

    if value is None:
        return default

    try:
        return float(value)
    except ValueError:
        return default


def _get_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)

    if value is None:
        return default

    return [item.strip() for item in value.split(",") if item.strip()]


_load_env_file()

UPLOAD_DIR = _get_str("UPLOAD_DIR", "uploads")
LOG_DIR = _get_str("LOG_DIR", "logs")
DETECTIONS_LOG_FILE = os.path.join(LOG_DIR, _get_str("DETECTIONS_LOG_FILENAME", "detections.json"))

DATABASE_URL = _get_str(
    "DATABASE_URL",
    "postgresql://elderly_user:elderly_password@localhost:5432/elderly_check",
)

ALLOWED_EXTENSIONS = set(
    _get_list("ALLOWED_EXTENSIONS", [".mp4", ".mov", ".avi", ".webm"])
)

YOLO_MODEL_NAME = _get_str("YOLO_MODEL_NAME", "yolov8n-pose.pt")
LSTM_MODEL_PATH = _get_str("LSTM_MODEL_PATH", "fall_detection_lstm.pth")

SEQ_LEN = _get_int("SEQ_LEN", 30)
INPUT_SIZE = _get_int("INPUT_SIZE", 51)
HIDDEN_SIZE = _get_int("HIDDEN_SIZE", 64)
NUM_CLASSES = _get_int("NUM_CLASSES", 2)

FALL_PROBABILITY_THRESHOLD = _get_float("FALL_PROBABILITY_THRESHOLD", 0.6)
WARNING_PROBABILITY_THRESHOLD = _get_float("WARNING_PROBABILITY_THRESHOLD", 0.4)

MAX_UPLOAD_MB = _get_int("MAX_UPLOAD_MB", 100)

CORS_ORIGINS = _get_list(
    "CORS_ORIGINS",
    [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
)
