from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from datetime import datetime

from models.schemas import UserCreate
from database.db import users_col
from auth.dependencies import require_admin
from auth.security import hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("")
async def list_users(user: dict = Depends(require_admin)):
    users = await users_col.find().to_list(500)
    for u in users:
        u["_id"] = str(u["_id"])
        u.pop("password_hash", None)
    return users


@router.post("")
async def create_user(payload: UserCreate, user: dict = Depends(require_admin)):
    existing = await users_col.find_one({"username": payload.username})
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken")
    await users_col.insert_one({
        "username": payload.username,
        "password_hash": hash_password(payload.password),
        "role": payload.role,
        "created_at": datetime.utcnow(),
    })
    return {"message": "User created"}


@router.delete("/{user_id}")
async def delete_user(user_id: str, user: dict = Depends(require_admin)):
    result = await users_col.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User removed"}
