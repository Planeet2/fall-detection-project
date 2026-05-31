from fastapi import APIRouter, HTTPException, Query

from app.models.elder_profile import ElderProfileCreate, ElderProfileUpdate
from app.storage.detection_repository import StorageUnavailable
from app.storage.elder_profiles import (
    create_elder_profile,
    deactivate_elder_profile,
    get_elder_profile,
    list_elder_profiles,
    update_elder_profile,
)

router = APIRouter(prefix="/elders", tags=["elders"])


def _model_data(model, *, exclude_unset: bool = False) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_unset=exclude_unset)

    return model.dict(exclude_unset=exclude_unset)


@router.post("")
def create_elder(profile: ElderProfileCreate):
    try:
        return create_elder_profile(_model_data(profile))
    except StorageUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("")
def list_elders(active_only: bool = Query(True)):
    try:
        return {
            "items": list_elder_profiles(active_only=active_only),
        }
    except StorageUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/{elder_id}")
def get_elder(elder_id: str):
    try:
        profile = get_elder_profile(elder_id)
    except StorageUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if profile is None:
        raise HTTPException(status_code=404, detail="Elder profile not found")

    return profile


@router.patch("/{elder_id}")
def update_elder(elder_id: str, profile: ElderProfileUpdate):
    try:
        updated_profile = update_elder_profile(
            elder_id,
            _model_data(profile, exclude_unset=True),
        )
    except StorageUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if updated_profile is None:
        raise HTTPException(status_code=404, detail="Elder profile not found")

    return updated_profile


@router.delete("/{elder_id}")
def delete_elder(elder_id: str):
    try:
        deleted = deactivate_elder_profile(elder_id)
    except StorageUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=404, detail="Elder profile not found")

    return {
        "deleted": True,
    }
