import os
import time
import base64
import hashlib
from redis.asyncio import Redis
from PIL import Image
import io
from ultralytics import YOLO
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import asyncio
from sqlalchemy.orm import Session
import torch
from ultralytics.nn import tasks

from src.database import SessionLocal, ApiLog, Detection, BoundingBox
from src.schemas import JobProcess, JobResult


# Gambiarra para carregar o modelo com weights_only=False
def torch_safe_load(file):
    """Load a PyTorch model with weights_only=False."""
    return torch.load(file, map_location="cpu", weights_only=False), file

tasks.torch_safe_load = torch_safe_load

# Redis and model configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_QUEUE = "detection_jobs"
MODELS_DIR = Path("models")
DEFAULT_MODEL = "yolov8n"


class GPUWorker:
    def __init__(self):
        self.redis_conn: Optional[Redis] = None
        self.model: YOLO = self.load_model()
        self.model_name = DEFAULT_MODEL

    def load_model(self) -> YOLO:
        """Load the YOLO model"""

        model_path = MODELS_DIR / f"{DEFAULT_MODEL}.pt"
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found at {model_path}")
        return YOLO(str(model_path))

    async def init_redis(self):
        """Initialize Redis connection"""
        self.redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    def process_image(
        self, image_data: str
    ) -> Tuple[list[Dict[str, Any]], int, int, str]:
        """Process an image using the loaded model"""
        # Convert base64 to image
        img_bytes = base64.b64decode(image_data)
        img = Image.open(io.BytesIO(img_bytes))
        width, height = img.size

        # Run inference
        results = self.model(img)

        # Process results
        detections: list[Dict[str, Any]] = []
        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                assert self.model.names is not None
                class_name = self.model.names[cls]
                detections.append(
                    {
                        "class_name": class_name,
                        "confidence": conf,
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                    }
                )

        image_hash = hashlib.sha256(image_data.encode()).hexdigest()

        return detections, width, height, image_hash

    def store_detection_results_in_db(
        self,
        db: Session,
        job_id: int,
        model_name: str,
        width: int,
        height: int,
        image_hash: str,
        processing_time: float,
        detections: list[Dict[str, Any]],
    ):
        """Store detection results in the database"""
        # Get the ApiLog entry
        api_log_entry = db.query(ApiLog).filter(ApiLog.id == job_id).first()
        if not api_log_entry:
            print(f"ApiLog with id {job_id} not found.")
            return

        # Update ApiLog with model name and status code
        db.query(ApiLog).filter(ApiLog.id == job_id).update(
            {"model_name": model_name, "status_code": 200}
        )

        # Create Detection entry
        detection_entry = Detection(
            job_id=job_id,
            model_name=model_name,
            image_width=width,
            image_height=height,
            image_hash=image_hash,
            processing_time=processing_time,
        )
        db.add(detection_entry)
        db.commit()
        db.refresh(detection_entry)

        # Create BoundingBox entries
        for det in detections:
            bbox_entry = BoundingBox(detection_id=detection_entry.id, **det)
            db.add(bbox_entry)

        db.commit()

    async def run(self):
        """Main worker loop"""
        await self.init_redis()
        if not self.redis_conn:
            raise RuntimeError("Redis connection not initialized")

        print("GPU Worker started. Waiting for jobs...")

        while True:
            try:
                # Get job from queue (blocking)
                job_data = await self.redis_conn.brpop(REDIS_QUEUE)  # type: ignore

                if job_data:
                    job_json = job_data[1]

                    # Parse and validate job using schema
                    try:
                        job = JobProcess.model_validate_json(job_json)
                    except Exception as e:
                        print(f"Invalid job format: {e}")
                        continue

                    print(f"Processing job {job.job_id}")
                    start_time = time.time()

                    try:
                        # Process the image
                        detections, width, height, image_hash = self.process_image(
                            job.image
                        )
                        processing_time = time.time() - start_time

                        # Store results in database
                        with SessionLocal() as db:
                            self.store_detection_results_in_db(
                                db,
                                job.job_id,
                                self.model_name,
                                width,
                                height,
                                image_hash,
                                processing_time,
                                detections,
                            )

                        # Create successful job result
                        result = JobResult(
                            job_id=job.job_id,
                            success=True,
                            processing_time=processing_time,
                            detections_count=len(detections),
                        )

                        # Publish result to Redis
                        result_key = f"result_{job.job_id}"
                        await self.redis_conn.lpush(
                            result_key, result.model_dump_json()
                        )  # type: ignore

                        print(
                            f"Processed job {job.job_id} with {len(detections)} detections in {processing_time:.4f}s"
                        )

                    except Exception as processing_error:
                        # Create failed job result
                        result = JobResult(
                            job_id=job.job_id,
                            success=False,
                            error_message=str(processing_error),
                        )

                        # Publish error result to Redis
                        result_key = f"result_{job.job_id}"
                        await self.redis_conn.lpush(
                            result_key, result.model_dump_json()
                        )  # type: ignore

                        print(f"Error processing job {job.job_id}: {processing_error}")

            except Exception as e:
                print(f"Error in worker loop: {e}")
                time.sleep(1)  # Prevent tight loop on errors


if __name__ == "__main__":
    worker = GPUWorker()
    asyncio.run(worker.run())
