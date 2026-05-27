from datetime import datetime

from fastapi import APIRouter

from app.models.schemas import NotifyRequest

router = APIRouter(tags=["notifications"])


@router.post("/mock-notify")
def mock_notify(data: NotifyRequest):
    return {
        "status": "sent",
        "channel": "mock_sms",
        "elder_id": data.elder_id,
        "contact_name": data.contact_name,
        "message": data.message,
        "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
