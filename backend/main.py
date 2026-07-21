import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from database.db import ensure_indexes, users_col
from auth.security import hash_password
from auth.jwt_handler import decode_access_token
from services.ws_manager import manager
from routes import auth, buildings, readings, alerts, devices, users, settings, analytics, reports

load_dotenv()

app = FastAPI(title="S-SHM Platform API", version="1.0.0")

origins_from_env = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
# Known frontend URL, hardcoded as a guaranteed fallback so login isn't
# blocked by a missed/unsaved Render environment variable edit.
KNOWN_ORIGINS = ["https://sshm-ui.onrender.com", "http://localhost:5500", "http://127.0.0.1:5500"]
origins = list(set(origins_from_env + KNOWN_ORIGINS)) or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(buildings.router)
app.include_router(readings.router)
app.include_router(alerts.router)
app.include_router(devices.router)
app.include_router(users.router)
app.include_router(settings.router)
app.include_router(analytics.router)
app.include_router(reports.router)


@app.on_event("startup")
async def on_startup():
    await ensure_indexes()

    # Bootstrap a default admin account on first run so the dashboard
    # is reachable before anyone manually creates a user.
    existing_admin = await users_col.find_one({})
    if not existing_admin:
        username = os.getenv("ADMIN_USERNAME", "admin")
        password = os.getenv("ADMIN_PASSWORD", "changeme123")
        await users_col.insert_one({
            "username": username,
            "password_hash": hash_password(password),
            "role": "admin",
        })
        print(f"[startup] Created default admin user '{username}' -- change this password after first login.")


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket, token: str = None):
    # WebSockets can't send an Authorization header, so the frontend
    # passes the JWT as a query param instead: /ws/live?token=...
    payload = decode_access_token(token) if token else None
    if not payload:
        await websocket.close(code=1008)  # policy violation -- not authenticated
        return

    await manager.connect(websocket)
    try:
        while True:
            # We don't expect the client to send anything meaningful --
            # this just keeps the connection open and detects disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
