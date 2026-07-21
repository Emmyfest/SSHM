from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta

from models.schemas import BuildingCreate
from database.db import buildings_col, readings_col
from auth.dependencies import get_current_user
from services.settings_service import get_thresholds
from services.health_index import compute_health_index, determine_status

router = APIRouter(prefix="/api/buildings", tags=["buildings"])

RANGE_TO_DELTA = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "month": timedelta(days=30),
}


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


async def _with_latest_reading(building: dict, thresholds: dict) -> dict:
    latest = await readings_col.find_one({"buildingID": building["buildingID"]}, sort=[("timestamp", -1)])
    if latest:
        comm_ok = (datetime.utcnow() - latest["timestamp"]) < timedelta(hours=6)
        building["strain"] = latest.get("strain")
        building["tilt"] = latest.get("tilt")
        building["vibration"] = latest.get("vibration")
        building["battery"] = latest.get("battery")
        building["gsm_signal"] = latest.get("gsm_signal")
        building["timestamp"] = latest.get("timestamp")
        building["status"] = determine_status(latest["strain"], latest["tilt"], latest["vibration"], thresholds)
        building["health_index"] = compute_health_index(
            latest["strain"], latest["tilt"], latest["vibration"], latest.get("battery"), comm_ok, thresholds
        )
    else:
        building["status"] = "SAFE"
        building["health_index"] = None
    return building


@router.get("")
async def list_buildings(user: dict = Depends(get_current_user)):
    thresholds = await get_thresholds()
    buildings = await buildings_col.find().to_list(500)
    return [await _with_latest_reading(_serialize(b), thresholds) for b in buildings]


@router.get("/{building_id}")
async def get_building(building_id: str, user: dict = Depends(get_current_user)):
    building = await buildings_col.find_one({"buildingID": building_id})
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    thresholds = await get_thresholds()
    return await _with_latest_reading(_serialize(building), thresholds)


@router.get("/{building_id}/history")
async def get_building_history(building_id: str, range: str = "24h", user: dict = Depends(get_current_user)):
    delta = RANGE_TO_DELTA.get(range, RANGE_TO_DELTA["24h"])
    cutoff = datetime.utcnow() - delta
    cursor = readings_col.find(
        {"buildingID": building_id, "timestamp": {"$gte": cutoff}}
    ).sort("timestamp", 1)
    readings = await cursor.to_list(2000)
    for r in readings:
        r["_id"] = str(r["_id"])
    return readings


@router.post("")
async def create_building(payload: BuildingCreate, user: dict = Depends(get_current_user)):
    existing = await buildings_col.find_one({"buildingID": payload.buildingID})
    if existing:
        raise HTTPException(status_code=409, detail="A building with this ID already exists")
    doc = payload.dict()
    await buildings_col.insert_one(doc)
    return {"message": "Building created", "buildingID": payload.buildingID}


@router.put("/{building_id}")
async def update_building(building_id: str, payload: BuildingCreate, user: dict = Depends(get_current_user)):
    result = await buildings_col.update_one({"buildingID": building_id}, {"$set": payload.dict()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Building not found")
    return {"message": "Building updated"}


@router.delete("/{building_id}")
async def delete_building(building_id: str, user: dict = Depends(get_current_user)):
    result = await buildings_col.delete_one({"buildingID": building_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Building not found")
    return {"message": "Building deleted"}
