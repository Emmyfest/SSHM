from database.db import settings_col

DEFAULT_THRESHOLDS = {
    "strain_threshold": 1000.0,
    "vibration_threshold": 1.5,
    "tilt_threshold": 5.0,
    "battery_threshold": 3.3,
}


async def get_thresholds() -> dict:
    doc = await settings_col.find_one({"_id": "global"})
    if not doc:
        return DEFAULT_THRESHOLDS
    return {**DEFAULT_THRESHOLDS, **{k: v for k, v in doc.items() if k != "_id"}}


async def save_thresholds(data: dict) -> dict:
    await settings_col.update_one({"_id": "global"}, {"$set": data}, upsert=True)
    return await get_thresholds()
