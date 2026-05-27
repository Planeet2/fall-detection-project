from fastapi import APIRouter

from app.storage.detection_repository import load_detections

router = APIRouter(tags=["stats"])


@router.get("/stats")
def get_stats():
    detections = load_detections()

    total_detections = len(detections)

    fall_detections = sum(
        1 for item in detections
        if item.get("is_fall") is True
    )

    safe_detections = sum(
        1 for item in detections
        if item.get("status") == "safe"
    )

    warning_detections = sum(
        1 for item in detections
        if item.get("status") == "warning"
    )

    high_risk_count = sum(
        1 for item in detections
        if item.get("risk_level") == "high"
    )

    medium_risk_count = sum(
        1 for item in detections
        if item.get("risk_level") == "medium"
    )

    low_risk_count = sum(
        1 for item in detections
        if item.get("risk_level") == "low"
    )

    if total_detections > 0:
        average_fall_probability = sum(
            item.get("fall_probability_percent", 0) or 0
            for item in detections
        ) / total_detections
    else:
        average_fall_probability = 0

    latest_detection = detections[0] if total_detections > 0 else None

    return {
        "total_detections": total_detections,
        "fall_detections": fall_detections,
        "safe_detections": safe_detections,
        "warning_detections": warning_detections,
        "high_risk_count": high_risk_count,
        "medium_risk_count": medium_risk_count,
        "low_risk_count": low_risk_count,
        "average_fall_probability_percent": round(average_fall_probability, 2),
        "latest_detection": latest_detection,
    }
