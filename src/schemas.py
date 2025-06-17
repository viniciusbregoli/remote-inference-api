from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# API Key Schemas
class APIKeyBase(BaseModel):
    name: str


class APIKeyCreate(APIKeyBase):
    user_id: int
    expires_at: Optional[datetime] = None


class APIKeyUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class APIKeyInDB(APIKeyBase):
    id: int
    user_id: Optional[int] = None
    user_username: Optional[str] = None
    key: str
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class APIKey(APIKeyInDB):
    pass


# Usage Log Schemas
class UsageLogBase(BaseModel):
    endpoint: str
    request_size: int
    processing_time: float
    status_code: int
    request_ip: Optional[str] = None
    user_agent: Optional[str] = None


class UsageLogCreate(UsageLogBase):
    user_id: int
    api_key_id: int
    model_name: Optional[str] = None


class UsageLogInDB(UsageLogBase):
    id: int
    user_id: int
    api_key_id: int
    model_name: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class UsageLog(UsageLogInDB):
    pass


# Detection Response
class Detection(BaseModel):
    box: List[float]  # [x1, y1, x2, y2]
    confidence: float
    class_name: str


class DetectionResponse(BaseModel):
    detections: List[Detection]
    processing_time: float
    model_name: str


# Model related schemas
class ModelInfo(BaseModel):
    name: str
    description: str
    is_available: bool
    file_path: str
