import json
from fastapi import APIRouter, HTTPException, Header, UploadFile, Form
from datetime import datetime
from database.db import readings_col, buildings_col, devices_col, alerts_col
from services.ws_manager import manager
import os

DEVICE_API_KEY = os.getenv("DEVICE_API_KEY", "change_this_device_key")

@router.post("/crack-reports")
async def ingest_crack_report(
    image: UploadFile,
    report: str = Form(...),
    x_device_key: str = Header(default=None),
):
    if x_device_key != DEVICE_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid device key")

    try:
        report_data = json.loads(report)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid report JSON")

    image_bytes = await image.read()
    # TODO: save image_bytes to disk/S3/GridFS, store the resulting path/URL
    # rather than the raw bytes, in your readings_col or a new crack_reports_col

    doc = {
        "device_id": report_data.get("device_id"),
        "timestamp": datetime.utcnow(),
        "summary": report_data.get("summary"),
        "cracks": report_data.get("cracks"),
        # "image_path": saved_path,
    }
    await readings_col.insert_one(doc)

    await manager.broadcast({
        "type": "crack_report",
        "device_id": doc["device_id"],
        "summary": doc["summary"],
        "timestamp": doc["timestamp"].isoformat(),
    })

    return {"message": "Crack report recorded", "summary": doc["summary"]}
