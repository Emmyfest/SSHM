import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Header

from models.schemas import ReadingIn
from database.db import (
    readings_col,
    buildings_col,
    devices_col,
    alerts_col,
)
from auth.dependencies import get_current_user
from services.settings_service import get_thresholds
from services.health_index import determine_status
from services.ws_manager import manager


router = APIRouter(
    prefix="/api/readings",
    tags=["readings"]
)


DEVICE_API_KEY = os.getenv(
    "DEVICE_API_KEY",
    "change_this_device_key"
)


# ============================================================
# RECEIVE READING FROM ESP32
# ============================================================

@router.post("")
async def ingest_reading(
    payload: ReadingIn,
    x_device_key: str = Header(default=None)
):
    """
    Called directly by ESP32 devices over HTTPS.

    ESP32 devices authenticate using the shared device key
    instead of a user JWT.
    """

    # --------------------------------------------------------
    # Authenticate ESP32
    # --------------------------------------------------------

    if x_device_key != DEVICE_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid device key"
        )

    # --------------------------------------------------------
    # Check building exists
    # --------------------------------------------------------

    building = await buildings_col.find_one({
        "buildingID": payload.buildingID
    })

    if not building:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown buildingID: {payload.buildingID}"
        )

    # --------------------------------------------------------
    # Get thresholds
    # --------------------------------------------------------

    thresholds = await get_thresholds()

    # --------------------------------------------------------
    # Determine status for this reading
    # --------------------------------------------------------

    status = determine_status(
        payload.strain,
        payload.tilt,
        payload.vibration,
        thresholds
    )

    # --------------------------------------------------------
    # Create database document
    # --------------------------------------------------------

    doc = payload.dict()

    doc["timestamp"] = datetime.utcnow()
    doc["status"] = status

    # --------------------------------------------------------
    # IMPORTANT:
    # Save EVERY reading.
    #
    # We do NOT overwrite the previous node reading.
    # This allows tilt and vibration nodes to coexist.
    # --------------------------------------------------------

    await readings_col.insert_one(doc)

    # --------------------------------------------------------
    # Update device information
    # --------------------------------------------------------

    if payload.device_id:
        await devices_col.update_one(
            {"device_id": payload.device_id},
            {
                "$set": {
                    "last_seen": doc["timestamp"],
                    "battery": payload.battery,
                    "gsm_signal": payload.gsm_signal,
                }
            },
        )

    # --------------------------------------------------------
    # Create alert if necessary
    # --------------------------------------------------------

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
            "building_name": building.get(
                "name",
                payload.buildingID
            ),
            "severity": status,
            "reason": "; ".join(reasons)
                or "Reading outside safe range",
            "timestamp": doc["timestamp"],
            "status": "open",
            "device_id": payload.device_id,
        })

    # --------------------------------------------------------
    # Send real-time update through WebSocket
    # --------------------------------------------------------

    await manager.broadcast({
        "buildingID": payload.buildingID,
        "name": building.get(
            "name",
            payload.buildingID
        ),

        "device_id": payload.device_id,

        "status": status,

        "strain": payload.strain,
        "tilt": payload.tilt,
        "vibration": payload.vibration,

        "battery": payload.battery,
        "gsm_signal": payload.gsm_signal,

        "timestamp": doc["timestamp"].isoformat(),
    })

    return {
        "message": "Reading recorded",
        "status": status
    }


# ============================================================
# LIVE READINGS
# ============================================================

@router.get("/live")
async def live_readings(
    user: dict = Depends(get_current_user)
):
    """
    Return the latest reading from EACH DEVICE/NODE
    belonging to each building.

    This is important because a building can have multiple
    ESP32 nodes.

    Example:

        NODE-0 -> tilt
        NODE-1 -> vibration

    Both will be returned instead of only whichever one
    reported last.
    """

    # --------------------------------------------------------
    # Determine which buildings the user can see
    # --------------------------------------------------------

    owner_building = user.get("buildingID")

    if owner_building:
        query = {
            "buildingID": owner_building
        }
    else:
        query = {}

    buildings = await buildings_col.find(
        query
    ).to_list(500)

    results = []

    # --------------------------------------------------------
    # Process each building
    # --------------------------------------------------------

    for building in buildings:

        building_id = building["buildingID"]

        # ----------------------------------------------------
        # Get the latest reading from EACH device.
        #
        # This is the important fix.
        #
        # Before:
        #
        #   latest reading for entire building
        #
        # Now:
        #
        #   latest reading for NODE-0
        #   latest reading for NODE-1
        #   latest reading for NODE-2
        #   etc.
        # ----------------------------------------------------

        pipeline = [

            # Only readings belonging to this building
            {
                "$match": {
                    "buildingID": building_id,

                    # Make sure the reading has a device ID
                    "device_id": {
                        "$exists": True,
                        "$ne": None
                    }
                }
            },

            # Newest readings first
            {
                "$sort": {
                    "timestamp": -1
                }
            },

            # Group readings by device_id.
            #
            # Because they were sorted newest-first,
            # $first gives us the latest reading for
            # each individual device.
            {
                "$group": {
                    "_id": "$device_id",
                    "reading": {
                        "$first": "$$ROOT"
                    }
                }
            },

            # Return the original reading document
            {
                "$replaceRoot": {
                    "newRoot": "$reading"
                }
            }
        ]

        latest_per_device = await readings_col.aggregate(
            pipeline
        ).to_list(500)

        # ----------------------------------------------------
        # Add every node's latest reading to the result
        # ----------------------------------------------------

        for latest in latest_per_device:

            results.append({
                "buildingID": building_id,

                "name": building.get(
                    "name",
                    building_id
                ),

                # IMPORTANT:
                # The frontend can now identify which node
                # produced the reading.
                "device_id": latest.get(
                    "device_id"
                ),

                "status": latest.get(
                    "status",
                    "SAFE"
                ),

                "strain": latest.get(
                    "strain"
                ),

                "tilt": latest.get(
                    "tilt"
                ),

                "vibration": latest.get(
                    "vibration"
                ),

                "battery": latest.get(
                    "battery"
                ),

                "gsm_signal": latest.get(
                    "gsm_signal"
                ),

                "timestamp": latest.get(
                    "timestamp"
                ),
            })

    return results
