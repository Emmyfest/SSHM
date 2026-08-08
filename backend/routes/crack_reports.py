"""# routes/crack_reports.py
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
"""


# routes/crack_reports.py

import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import (
    APIRouter,
    HTTPException,
    Header,
    UploadFile,
    Form,
    File,
)
from fastapi.responses import FileResponse

from bson import ObjectId
from bson.errors import InvalidId

from database.db import crack_reports_col
from services.ws_manager import manager


router = APIRouter(
    prefix="/api/crack-reports",
    tags=["crack-reports"]
)

DEVICE_API_KEY = os.getenv(
    "DEVICE_API_KEY",
    "change_this_device_key"
)

# ============================================================
# IMAGE STORAGE CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

IMAGE_DIR = BASE_DIR / "uploads" / "crack_images"

# Create the directory automatically if it does not exist
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

# Maximum image size: 10 MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


# ============================================================
# POST — RECEIVE CRACK REPORT + IMAGE
# ============================================================

@router.post("")
async def ingest_crack_report(
    image: UploadFile = File(...),
    report: str = Form(...),
    x_device_key: str = Header(default=None),
):

    # --------------------------------------------------------
    # 1. Authenticate device
    # --------------------------------------------------------

    if x_device_key != DEVICE_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid device key"
        )

    # --------------------------------------------------------
    # 2. Validate image type
    # --------------------------------------------------------

    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid image type. "
                "Allowed types: JPEG, PNG, WEBP"
            )
        )

    # --------------------------------------------------------
    # 3. Parse report JSON
    # --------------------------------------------------------

    try:
        report_data = json.loads(report)

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid report JSON"
        )

    # --------------------------------------------------------
    # 4. Read image
    # --------------------------------------------------------

    image_bytes = await image.read()

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded image is empty"
        )

    # --------------------------------------------------------
    # 5. Check image size
    # --------------------------------------------------------

    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Image is too large. Maximum size is 10 MB."
        )

    # --------------------------------------------------------
    # 6. Generate unique filename
    # --------------------------------------------------------

    extension = ALLOWED_IMAGE_TYPES[image.content_type]

    filename = f"{uuid.uuid4().hex}{extension}"

    image_path = IMAGE_DIR / filename

    # --------------------------------------------------------
    # 7. Save image to disk
    # --------------------------------------------------------

    try:
        with open(image_path, "wb") as f:
            f.write(image_bytes)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save image: {str(e)}"
        )

    # --------------------------------------------------------
    # 8. Create database document
    # --------------------------------------------------------

    doc = {
        "device_id": report_data.get("device_id"),
        "timestamp": datetime.utcnow(),
        "summary": report_data.get("summary"),
        "cracks": report_data.get("cracks"),

        # Store only the filename/path in MongoDB.
        # The actual image remains on the server.
        "image_filename": filename,

        "image_original_filename": image.filename,

        "image_content_type": image.content_type,

        "image_size": len(image_bytes),
    }

    # --------------------------------------------------------
    # 9. Save report to MongoDB
    # --------------------------------------------------------

    try:
        result = await crack_reports_col.insert_one(doc)

    except Exception as e:

        # If MongoDB fails, remove the image we just saved
        # so we don't leave orphaned files behind.

        if image_path.exists():
            image_path.unlink()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to save crack report: {str(e)}"
        )

    # --------------------------------------------------------
    # 10. Generate image URL
    # --------------------------------------------------------

    image_url = (
        f"/api/crack-reports/"
        f"{result.inserted_id}/image"
    )

    # --------------------------------------------------------
    # 11. Broadcast real-time notification
    # --------------------------------------------------------

    await manager.broadcast({
        "type": "crack_report",

        "id": str(result.inserted_id),

        "device_id": doc["device_id"],

        "summary": doc["summary"],

        "cracks": doc["cracks"],

        "timestamp": doc["timestamp"].isoformat(),

        "image_url": image_url,
    })

    # --------------------------------------------------------
    # 12. Return response
    # --------------------------------------------------------

    return {
        "message": "Crack report recorded",

        "id": str(result.inserted_id),

        "device_id": doc["device_id"],

        "summary": doc["summary"],

        "cracks": doc["cracks"],

        "image_url": image_url,

        "timestamp": doc["timestamp"].isoformat(),
    }


# ============================================================
# GET — LIST CRACK REPORTS
# ============================================================

@router.get("")
async def list_crack_reports(
    limit: int = 50
):

    # Prevent unreasonable requests
    if limit < 1:
        limit = 1

    if limit > 200:
        limit = 200

    cursor = (
        crack_reports_col
        .find()
        .sort("timestamp", -1)
        .limit(limit)
    )

    docs = await cursor.to_list(length=limit)

    results = []

    for d in docs:

        results.append({
            "id": str(d["_id"]),

            "device_id": d.get("device_id"),

            "timestamp": d.get("timestamp"),

            "summary": d.get("summary"),

            "cracks": d.get("cracks"),

            "image_url": (
                f"/api/crack-reports/"
                f"{d['_id']}/image"
            ),

            "image_filename": d.get(
                "image_filename"
            ),

            "image_content_type": d.get(
                "image_content_type"
            ),

            "image_size": d.get(
                "image_size"
            ),
        })

    return results


# ============================================================
# GET — RETURN ACTUAL CRACK IMAGE
# ============================================================

@router.get("/{report_id}/image")
async def get_crack_report_image(
    report_id: str
):

    # --------------------------------------------------------
    # 1. Validate MongoDB ObjectId
    # --------------------------------------------------------

    try:
        object_id = ObjectId(report_id)

    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid crack report ID"
        )

    # --------------------------------------------------------
    # 2. Find report
    # --------------------------------------------------------

    report = await crack_reports_col.find_one({
        "_id": object_id
    })

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Crack report not found"
        )

    # --------------------------------------------------------
    # 3. Get stored filename
    # --------------------------------------------------------

    filename = report.get("image_filename")

    if not filename:
        raise HTTPException(
            status_code=404,
            detail="No image associated with this report"
        )

    # --------------------------------------------------------
    # 4. Build image path
    # --------------------------------------------------------

    image_path = IMAGE_DIR / filename

    # Security check:
    # Make sure the requested file remains inside
    # the crack image directory.

    try:
        image_path.resolve().relative_to(
            IMAGE_DIR.resolve()
        )

    except ValueError:
        raise HTTPException(
            status_code=403,
            detail="Invalid image path"
        )

    # --------------------------------------------------------
    # 5. Check if file exists
    # --------------------------------------------------------

    if not image_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Image file not found on server"
        )

    # --------------------------------------------------------
    # 6. Return image
    # --------------------------------------------------------

    return FileResponse(
        path=image_path,
        media_type=report.get(
            "image_content_type",
            "image/jpeg"
        ),

        filename=report.get(
            "image_original_filename",
            filename
        )
    )
```
