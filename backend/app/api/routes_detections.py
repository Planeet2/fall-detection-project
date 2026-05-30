from fastapi import APIRouter, HTTPException

from app.storage.detection_repository import (
    StorageUnavailable,
    clear_detection_logs,
    load_detections,
)

router = APIRouter(tags=["detections"])


@router.get("/detections")
def get_detections():
    try:
        detections = load_detections()
    except StorageUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "count": len(detections),
        "items": detections,
    }


@router.get("/detections/latest")
def get_latest_detection():
    try:
        detections = load_detections()
    except StorageUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if len(detections) == 0:
        return {
            "message": "No detections yet",
            "item": None,
        }

    return {
        "item": detections[0],
    }


@router.delete("/detections")
def clear_detections():
    try:
        clear_detection_logs()
    except StorageUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "message": "Detection history cleared",
    }
