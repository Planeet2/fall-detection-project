from fastapi import APIRouter

from app.storage.detection_repository import clear_detection_logs, load_detections

router = APIRouter(tags=["detections"])


@router.get("/detections")
def get_detections():
    detections = load_detections()

    return {
        "count": len(detections),
        "items": detections,
    }


@router.get("/detections/latest")
def get_latest_detection():
    detections = load_detections()

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
    clear_detection_logs()

    return {
        "message": "Detection history cleared",
    }
