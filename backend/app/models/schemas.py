from pydantic import BaseModel


class NotifyRequest(BaseModel):
    elder_id: str = "elder_001"
    contact_name: str = "Family member"
    message: str
