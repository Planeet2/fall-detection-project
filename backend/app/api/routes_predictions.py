import os
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import ALLOWED_EXTENSIONS, MAX_UPLOAD_MB, UPLOAD_DIR
from app.services.agent_decision import build_agent_decision
from app.services.fall_detector import FallDetector
from app.storage.detection_repository import add_detection_log

router = APIRouter(tags=["predictions"])

detector = FallDetector()

os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
CHUNK_SIZE = 1024 * 1024  # 1 MB


async def save_upload_file_with_limit(file: UploadFile, file_path: str) -> int:
    """Save uploaded file by chunks and reject files larger than MAX_UPLOAD_MB."""
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

        result = detector.predict_video(file_path)
        result["agent"] = build_agent_decision(result)
        detection_record = add_detection_log(original_filename, result)

        return {
            **result,
            "detection_id": detection_record["id"],
            "created_at": detection_record["created_at"],
            "upload_size_bytes": upload_size_bytes,
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
