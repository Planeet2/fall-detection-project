import os
from typing import Optional

from app.config import LSTM_MODEL_PATH, YOLO_MODEL_NAME
from app.services.fall_detector import FallDetector


class ModelUnavailable(RuntimeError):
    pass


detector: Optional[FallDetector] = None
last_model_error: Optional[str] = None


def get_detector() -> FallDetector:
    global detector, last_model_error

    if detector is not None:
        return detector

    try:
        detector = FallDetector()
        last_model_error = None
    except Exception as exc:
        last_model_error = str(exc)
        raise ModelUnavailable("Fall detector model is unavailable.") from exc

    return detector


def reset_detector():
    loaded_detector = get_detector()
    loaded_detector.reset_live_state()


def check_model_health():
    if detector is not None:
        return {
            "ok": True,
            "loaded": True,
            "error": None,
        }

    missing_files = []

    if not os.path.exists(LSTM_MODEL_PATH):
        missing_files.append(LSTM_MODEL_PATH)

    if YOLO_MODEL_NAME.endswith((".pt", ".pth")) and not os.path.exists(YOLO_MODEL_NAME):
        missing_files.append(YOLO_MODEL_NAME)

    if missing_files:
        return {
            "ok": False,
            "loaded": False,
            "error": "Missing model files.",
            "missing_files": missing_files,
        }

    return {
        "ok": True,
        "loaded": False,
        "error": last_model_error,
    }
