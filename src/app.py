import os
import base64
from fastapi import (
    FastAPI,
    File,
    UploadFile,
    HTTPException,
    Depends,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import redis

from database import get_db, create_tables, SessionLocal
from auth import authenticate_request
from usage_logger import log_api_call
from database import Detection as DetectionModel
from schemas import ApiLogCreate, JobCreate, JobResult
from utils import get_image_size

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DETECTION_QUEUE = "detection_jobs"

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


@app.post("/detect")
async def detect_objects(
    request: Request,
    image: UploadFile = File(...),
    timeout: int = 30,  # Add timeout parameter
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

        # Create job payload using schema
        job_payload = JobCreate(
            job_id=log_entry.id,
            image=img_base64,
        )

        # Push job to Redis queue (as JSON string)
        redis_conn = get_redis_connection()
        redis_conn.lpush(REDIS_DETECTION_QUEUE, job_payload.model_dump_json())

        result_key = f"result_{log_entry.id}"

        try:
            # Block until result is available or timeout
            result_data = redis_conn.brpop([result_key], timeout=timeout)

            if result_data:
                # Parse the result
                result_json = result_data[1]  # type: ignore
                job_result = JobResult.model_validate_json(result_json)

                if job_result.success:
                    # Fetch the detection from database

                    with SessionLocal() as session:
                        detection = (
                            session.query(DetectionModel)
                            .filter(DetectionModel.job_id == log_entry.id)
                            .first()
                        )

                        if detection:
                            # Convert to dict for JSON response
                            detection_dict = {
                                "id": detection.id,
                                "job_id": detection.job_id,
                                "model_name": detection.model_name,
                                "image_width": detection.image_width,
                                "image_height": detection.image_height,
                                "processing_time": detection.processing_time,
                                "bounding_boxes": [
                                    {
                                        "id": bb.id,
                                        "class_name": bb.class_name,
                                        "confidence": bb.confidence,
                                        "x1": bb.x1,
                                        "y1": bb.y1,
                                        "x2": bb.x2,
                                        "y2": bb.y2,
                                    }
                                    for bb in detection.bounding_boxes
                                ],
                            }
                            return detection_dict
                        else:
                            raise HTTPException(
                                status_code=500,
                                detail="Detection processed but not found in database",
                            )
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Detection failed: {job_result.error_message}",
                    )
            else:
                # Timeout occurred
                raise HTTPException(
                    status_code=408,
                    detail=f"Detection timed out after {timeout} seconds",
                )

        except Exception as redis_error:
            print(f"Redis error: {redis_error}")
            raise HTTPException(
                status_code=408, detail=f"Detection timed out after {timeout} seconds"
            )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error processing request: {str(e)}"
        print(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@app.websocket("/ws/detect")
async def websocket_detect(websocket: WebSocket):
    """WebSocket endpoint for real-time object detection"""
    await websocket.accept()

    try:
        while True:
            # Receive image data from client
            data = await websocket.receive_json()

            if "image" not in data:
                await websocket.send_json({"error": "No image data provided"})
                continue

            # Here you would typically authenticate the WebSocket connection
            # For now, we'll use a dummy user_id and api_key_id
            user_id = data.get("user_id", 1)
            api_key_id = data.get("api_key_id", 1)

            # Log the API call
            with SessionLocal() as db:
                log_entry = log_api_call(
                    db=db,
                    log_data=ApiLogCreate(
                        user_id=user_id,
                        api_key_id=api_key_id,
                        endpoint="/ws/detect",
                        request_size=len(data["image"]),
                        status_code=202,
                        model_name="queued",
                    ),
                )

                # Create job payload
                job_payload = JobCreate(
                    job_id=log_entry.id,  # type: ignore
                    image=data["image"],
                )

                # Push job to Redis queue
                redis_conn = get_redis_connection()
                redis_conn.lpush(REDIS_DETECTION_QUEUE, job_payload.model_dump_json())

                # Send acknowledgment
                await websocket.send_json(
                    {
                        "job_id": log_entry.id,
                        "status": "queued",
                        "message": "Image queued for processing",
                    }
                )

                # Wait for results
                result_key = f"result_{log_entry.id}"
                result_data = redis_conn.brpop([result_key], timeout=30)

                if result_data:
                    result_json = result_data[1]  # type: ignore
                    job_result = JobResult.model_validate_json(result_json)

                    if job_result.success:
                        # Fetch detection from database
                        detection = (
                            db.query(DetectionModel)
                            .filter(DetectionModel.job_id == log_entry.id)
                            .first()
                        )

                        if detection:
                            # Send results to client
                            await websocket.send_json(
                                {
                                    "job_id": log_entry.id,
                                    "status": "completed",
                                    "detection": {
                                        "id": detection.id,
                                        "model_name": detection.model_name,
                                        "image_width": detection.image_width,
                                        "image_height": detection.image_height,
                                        "processing_time": detection.processing_time,
                                        "bounding_boxes": [
                                            {
                                                "class_name": bb.class_name,
                                                "confidence": bb.confidence,
                                                "x1": bb.x1,
                                                "y1": bb.y1,
                                                "x2": bb.x2,
                                                "y2": bb.y2,
                                            }
                                            for bb in detection.bounding_boxes
                                        ],
                                    },
                                }
                            )
                        else:
                            await websocket.send_json(
                                {
                                    "job_id": log_entry.id,
                                    "status": "error",
                                    "error": "Detection processed but not found in database",
                                }
                            )
                    else:
                        await websocket.send_json(
                            {
                                "job_id": log_entry.id,
                                "status": "error",
                                "error": job_result.error_message,
                            }
                        )
                else:
                    await websocket.send_json(
                        {
                            "job_id": log_entry.id,
                            "status": "timeout",
                            "error": "Detection timed out",
                        }
                    )

    except WebSocketDisconnect:
        print("WebSocket client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.send_json({"status": "error", "error": str(e)})


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
