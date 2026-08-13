import json
import os
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Header, UploadFile, Form
from fastapi.responses import StreamingResponse
from database.db import crack_reports_col, fs_bucket
from services.ws_manager import manager

router = APIRouter(prefix="/api/crack-reports", tags=["crack-reports"])
DEVICE_API_KEY = os.getenv("DEVICE_API_KEY", "change_this_device_key")


@router.post("")
async def ingest_crack_report(
    image: UploadFile,
    report: str = Form(...),
    x_device_key: str = Header(default=None),
):
    """
    Called by the Raspberry Pi crack-detection node over HTTPS -- authenticated
    with the same shared device key header used by ESP32 sensor nodes.
    """
    if x_device_key != DEVICE_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid device key")

    try:
        report_data = json.loads(report)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid report JSON")

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image upload")

    file_id = await fs_bucket.upload_from_stream(
        image.filename or "crack.jpg",
        image_bytes,
        metadata={"content_type": image.content_type or "image/jpeg"},
    )

    doc = {
        "device_id": report_data.get("device_id"),
        "timestamp": datetime.utcnow(),
        "summary": report_data.get("summary"),
        "cracks": report_data.get("cracks"),
        "image_file_id": file_id,
    }
    result = await crack_reports_col.insert_one(doc)

    payload = {
        "type": "crack_report",
        "id": str(result.inserted_id),
        "device_id": doc["device_id"],
        "summary": doc["summary"],
        "image_url": f"/api/crack-reports/{result.inserted_id}/image",
        "timestamp": doc["timestamp"].isoformat(),
    }
    await manager.broadcast(payload)

    return {
        "message": "Crack report recorded",
        "id": str(result.inserted_id),
        "summary": doc["summary"],
    }


@router.get("")
async def list_crack_reports(limit: int = 50, device_id: str = None):
    """
    Returns recent crack reports (metadata + image URL, not raw image bytes)
    so the dashboard can render a history feed / gallery on page load.
    """
    query = {"device_id": device_id} if device_id else {}
    cursor = crack_reports_col.find(query).sort("timestamp", -1).limit(limit)
    docs = await cursor.to_list(limit)

    results = []
    for d in docs:
        results.append({
            "id": str(d["_id"]),
            "device_id": d.get("device_id"),
            "timestamp": d.get("timestamp"),
            "summary": d.get("summary"),
            "cracks": d.get("cracks"),
            "image_url": f"/api/crack-reports/{d['_id']}/image",
        })
    return results


@router.get("/{report_id}")
async def get_crack_report(report_id: str):
    """Full detail for a single crack report (used for a detail/expanded view)."""
    try:
        oid = ObjectId(report_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid report id")

    doc = await crack_reports_col.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "id": str(doc["_id"]),
        "device_id": doc.get("device_id"),
        "timestamp": doc.get("timestamp"),
        "summary": doc.get("summary"),
        "cracks": doc.get("cracks"),
        "image_url": f"/api/crack-reports/{doc['_id']}/image",
    }


@router.get("/{report_id}/image")
async def get_crack_report_image(report_id: str):
    try:
        oid = ObjectId(report_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid report id")

    doc = await crack_reports_col.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")

    file_id = doc.get("image_file_id")
    if not file_id:
        raise HTTPException(status_code=404, detail="This report has no stored image")

    try:
        grid_out = await fs_bucket.open_download_stream(file_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Image not found in storage")

    content_type = "image/jpeg"
    if grid_out.metadata and "content_type" in grid_out.metadata:
        content_type = grid_out.metadata["content_type"]

    async def stream():
        while True:
            chunk = await grid_out.readchunk()
            if not chunk:
                break
            yield chunk

    return StreamingResponse(stream(), media_type=content_type)
