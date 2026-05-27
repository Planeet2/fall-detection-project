from fastapi import APIRouter

from app.config import ALLOWED_EXTENSIONS, FALL_PROBABILITY_THRESHOLD, SEQ_LEN

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
