from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId
from datetime import datetime

from database.db import alerts_col
from auth.dependencies import get_current_user

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("")
async def list_alerts(status: str = Query(default=None), limit: int = 100, user: dict = Depends(get_current_user)):
    query = {}
    if status:
        query["status"] = status
    cursor = alerts_col.find(query).sort("timestamp", -1).limit(limit)
    alerts = await cursor.to_list(limit)
    for a in alerts:
        a["_id"] = str(a["_id"])
    return alerts


@router.patch("/{alert_id}/resolve")
async def resolve_alert(alert_id: str, user: dict = Depends(get_current_user)):
    result = await alerts_col.update_one(
        {"_id": ObjectId(alert_id)},
        {"$set": {"status": "resolved", "resolved_at": datetime.utcnow(), "resolved_by": user.get("sub")}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"message": "Alert resolved"}
