import os
import shutil
import json
from uuid import uuid4
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from fall_detector import FallDetector


UPLOAD_DIR = "uploads"
LOG_DIR = "logs"
DETECTIONS_LOG_FILE = os.path.join(LOG_DIR, "detections.json")

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
os.makedirs(LOG_DIR, exist_ok=True)


detector = FallDetector()


def load_detections():
    if not os.path.exists(DETECTIONS_LOG_FILE):
        return []

    try:
        with open(DETECTIONS_LOG_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        return []


def save_detections(detections):
    with open(DETECTIONS_LOG_FILE, "w", encoding="utf-8") as file:
        json.dump(detections, file, ensure_ascii=False, indent=2)


def add_detection_log(original_filename, result):
    detections = load_detections()

    detection_record = {
        "id": str(uuid4()),
        "filename": original_filename,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": result.get("status"),
        "is_fall": result.get("is_fall"),
        "risk_level": result.get("risk_level"),
        "fall_probability": result.get("fall_probability"),
        "fall_probability_percent": result.get("fall_probability_percent"),
        "label": result.get("label"),
        "message": result.get("message"),
        "frames_processed": result.get("frames_processed"),
        "windows_analyzed": result.get("windows_analyzed")
    }

    detections.insert(0, detection_record)
    save_detections(detections)

    return detection_record


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


@app.get("/model-info")
def model_info():
    return {
        "model": "YOLOv8 Pose + LSTM",
        "input": "video",
        "sequence_length": 30,
        "classes": ["safe", "fall"],
        "threshold": 0.6,
        "supported_formats": list(ALLOWED_EXTENSIONS)
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
        detection_record = add_detection_log(original_filename, result)

        return {
            **result,
            "detection_id": detection_record["id"],
            "created_at": detection_record["created_at"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@app.get("/detections")
def get_detections():
    detections = load_detections()

    return {
        "count": len(detections),
        "items": detections
    }


@app.get("/detections/latest")
def get_latest_detection():
    detections = load_detections()

    if len(detections) == 0:
        return {
            "message": "No detections yet",
            "item": None
        }

    return {
        "item": detections[0]
    }


@app.delete("/detections")
def clear_detections():
    save_detections([])

    return {
        "message": "Detection history cleared"
    }

@app.get("/stats")
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
        "latest_detection": latest_detection
    }