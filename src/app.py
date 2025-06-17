import os
import time
import base64
from fastapi import (
    FastAPI,
    File,
    UploadFile,
    HTTPException,
    Depends,
    Request,
)
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import redis
import json

from database import get_db, create_tables
from auth import authenticate_request
from usage_logger import log_api_call
from schemas import ApiLogCreate, DetectionResponse
from utils import get_image_size

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_QUEUE = "detection_jobs"

# Create Redis connection pool
redis_pool = redis.ConnectionPool(
    host=REDIS_HOST, port=REDIS_PORT, decode_responses=True
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    create_tables()
    print("API initialized successfully!")
    yield
    print("Shutting down application...")


app = FastAPI(
    title="YOLO Object Detection API",
    description="API for object detection using YOLOv8 models",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_redis_connection():
    """Get Redis connection from pool"""
    return redis.Redis(connection_pool=redis_pool)


@app.post("/detect", response_model=DetectionResponse)
async def detect_objects(
    request: Request,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    auth_data: dict = Depends(authenticate_request),
):
    user_id = auth_data["user_id"]
    api_key_id = auth_data["api_key_id"]

    request_size = get_image_size(image)

    try:
        # Log the API call and get a job ID
        log_entry = log_api_call(
            db=db,
            log_data=ApiLogCreate(
                user_id=user_id,
                api_key_id=api_key_id,
                endpoint="/detect",
                request_size=request_size,
                status_code=202,  # Accepted
                model_name="queued",
            ),
        )

        # Get image from request and convert to base64
        img_data = await image.read()
        img_base64 = base64.b64encode(img_data).decode("utf-8")

        # Create job payload
        job_payload = {
            "job_id": log_entry.id,
            "image": img_base64,
        }

        # Push job to Redis queue
        redis_conn = get_redis_connection()
        redis_conn.lpush(REDIS_QUEUE, json.dumps(job_payload))

        return DetectionResponse(
            job_id=log_entry.id, message="Image queued for processing."  # type: ignore
        )

    except Exception as e:
        error_msg = f"Error processing request: {str(e)}"
        print(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
