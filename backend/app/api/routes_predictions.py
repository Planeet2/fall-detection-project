import os
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

import cv2
import numpy as np
from fastapi.concurrency import run_in_threadpool

from app.config import ALLOWED_EXTENSIONS, MAX_FRAME_UPLOAD_MB, MAX_UPLOAD_MB, UPLOAD_DIR
from app.services.agent_decision import build_agent_decision
from app.services.detector_provider import ModelUnavailable, get_detector, reset_detector
from app.services.fall_decision import add_live_decision_metadata, classify_fall_decision
from app.services.yuanjing_agent import analyze_fall_event
from app.storage.detection_repository import StorageUnavailable
from app.storage.detection_events import save_detection_event
from app.storage.elder_profiles import elder_snapshot, get_elder_profile

router = APIRouter(tags=["predictions"])

os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_FRAME_UPLOAD_BYTES = MAX_FRAME_UPLOAD_MB * 1024 * 1024
CHUNK_SIZE = 1024 * 1024  # 1 MB


def is_confirmed_fall(result: dict) -> bool:
    return result.get("confirmed_fall") is True


def add_video_decision_metadata(result: dict) -> None:
    decision = classify_fall_decision(
        fall_probability=result.get("fall_probability", 0.0),
        frames_processed=result.get("frames_processed", 0),
        reliable_pose_frames=result.get("reliable_pose_frames", 0),
        windows_analyzed=result.get("windows_analyzed", 0),
        additional_context=result,
    )
    result.update(decision)


def public_elder_profile(profile: dict | None) -> dict | None:
    if not profile:
        return None

    return {
        "id": profile.get("id"),
        "full_name": profile.get("full_name"),
        "age": profile.get("age"),
        "room": profile.get("room"),
        "location": profile.get("location"),
        "has_chronic_disease": profile.get("has_chronic_disease"),
        "health_notes": profile.get("health_notes"),
        "caregiver_name": profile.get("caregiver_name"),
        "is_active": profile.get("is_active"),
    }


async def load_elder_profile(elder_id: str | None) -> tuple[dict | None, str | None]:
    if not elder_id:
        return None, None

    try:
        profile = await run_in_threadpool(get_elder_profile, elder_id)
    except StorageUnavailable:
        return None, "Elder profile lookup is unavailable. Detection processed without profile context."

    if profile is None:
        return None, "Elder profile not found. Detection processed without profile context."

    return profile, None


def build_fall_event_data(result: dict, elder_profile: dict | None = None) -> dict:
    elder_name = "unknown"
    location = "unknown"

    if elder_profile:
        elder_name = elder_profile.get("full_name") or elder_name
        location = elder_profile.get("location") or elder_profile.get("room") or location

    return {
        "event": "fall_detected",
        "confidence": result.get("fall_probability"),
        "confidence_percent": result.get("fall_probability_percent"),
        "source": "prediction_endpoint",
        "elder_id": elder_profile.get("id") if elder_profile else result.get("elder_id"),
        "elder_name": elder_name,
        "age": elder_profile.get("age") if elder_profile else None,
        "room": elder_profile.get("room") if elder_profile else None,
        "location": location,
        "has_chronic_disease": elder_profile.get("has_chronic_disease") if elder_profile else None,
        "health_notes": elder_profile.get("health_notes") if elder_profile else None,
        "caregiver_name": elder_profile.get("caregiver_name") if elder_profile else None,
        "caregiver_contact": elder_profile.get("caregiver_contact") if elder_profile else None,
        "family_contact": elder_profile.get("family_contact") if elder_profile else None,
        "emergency_contact": elder_profile.get("emergency_contact") if elder_profile else None,
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "pose_reliability_ratio": result.get("pose_reliability_ratio"),
        "fall_window_ratio": result.get("fall_window_ratio"),
        "peak_fall_streak": result.get("peak_fall_streak"),
        "windows_analyzed": result.get("windows_analyzed"),
    }


def build_agent_failure_result(exc: Exception) -> dict:
    return {
        "risk_level": "unknown",
        "notify_caregiver": False,
        "message": "Yuanjing agent request failed.",
        "recommendation": "Check Yuanjing API configuration and network access.",
        "reason": f"{type(exc).__name__}: {exc}",
    }


async def add_yuanjing_agent_result(result: dict, elder_profile: dict | None = None) -> None:
    if not is_confirmed_fall(result):
        result["agent_result"] = None
        return

    event_data = build_fall_event_data(result, elder_profile)

    try:
        result["agent_result"] = await analyze_fall_event(event_data)
    except Exception as exc:
        result["agent_result"] = build_agent_failure_result(exc)


async def save_upload_file_with_limit(file: UploadFile, file_path: str) -> int:
    total_size = 0

    with open(file_path, "wb") as buffer:
        while True:
            chunk = await file.read(CHUNK_SIZE)

            if not chunk:
                break

            total_size += len(chunk)

            if total_size > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"File is too large. Max upload size is {MAX_UPLOAD_MB} MB.",
                )

            buffer.write(chunk)

    return total_size


@router.post("/predict-video")
async def predict_video(
    file: UploadFile = File(...),
    elder_id: str | None = Form(default=None),
):
    original_filename = file.filename
    elder_id = elder_id.strip() if elder_id else None

    if not original_filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    _, extension = os.path.splitext(original_filename)
    extension = extension.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Allowed formats: {list(ALLOWED_EXTENSIONS)}",
        )

    unique_filename = f"{uuid4()}{extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        upload_size_bytes = await save_upload_file_with_limit(file, file_path)
        elder_profile, elder_warning = await load_elder_profile(elder_id)
        public_profile = public_elder_profile(elder_profile)
        elder_snapshot_data = elder_snapshot(elder_profile)

        detector = get_detector()
        result = await run_in_threadpool(detector.predict_video, file_path)
        add_video_decision_metadata(result)
        result["elder_id"] = elder_id
        result["elder_profile"] = public_profile
        result["elder_snapshot"] = elder_snapshot_data
        result["elder_warning"] = elder_warning
        result["agent"] = build_agent_decision(result)
        await add_yuanjing_agent_result(result, elder_profile)
        # TODO: If confirmed_fall is true, create emergency notification for caregiver.
        # TODO: If needs_manual_review is true, create manual review notification.

        event_data = {
            **result,
            "upload_size_bytes": upload_size_bytes,
            "source": "predict-video",
        }
        storage = await run_in_threadpool(save_detection_event, event_data)
        detection_id = storage.get("detection_id")
        created_at = storage.get("created_at")

        return {
            **result,
            "detection_id": detection_id,
            "created_at": created_at,
            "upload_size_bytes": upload_size_bytes,
            "storage": storage,
        }

    except HTTPException:
        raise

    except ModelUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    except Exception as exc:
        raise HTTPException(status_code=500, detail="Video prediction failed.") from exc

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@router.post("/predict-frame/reset")
def reset_live_prediction():
    try:
        reset_detector()
    except ModelUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "status": "reset",
        "message": "Live frame state was reset",
    }


@router.post("/predict-frame")
async def predict_frame(file: UploadFile = File(...)):
    original_filename = file.filename

    if not original_filename:
        raise HTTPException(status_code=400, detail="No frame uploaded.")

    _, extension = os.path.splitext(original_filename)
    extension = extension.lower()

    if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(
            status_code=400,
            detail="Unsupported frame format. Allowed formats: .jpg, .jpeg, .png, .webp"
        )

    try:
        content = await file.read(MAX_FRAME_UPLOAD_BYTES + 1)

        if len(content) > MAX_FRAME_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Frame is too large. Max upload size is {MAX_FRAME_UPLOAD_MB} MB.",
            )

        np_array = np.frombuffer(content, np.uint8)
        frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

        if frame is None:
            raise HTTPException(
                status_code=400,
                detail="Could not read image frame."
            )

        detector = get_detector()
        result = await run_in_threadpool(detector.predict_frame, frame)
        add_live_decision_metadata(result)
        result["agent"] = build_agent_decision(result)
        result["agent_result"] = None

        return result

    except HTTPException:
        raise

    except ModelUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Live frame prediction failed."
        ) from exc
