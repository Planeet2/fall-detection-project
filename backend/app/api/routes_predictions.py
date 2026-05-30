import os
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile

import cv2
import numpy as np
from fastapi.concurrency import run_in_threadpool

from app.config import ALLOWED_EXTENSIONS, MAX_FRAME_UPLOAD_MB, MAX_UPLOAD_MB, UPLOAD_DIR
from app.services.agent_decision import build_agent_decision
from app.services.detector_provider import ModelUnavailable, get_detector, reset_detector
from app.services.fall_decision import add_live_decision_metadata, classify_fall_decision
from app.services.yuanjing_agent import analyze_fall_event
from app.storage.detection_repository import StorageUnavailable, add_detection_log

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


def build_fall_event_data(result: dict) -> dict:
    return {
        "event": "fall_detected",
        "confidence": result.get("fall_probability"),
        "confidence_percent": result.get("fall_probability_percent"),
        "source": "prediction_endpoint",
        "location": "unknown",
        "elder_id": None,
        "elder_name": "unknown",
        "age": None,
        "has_chronic_disease": None,
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


async def add_yuanjing_agent_result(result: dict) -> None:
    if not is_confirmed_fall(result):
        result["agent_result"] = None
        return

    event_data = build_fall_event_data(result)

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
async def predict_video(file: UploadFile = File(...)):
    original_filename = file.filename

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

        detector = get_detector()
        result = await run_in_threadpool(detector.predict_video, file_path)
        add_video_decision_metadata(result)
        result["agent"] = build_agent_decision(result)
        await add_yuanjing_agent_result(result)
        # TODO: Save fall detection event and agent_result to PostgreSQL.
        # TODO: If agent_result.notify_caregiver is true, create caregiver notification.

        detection_id = None
        created_at = None
        storage = {"saved": True, "error": None}

        try:
            detection_record = await run_in_threadpool(add_detection_log, original_filename, result)
            detection_id = detection_record["id"]
            created_at = detection_record["created_at"]
        except StorageUnavailable as exc:
            storage = {"saved": False, "error": str(exc)}

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
