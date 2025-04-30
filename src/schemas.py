from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# User Schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class UserInDB(UserBase):
    id: int
    is_admin: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class User(UserInDB):
    pass


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
    user_id: Optional[int] = None  # Changed to allow None values
    key: str
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class APIKey(APIKeyInDB):
    pass


# Model Schemas
class ModelBase(BaseModel):
    name: str
    description: Optional[str] = None


class ModelCreate(ModelBase):
    file_path: str


class ModelUpdate(BaseModel):
    name: Optional[str] = None
    file_path: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ModelInDB(ModelBase):
    id: int
    file_path: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Model(ModelInDB):
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
    model_id: Optional[int] = None


class UsageLogInDB(UsageLogBase):
    id: int
    user_id: int
    api_key_id: int
    model_id: Optional[int] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class UsageLog(UsageLogInDB):
    pass


# Rate Limit Schemas
class RateLimitBase(BaseModel):
    daily_limit: int = 100
    monthly_limit: int = 3000


class RateLimitCreate(RateLimitBase):
    user_id: int


class RateLimitUpdate(BaseModel):
    daily_limit: Optional[int] = None
    monthly_limit: Optional[int] = None


class RateLimitInDB(RateLimitBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RateLimit(RateLimitInDB):
    pass


# Authentication Schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None
    is_admin: Optional[bool] = False


# API Usage Statistics
class UserStats(BaseModel):
    daily_usage: int
    monthly_usage: int
    daily_limit: int
    monthly_limit: int
    daily_percentage: float
    monthly_percentage: float


# Detection Response
class Detection(BaseModel):
    box: List[float]  # [x1, y1, x2, y2]
    confidence: float
    class_name: str


class DetectionResponse(BaseModel):
    detections: List[Detection]
    processing_time: float
    model_name: str