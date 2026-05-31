from fastapi import APIRouter, Response, status

from app.config import ALLOWED_EXTENSIONS, FALL_PROBABILITY_THRESHOLD, SEQ_LEN
from app.services.detector_provider import check_model_health
from app.storage.detection_events import check_detection_events_health
from app.storage.detection_repository import check_storage_health

router = APIRouter(tags=["system"])


@router.get("/")
def root():
    return {
        "message": "Fall Detection Backend is running",
        "docs": "/docs",
    }


@router.get("/health")
def health_check():
    return {
        "status": "ok",
    }


@router.get("/ready")
def readiness_check(response: Response):
    model = check_model_health()
    storage = check_storage_health()
    event_storage = check_detection_events_health()
    is_ready = model["ok"] and storage["ok"] and event_storage["ok"]

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if is_ready else "degraded",
        "checks": {
            "model": model,
            "storage": storage,
            "event_storage": event_storage,
        },
    }


@router.get("/model-info")
def model_info():
    return {
        "model": "YOLOv8 Pose + LSTM",
        "input": "video",
        "sequence_length": SEQ_LEN,
        "classes": ["safe", "fall"],
        "threshold": FALL_PROBABILITY_THRESHOLD,
        "supported_formats": list(ALLOWED_EXTENSIONS),
    }
