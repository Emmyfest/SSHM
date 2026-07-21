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

    token = create_access_token({"sub": user["username"], "role": user.get("role", "viewer")})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"username": user["username"], "role": user.get("role", "viewer")},
    }
