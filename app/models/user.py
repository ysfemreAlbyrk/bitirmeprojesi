"""User models"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class UserPreferences(BaseModel):
    ambient_intensity: float = 0.7
    theme: str = "dark"
    language: str = "tr"
    auto_play_audio: bool = True


class User(BaseModel):
    id: str
    email: str
    display_name: str
    preferences: UserPreferences
    created_at: datetime
    last_active: Optional[datetime] = None


class UserCreate(BaseModel):
    email: str
    display_name: str
    preferences: Optional[UserPreferences] = None


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    preferences: Optional[UserPreferences] = None
