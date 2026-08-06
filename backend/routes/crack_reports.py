# routes/crack_reports.py
import json
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, Header, UploadFile, Form
from database.db import readings_col
from services.ws_manager import manager

router = APIRouter(prefix="/api/crack-reports", tags=["crack-reports"])
DEVICE_API_KEY = os.getenv("DEVICE_API_KEY", "change_this_device_key")


@router.post("")
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
    # TODO: save image_bytes to disk/S3/GridFS, store resulting path/URL

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
