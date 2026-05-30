import os
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile

import cv2
import numpy as np
from fastapi.concurrency import run_in_threadpool

from app.config import ALLOWED_EXTENSIONS, MAX_FRAME_UPLOAD_MB, MAX_UPLOAD_MB, UPLOAD_DIR
from app.services.agent_decision import build_agent_decision
from app.services.detector_provider import ModelUnavailable, get_detector, reset_detector
from app.storage.detection_repository import StorageUnavailable, add_detection_log

router = APIRouter(tags=["predictions"])

os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_FRAME_UPLOAD_BYTES = MAX_FRAME_UPLOAD_MB * 1024 * 1024
CHUNK_SIZE = 1024 * 1024  # 1 MB


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
        result["agent"] = build_agent_decision(result)
        # TODO: After fall detection is confirmed, call analyze_fall_event(event_data),
        # save agent_result to PostgreSQL, and trigger notification if notify_caregiver is true.

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
        result["agent"] = build_agent_decision(result)

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
