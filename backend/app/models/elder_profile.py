from pydantic import BaseModel


class ElderProfileBase(BaseModel):
    full_name: str
    age: int | None = None
    room: str | None = None
    location: str | None = None
    has_chronic_disease: bool = False
    health_notes: str | None = None
    caregiver_name: str | None = None
    caregiver_contact: str | None = None
    family_contact: str | None = None
    emergency_contact: str | None = None


class ElderProfileCreate(ElderProfileBase):
    pass


class ElderProfileUpdate(BaseModel):
    full_name: str | None = None
    age: int | None = None
    room: str | None = None
    location: str | None = None
    has_chronic_disease: bool | None = None
    health_notes: str | None = None
    caregiver_name: str | None = None
    caregiver_contact: str | None = None
    family_contact: str | None = None
    emergency_contact: str | None = None
    is_active: bool | None = None


class ElderProfileResponse(ElderProfileBase):
    id: str
    is_active: bool
    created_at: str | None = None
    updated_at: str | None = None
