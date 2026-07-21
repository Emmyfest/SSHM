from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "viewer"  # viewer | engineer | admin


class BuildingCreate(BaseModel):
    buildingID: str
    name: Optional[str] = None
    owner: Optional[str] = None
    city: Optional[str] = None
    engineer: Optional[str] = None
    installation_date: Optional[str] = None
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    firmware_version: Optional[str] = None


class ReadingIn(BaseModel):
    buildingID: str
    strain: float
    tilt: float
    vibration: float
    battery: Optional[float] = None
    gsm_signal: Optional[int] = None
    device_id: Optional[str] = None


class DeviceCreate(BaseModel):
    device_id: str
    buildingID: str
    firmware_version: Optional[str] = None


class SettingsUpdate(BaseModel):
    strain_threshold: float = 1000.0
    vibration_threshold: float = 1.5
    tilt_threshold: float = 5.0
    battery_threshold: float = 3.3
