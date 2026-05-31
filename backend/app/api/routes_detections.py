from fastapi import APIRouter, HTTPException, Query

from app.storage.detection_events import (
    clear_detection_events,
    get_detection_event,
    list_detection_events,
)
from app.storage.detection_repository import StorageUnavailable

router = APIRouter(tags=["detections"])


def _history_unavailable_response(exc: Exception):
    return {
        "count": 0,
        "items": [],
        "storage": {
            "available": False,
            "error": str(exc),
        },
    }


@router.get("/detections/history")
def get_detection_history(
    limit: int = Query(20, ge=1, le=100),
    status: str | None = None,
):
    try:
        events = list_detection_events(limit=limit, status=status)
    except StorageUnavailable as exc:
        return _history_unavailable_response(exc)

    return {
        "count": len(events),
        "items": events,
        "storage": {
            "available": True,
            "error": None,
        },
    }


@router.get("/detections/history/{detection_id}")
def get_detection_history_item(detection_id: str):
    try:
        event = get_detection_event(detection_id)
    except StorageUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if event is None:
        raise HTTPException(status_code=404, detail="Detection event not found")

    return {
        "item": event,
    }


@router.get("/detections")
def get_detections(limit: int = Query(20, ge=1, le=100)):
    try:
        detections = list_detection_events(limit=limit)
    except StorageUnavailable as exc:
        return _history_unavailable_response(exc)

    return {
        "count": len(detections),
        "items": detections,
        "storage": {
            "available": True,
            "error": None,
        },
    }


@router.get("/detections/latest")
def get_latest_detection():
    try:
        detections = list_detection_events(limit=1)
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
        clear_detection_events()
    except StorageUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "message": "Detection history cleared",
    }
