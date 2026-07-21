from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from collections import defaultdict

from database.db import readings_col, buildings_col, alerts_col
from auth.dependencies import get_current_user
from services.settings_service import get_thresholds
from services.health_index import compute_health_index, determine_status

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

RANGE_TO_DELTA = {"24h": timedelta(hours=24), "7d": timedelta(days=7), "month": timedelta(days=30)}
BUCKET_SIZE = {"24h": timedelta(hours=1), "7d": timedelta(hours=12), "month": timedelta(days=1)}


@router.get("")
async def get_analytics(range: str = "24h", user: dict = Depends(get_current_user)):
    delta = RANGE_TO_DELTA.get(range, RANGE_TO_DELTA["24h"])
    bucket_size = BUCKET_SIZE.get(range, BUCKET_SIZE["24h"])
    cutoff = datetime.utcnow() - delta
    thresholds = await get_thresholds()

    readings = await readings_col.find({"timestamp": {"$gte": cutoff}}).sort("timestamp", 1).to_list(5000)

    buckets = defaultdict(list)
    for r in readings:
        idx = int((r["timestamp"] - cutoff) / bucket_size)
        health = compute_health_index(r["strain"], r["tilt"], r["vibration"], r.get("battery"), True, thresholds)
        buckets[idx].append(health)

    timeline = [
        {"timestamp": cutoff + bucket_size * idx, "avg_health": round(sum(vals) / len(vals), 1)}
        for idx, vals in sorted(buckets.items())
    ]

    buildings = await buildings_col.find().to_list(500)
    status_counts = {"SAFE": 0, "WARNING": 0, "CRITICAL": 0}
    for b in buildings:
        latest = await readings_col.find_one({"buildingID": b["buildingID"]}, sort=[("timestamp", -1)])
        if latest:
            s = determine_status(latest["strain"], latest["tilt"], latest["vibration"], thresholds)
            status_counts[s] = status_counts.get(s, 0) + 1

    alerts = await alerts_col.find({"timestamp": {"$gte": cutoff}}).to_list(2000)
    counts_by_building = defaultdict(int)
    names = {}
    for a in alerts:
        counts_by_building[a["buildingID"]] += 1
        names[a["buildingID"]] = a.get("building_name", a["buildingID"])
    alerts_by_building = [{"name": names[bid], "count": c} for bid, c in counts_by_building.items()]

    return {"timeline": timeline, "status_counts": status_counts, "alerts_by_building": alerts_by_building}
