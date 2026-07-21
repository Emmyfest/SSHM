import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "")
DB_NAME = os.getenv("DB_NAME", "shm")

if not MONGODB_URI:
    raise RuntimeError(
        "MONGODB_URI is not set. Copy backend/.env.example to backend/.env "
        "and fill in your MongoDB Atlas connection string."
    )

client = AsyncIOMotorClient(MONGODB_URI)
db = client[DB_NAME]

buildings_col = db["buildings"]
readings_col = db["readings"]
alerts_col = db["alerts"]
devices_col = db["devices"]
users_col = db["users"]
settings_col = db["settings"]


async def ensure_indexes():
    await buildings_col.create_index("buildingID", unique=True)
    await readings_col.create_index([("buildingID", 1), ("timestamp", -1)])
    await alerts_col.create_index([("timestamp", -1)])
    await devices_col.create_index("device_id", unique=True)
    await users_col.create_index("username", unique=True)
