import os
from fastapi import UploadFile
from PIL import Image, ImageDraw, ImageFont
from typing import List

from src.schemas import Detection  # Assuming Detection is defined here


# Helper function to draw bounding boxes
def draw_boxes(image: Image.Image, detections: List[Detection]) -> Image.Image:
    draw = ImageDraw.Draw(image)

    # Try to load a font, with fallbacks
    font_size = 30
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size
        )
    except IOError:
        # Fallback to default font
        font = ImageFont.load_default()

    for detection in detections:
        box = detection.box
        confidence = detection.confidence
        class_name = detection.class_name

        # Draw rectangle with thinner lines
        draw.rectangle(box, outline="red", width=3)

        # Draw label with smaller text and background
        label = f"{class_name} {confidence:.2f}"

        # Get text dimensions
        try:
            left, top, right, bottom = draw.textbbox((0, 0), label, font=font)
            text_width = right - left
            text_height = bottom - top
        except AttributeError:
            # For older Pillow versions
            text_width, text_height = draw.textsize(label, font=font)

        # Smaller padding around text
        padding = 8

        # Draw background rectangle for text with smaller padding
        draw.rectangle(
            [
                (box[0] - padding, box[1] - text_height - padding),
                (box[0] + text_width + padding, box[1] + padding),
            ],
            fill="red",
        )

        # Draw text with smaller padding
        draw.text(
            (box[0] - padding + 3, box[1] - text_height - padding + 3),
            label,
            fill="white",
            font=font,
        )

    return image


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
