from fastapi import APIRouter

from app.storage.detection_events import get_detection_event_stats
from app.storage.detection_repository import StorageUnavailable
from app.storage.elder_profiles import get_elder_profile_counts

router = APIRouter(tags=["stats"])


@router.get("/stats")
def get_stats():
    try:
        stats = get_detection_event_stats()
    except StorageUnavailable as exc:
        return {
            "total_detections": 0,
            "fall_detections": 0,
            "safe_detections": 0,
            "warning_detections": 0,
            "normal_detections": 0,
            "suspicious_detections": 0,
            "manual_review_count": 0,
            "confirmed_fall_count": 0,
            "total_elders": 0,
            "active_elders": 0,
            "high_risk_count": 0,
            "medium_risk_count": 0,
            "low_risk_count": 0,
            "average_fall_probability_percent": 0,
            "latest_detection": None,
            "storage": {
                "available": False,
                "error": str(exc),
            },
        }

    try:
        elder_stats = get_elder_profile_counts()
    except StorageUnavailable:
        elder_stats = {
            "total_elders": 0,
            "active_elders": 0,
        }

    return {
        **stats,
        **elder_stats,
        "storage": {
            "available": True,
            "error": None,
        },
    }
