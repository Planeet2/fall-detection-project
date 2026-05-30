from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_agent import router as agent_router
from app.api.routes_detections import router as detections_router
from app.api.routes_notifications import router as notifications_router
from app.api.routes_predictions import router as predictions_router
from app.api.routes_stats import router as stats_router
from app.api.routes_system import router as system_router
from app.config import CORS_ORIGINS
from app.storage.detection_repository import close_storage

app = FastAPI(
    title="Fall Detection Backend",
    description="Backend API for YOLOv8 Pose + LSTM fall detection",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router)
app.include_router(predictions_router)
app.include_router(notifications_router)
app.include_router(detections_router)
app.include_router(stats_router)
app.include_router(agent_router)


@app.on_event("shutdown")
def shutdown_event():
    close_storage()
