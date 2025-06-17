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
import io
from contextlib import asynccontextmanager
import redis
import json

from database import get_db, create_tables
from auth import authenticate_request
from usage_logger import log_api_usage
from utils import get_image_size

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_QUEUE = "detection_jobs"

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
    """Get Redis connection"""
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

@app.post("/detect")
async def detect_objects(
    image: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
):
    # Authenticate the request
    user_id, api_key_data = authenticate_request(request, db)

    start_time = time.time()
    request_size = get_image_size(image)

    try:
        # Get image from request and convert to base64
        img_data = await image.read()
        img_base64 = base64.b64encode(img_data).decode('utf-8')

        # Create job payload
        job_payload = {
            "image": img_base64,
            "user_id": user_id,
            "api_key_id": api_key_data["api_key"].id if api_key_data else None,
            "request_ip": request.client.host if request else None,
            "user_agent": request.headers.get("user-agent") if request else None,
            "timestamp": time.time()
        }

        # Push job to Redis queue
        redis_conn = get_redis_connection()
        redis_conn.lpush(REDIS_QUEUE, json.dumps(job_payload))

        end_time = time.time()
        processing_time = end_time - start_time

        # Log the request
        log_api_usage(
            user_id=user_id,
            api_key_id=api_key_data["api_key"].id if api_key_data else None,
            endpoint="/detect",
            request_size=request_size,
            processing_time=processing_time,
            status_code=200,
            model_name="queued",  # Since we don't know which model will process it
            request_ip=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None,
            db=db,
        )

        return {"status": "success", "message": "Image queued for processing"}

    except Exception as e:
        end_time = time.time()
        processing_time = end_time - start_time

        # Log the failed request
        log_api_usage(
            user_id=user_id,
            api_key_id=api_key_data["api_key"].id if api_key_data else None,
            endpoint="/detect",
            request_size=request_size,
            processing_time=processing_time,
            status_code=500,
            model_name="queued",
            request_ip=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None,
            db=db,
        )

        error_msg = f"Error processing request: {str(e)}"
        print(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
