from fastapi import APIRouter, HTTPException, status
from models.schemas import LoginRequest
from database.db import users_col
from auth.security import verify_password
from auth.jwt_handler import create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
async def login(payload: LoginRequest):
    user = await users_col.find_one({"username": payload.username})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    role = user.get("role", "viewer")
    building_id = user.get("buildingID")  # only set for role == "owner"

    token_payload = {"sub": user["username"], "role": role}
    if building_id:
        token_payload["buildingID"] = building_id

    token = create_access_token(token_payload)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"username": user["username"], "role": role, "buildingID": building_id},
    }
