from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId

from models.schemas import DeviceCreate
from database.db import devices_col
from auth.dependencies import get_current_user

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("")
async def list_devices(user: dict = Depends(get_current_user)):
    devices = await devices_col.find().to_list(500)
    for d in devices:
        d["_id"] = str(d["_id"])
    return devices


@router.post("")
async def create_device(payload: DeviceCreate, user: dict = Depends(get_current_user)):
    existing = await devices_col.find_one({"device_id": payload.device_id})
    if existing:
        raise HTTPException(status_code=409, detail="A device with this ID already exists")
    await devices_col.insert_one(payload.dict())
    return {"message": "Device registered"}


@router.put("/{device_id}")
async def update_device(device_id: str, payload: DeviceCreate, user: dict = Depends(get_current_user)):
    result = await devices_col.update_one({"device_id": device_id}, {"$set": payload.dict()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"message": "Device updated"}


@router.delete("/{device_id}")
async def delete_device(device_id: str, user: dict = Depends(get_current_user)):
    result = await devices_col.delete_one({"_id": ObjectId(device_id)}) if len(device_id) == 24 else \
        await devices_col.delete_one({"device_id": device_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"message": "Device removed"}
