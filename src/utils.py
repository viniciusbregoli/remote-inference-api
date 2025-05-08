import os
from fastapi import UploadFile
from PIL import Image, ImageDraw, ImageFont
from typing import List, Any

from src.schemas import Detection  # Assuming Detection is defined here


# Helper function to draw bounding boxes
def draw_boxes(image: Image.Image, detections: List[Detection]) -> Image.Image:
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
        box = detection.box
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


# Process model results into Detection objects
def process_detection_results(results: List[Any]) -> List[Detection]:
    """
    Process the raw model results into a list of Detection objects.

    Args:
        results: The raw output from the YOLO model

    Returns:
        A list of Detection objects with bounding boxes, confidence scores, and class names
    """
    detection_results = []

    for result in results:
        boxes = result.boxes.cpu().numpy()
        for box in boxes:
            detection_results.append(
                Detection(
                    box=box.xyxy[0].tolist(),
                    confidence=float(box.conf[0]),
                    class_name=result.names[int(box.cls[0])],
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
