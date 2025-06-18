import os
from fastapi import UploadFile
from PIL import Image, ImageDraw, ImageFont
from typing import List, Any
import redis
from src.schemas import BoundingBoxBase, ApiLogCreate, ApiLogInDB as ApiLogSchema
from sqlalchemy.orm import Session
from src.database import ApiLog as ApiLogModel


def get_redis_connection(redis_pool: redis.ConnectionPool):
    """Get Redis connection from pool"""
    return redis.Redis(connection_pool=redis_pool)


def log_api_call(db: Session, log_data: ApiLogCreate) -> ApiLogSchema:
    """
    Logs an API call to the database and returns the Pydantic model.
    """
    # Create SQLAlchemy model
    log_entry = ApiLogModel(**log_data.model_dump())
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    # Convert SQLAlchemy model to Pydantic schema
    return ApiLogSchema.model_validate(log_entry)


def draw_boxes(image: Image.Image, detections: List[BoundingBoxBase]) -> Image.Image:
    """
    Draw bounding boxes on an image.
    """
    draw = ImageDraw.Draw(image)
    image_width, image_height = image.size

    font_size = min(image_width, image_height) // 30
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size
        )
    except IOError:
        font = ImageFont.load_default()

    for detection in detections:
        box = [detection.x1, detection.y1, detection.x2, detection.y2]
        confidence = detection.confidence
        class_name = detection.class_name

        draw.rectangle(box, outline="red", width=3)

        label = f"{class_name} {confidence:.2f}"

        left, top, right, bottom = draw.textbbox((0, 0), label, font=font)
        text_width = right - left
        text_height = bottom - top

        padding = 8

        draw.rectangle(
            [
                (box[0] - padding, box[1] - text_height - padding),
                (box[0] + text_width + padding, box[1] + padding),
            ],
            fill="red",
        )

        draw.text(
            (box[0] - padding + 3, box[1] - text_height - padding + 3),
            label,
            fill="white",
            font=font,
        )

    return image


# Process model results into BoundingBox objects
def process_detection_results(results: List[Any]) -> List[BoundingBoxBase]:
    """
    Process the raw model results into a list of BoundingBox objects.

    Args:
        results: The raw output from the YOLO model

    Returns:
        A list of BoundingBox objects with bounding boxes, confidence scores, and class names
    """
    detection_results = []

    for result in results:
        boxes = result.boxes.cpu().numpy()
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            detection_results.append(
                BoundingBoxBase(
                    class_name=result.names[int(box.cls[0])],
                    confidence=float(box.conf[0]),
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                )
            )

    return detection_results


# Calculate image size in bytes
def get_image_size(image: UploadFile) -> int:
    # Get the file size
    try:
        image.file.seek(0, os.SEEK_END)
        file_size = image.file.tell()
        image.file.seek(0)  # Reset file position
        return file_size
    except Exception:
        return 0
