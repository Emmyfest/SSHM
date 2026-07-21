"""
Populates the database with realistic sample data so the dashboard isn't
empty on first look: 4 buildings across different cities, one of each
status (SAFE / SAFE / WARNING / CRITICAL), ~30 days of historical
readings per building (so the 24h/7d/month chart tabs all have data),
matching devices, and alerts generated from the same threshold logic
the live ingestion endpoint uses.

Run from the backend/ directory (after installing requirements and
setting up your .env):

    python seed_data.py
"""

import asyncio
import random
from datetime import datetime, timedelta

from database.db import buildings_col, devices_col, readings_col, alerts_col, settings_col, ensure_indexes
from services.health_index import determine_status
from services.settings_service import DEFAULT_THRESHOLDS

BUILDINGS = [
    {
        "buildingID": "JB001",
        "name": "Jabi Tower",
        "owner": "Jabi Properties Ltd",
        "city": "Abuja",
        "engineer": "Eng. Adaeze Okafor",
        "installation_date": "2025-11-02",
        "gps_lat": 9.0765,
        "gps_lng": 7.3986,
        "firmware_version": "v1.2.0",
        "profile": "safe",
    },
    {
        "buildingID": "PH004",
        "name": "GRA Bridge Point",
        "owner": "Rivers State Infrastructure Agency",
        "city": "Port Harcourt",
        "engineer": "Eng. Tamuno Wike",
        "installation_date": "2025-10-18",
        "gps_lat": 4.8156,
        "gps_lng": 7.0498,
        "firmware_version": "v1.2.0",
        "profile": "safe",
    },
    {
        "buildingID": "LG002",
        "name": "Marina Complex",
        "owner": "Lagos Marina Estates",
        "city": "Lagos",
        "engineer": "Eng. Bolanle Adeyemi",
        "installation_date": "2025-09-27",
        "gps_lat": 6.4531,
        "gps_lng": 3.3958,
        "firmware_version": "v1.1.4",
        "profile": "warning",
    },
    {
        "buildingID": "IB003",
        "name": "Bodija Heights",
        "owner": "Bodija Housing Cooperative",
        "city": "Ibadan",
        "engineer": "Eng. Kunle Bakare",
        "installation_date": "2025-08-14",
        "gps_lat": 7.4125,
        "gps_lng": 3.9107,
        "firmware_version": "v1.0.9",
        "profile": "critical",
    },
]

# base(min,max) readings per profile, plus how much the final ~48h escalates
PROFILE_RANGES = {
    "safe":     {"strain": (150, 320), "tilt": (0.2, 1.0), "vibration": (0.02, 0.07), "battery": (3.8, 4.1)},
    "warning":  {"strain": (650, 850), "tilt": (2.8, 4.2), "vibration": (0.8, 1.2),   "battery": (3.5, 3.7)},
    "critical": {"strain": (900, 1150), "tilt": (4.5, 6.5), "vibration": (1.3, 1.9),  "battery": (3.2, 3.5)},
}
ESCALATION = {  # multiplier applied progressively over the last 2 days for warning/critical buildings
    "safe": 1.0, "warning": 1.35, "critical": 1.6,
}


def gen_reading(profile: str, escalate_fraction: float):
    ranges = PROFILE_RANGES[profile]
    escalation = 1 + (ESCALATION[profile] - 1) * escalate_fraction
    strain = random.uniform(*ranges["strain"]) * escalation
    tilt = random.uniform(*ranges["tilt"]) * escalation
    vibration = random.uniform(*ranges["vibration"]) * escalation
    battery = random.uniform(*ranges["battery"]) - (0.3 * escalate_fraction if profile != "safe" else 0)
    gsm_signal = random.randint(14, 27)
    return round(strain, 1), round(tilt, 2), round(vibration, 3), round(max(battery, 3.0), 2), gsm_signal


async def seed():
    await ensure_indexes()

    print("Clearing previous sample data (buildings, devices, readings, alerts)...")
    building_ids = [b["buildingID"] for b in BUILDINGS]
    await buildings_col.delete_many({"buildingID": {"$in": building_ids}})
    await devices_col.delete_many({"buildingID": {"$in": building_ids}})
    await readings_col.delete_many({"buildingID": {"$in": building_ids}})
    await alerts_col.delete_many({"buildingID": {"$in": building_ids}})

    print("Inserting buildings + devices...")
    for b in BUILDINGS:
        doc = {k: v for k, v in b.items() if k != "profile"}
        await buildings_col.insert_one(doc)
        await devices_col.insert_one({
            "device_id": f"ESP32-{b['buildingID']}",
            "buildingID": b["buildingID"],
            "firmware_version": b["firmware_version"],
            "last_seen": datetime.utcnow(),
            "battery": None,
            "gsm_signal": None,
        })

    print("Generating ~30 days of readings per building (every 4 hours)...")
    now = datetime.utcnow()
    start = now - timedelta(days=30)
    interval = timedelta(hours=4)
    total_steps = int((now - start) / interval)

    alert_count = 0
    reading_count = 0

    for b in BUILDINGS:
        profile = b["profile"]
        for step in range(total_steps + 1):
            ts = start + interval * step
            # escalate only over the final 48h window, and only for warning/critical profiles
            hours_from_now = (now - ts).total_seconds() / 3600
            escalate_fraction = max(0.0, 1 - (hours_from_now / 48)) if profile != "safe" else 0.0

            strain, tilt, vibration, battery, gsm = gen_reading(profile, escalate_fraction)
            status = determine_status(strain, tilt, vibration, DEFAULT_THRESHOLDS)

            await readings_col.insert_one({
                "buildingID": b["buildingID"],
                "strain": strain,
                "tilt": tilt,
                "vibration": vibration,
                "battery": battery,
                "gsm_signal": gsm,
                "device_id": f"ESP32-{b['buildingID']}",
                "timestamp": ts,
                "status": status,
            })
            reading_count += 1

            if status in ("WARNING", "CRITICAL") and step % 3 == 0:  # thin out alerts to a realistic count
                reasons = []
                if strain > DEFAULT_THRESHOLDS["strain_threshold"]:
                    reasons.append("Strain threshold exceeded")
                if tilt > DEFAULT_THRESHOLDS["tilt_threshold"]:
                    reasons.append("Tilt threshold exceeded")
                if vibration > DEFAULT_THRESHOLDS["vibration_threshold"]:
                    reasons.append("Vibration threshold exceeded")
                await alerts_col.insert_one({
                    "buildingID": b["buildingID"],
                    "building_name": b["name"],
                    "severity": status,
                    "reason": "; ".join(reasons) or "Reading outside safe range",
                    "timestamp": ts,
                    "status": "resolved" if hours_from_now > 6 else "open",
                })
                alert_count += 1

        # update device with its final/latest reading snapshot
        await devices_col.update_one(
            {"device_id": f"ESP32-{b['buildingID']}"},
            {"$set": {"last_seen": now, "battery": battery, "gsm_signal": gsm}},
        )

    print("Setting default alert thresholds...")
    await settings_col.update_one({"_id": "global"}, {"$set": DEFAULT_THRESHOLDS}, upsert=True)

    print(f"\nDone. Inserted {len(BUILDINGS)} buildings, {reading_count} readings, {alert_count} alerts.")
    print("Expected dashboard mix: Jabi Tower & GRA Bridge Point = SAFE, "
          "Marina Complex = WARNING (escalating), Bodija Heights = CRITICAL (escalating).")


if __name__ == "__main__":
    asyncio.run(seed())
