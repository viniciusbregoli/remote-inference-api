from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# Job Queue Schemas
class JobBase(BaseModel):
    """Base schema for job data"""

    job_id: int
    image: str = Field(..., description="Base64 encoded image data")


class JobCreate(JobBase):
    """Schema for creating a new job to be sent to Redis queue"""

    pass


class JobProcess(JobBase):
    """Schema for processing a job fetched from Redis queue"""

    model_name: Optional[str] = Field(None, description="Model to use for processing")
    priority: Optional[int] = Field(1, description="Job priority (1=high, 5=low)")


class JobResult(BaseModel):
    """Schema for job processing results"""

    job_id: int
    success: bool
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    detections_count: Optional[int] = None


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


# Api Log Schemas
class ApiLogBase(BaseModel):
    endpoint: str
    request_size: int
    status_code: int


class ApiLogCreate(ApiLogBase):
    user_id: int
    api_key_id: int
    model_name: Optional[str] = None


class ApiLogInDB(ApiLogBase):
    id: int
    user_id: int
    api_key_id: int
    model_name: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class ApiLog(ApiLogInDB):
    pass


# Detection Schemas
class BoundingBoxBase(BaseModel):
    class_name: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float


class BoundingBoxCreate(BoundingBoxBase):
    detection_id: int


class BoundingBox(BoundingBoxBase):
    id: int
    detection_id: int

    class Config:
        from_attributes = True


class DetectionBase(BaseModel):
    model_name: str
    image_width: int
    image_height: int
    processing_time: float


class DetectionCreate(DetectionBase):
    job_id: int


class Detection(DetectionBase):
    id: int
    job_id: int
    bounding_boxes: List[BoundingBox] = []

    class Config:
        from_attributes = True


# Detection Response
class DetectionResponse(BaseModel):
    job_id: int
    message: str


# Model related schemas
class ModelInfo(BaseModel):
    name: str
    description: str
    is_available: bool
    file_path: str
