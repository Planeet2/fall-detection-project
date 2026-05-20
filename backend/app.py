import os
import shutil
from uuid import uuid4

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from fall_detector import FallDetector

UPLOAD_DIR = "uploads"

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm"}

app = FastAPI(
    title="Fall Detection Backend",
    description="Backend API for YOLOv8 Pose + LSTM fall detection",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(UPLOAD_DIR, exist_ok=True)

detector = FallDetector()


@app.get("/")
def root():
    return {
        "message": "Fall Detection Backend is running",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }


@app.post("/predict-video")
async def predict_video(file: UploadFile = File(...)):

    original_filename = file.filename

    if not original_filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    _, extension = os.path.splitext(original_filename)
    extension = extension.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Allowed formats: {list(ALLOWED_EXTENSIONS)}"
        )

    unique_filename = f"{uuid4()}{extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = detector.predict_video(file_path)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)