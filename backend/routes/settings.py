from fastapi import APIRouter, Depends

from models.schemas import SettingsUpdate
from auth.dependencies import get_current_user
from services.settings_service import get_thresholds, save_thresholds

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
async def read_settings(user: dict = Depends(get_current_user)):
    return await get_thresholds()


@router.put("")
async def update_settings(payload: SettingsUpdate, user: dict = Depends(get_current_user)):
    return await save_thresholds(payload.dict())
