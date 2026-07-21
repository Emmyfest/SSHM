import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header

from models.schemas import ReadingIn
from database.db import readings_col, buildings_col, devices_col, alerts_col
from auth.dependencies import get_current_user
from services.settings_service import get_thresholds
from services.health_index import determine_status
from services.ws_manager import manager

router = APIRouter(prefix="/api/readings", tags=["readings"])

DEVICE_API_KEY = os.getenv("DEVICE_API_KEY", "change_this_device_key")


@router.post("")
async def ingest_reading(payload: ReadingIn, x_device_key: str = Header(default=None)):
    """
    Called directly by ESP32 devices over HTTPS -- authenticated with a
    shared device key header instead of a user JWT, since the devices
    never log in as a user.
    """
    if x_device_key != DEVICE_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid device key")

    building = await buildings_col.find_one({"buildingID": payload.buildingID})
    if not building:
        raise HTTPException(status_code=404, detail=f"Unknown buildingID: {payload.buildingID}")

    thresholds = await get_thresholds()
    status = determine_status(payload.strain, payload.tilt, payload.vibration, thresholds)

    doc = payload.dict()
    doc["timestamp"] = datetime.utcnow()
    doc["status"] = status
    await readings_col.insert_one(doc)

    if payload.device_id:
        await devices_col.update_one(
            {"device_id": payload.device_id},
            {"$set": {
                "last_seen": doc["timestamp"],
                "battery": payload.battery,
                "gsm_signal": payload.gsm_signal,
            }},
        )

    if status in ("WARNING", "CRITICAL"):
        reasons = []
        if abs(payload.strain) > thresholds["strain_threshold"]:
            reasons.append("Strain threshold exceeded")
        if abs(payload.tilt) > thresholds["tilt_threshold"]:
            reasons.append("Tilt threshold exceeded")
        if abs(payload.vibration) > thresholds["vibration_threshold"]:
            reasons.append("Vibration threshold exceeded")

        await alerts_col.insert_one({
            "buildingID": payload.buildingID,
            "building_name": building.get("name", payload.buildingID),
            "severity": status,
            "reason": "; ".join(reasons) or "Reading outside safe range",
            "timestamp": doc["timestamp"],
            "status": "open",
        })

    await manager.broadcast({
        "buildingID": payload.buildingID,
        "name": building.get("name", payload.buildingID),
        "status": status,
        "strain": payload.strain,
        "tilt": payload.tilt,
        "vibration": payload.vibration,
        "battery": payload.battery,
        "gsm_signal": payload.gsm_signal,
        "timestamp": doc["timestamp"].isoformat(),
    })

    return {"message": "Reading recorded", "status": status}


@router.get("/live")
async def live_readings(user: dict = Depends(get_current_user)):
    buildings = await buildings_col.find().to_list(500)
    results = []
    for b in buildings:
        latest = await readings_col.find_one({"buildingID": b["buildingID"]}, sort=[("timestamp", -1)])
        if not latest:
            continue
        results.append({
            "buildingID": b["buildingID"],
            "name": b.get("name", b["buildingID"]),
            "status": latest.get("status", "SAFE"),
            "strain": latest.get("strain"),
            "tilt": latest.get("tilt"),
            "vibration": latest.get("vibration"),
            "battery": latest.get("battery"),
            "gsm_signal": latest.get("gsm_signal"),
            "timestamp": latest.get("timestamp"),
        })
    return results
