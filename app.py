import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont
import io
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the model when the application starts"""
    global model
    try:
        print(f"Loading {DEFAULT_MODEL} on startup...")
        model = YOLO(DEFAULT_MODEL)
        print(f"Model {DEFAULT_MODEL} loaded successfully!")
    except Exception as e:
        print(f"ERROR loading model on startup: {str(e)}")
    yield


app = FastAPI(title="YOLO Object Detection API", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define model name
DEFAULT_MODEL = "yolov8n.pt"

# Load YOLO model on startup
model = None


class Detection(BaseModel):
    box: List[float]  # [x1, y1, x2, y2]
    confidence: float  # 0-1
    class_name: str  # "person", "car", "dog", etc.


class ModelLoadRequest(BaseModel):
    model_name: str = DEFAULT_MODEL


def draw_boxes(image: Image.Image, detections: List[Detection]) -> Image.Image:
    draw = ImageDraw.Draw(image)

    # Try to load a font, with fallbacks
    font_size = 30

    font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size
    )

    for detection in detections:
        box = detection.box
        confidence = detection.confidence
        class_name = detection.class_name

        # Draw rectangle with thinner lines
        draw.rectangle(box, outline="red", width=3)

        # Draw label with smaller text and background
        label = f"{class_name} {confidence:.2f}"

        left, top, right, bottom = draw.textbbox((0, 0), label, font=font)
        text_width = right - left
        text_height = bottom - top

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


@app.get("/health")
async def health_check():
    """Check if the API is healthy and if the model is loaded"""
    global model
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "model_name": DEFAULT_MODEL if model is not None else None,
    }


@app.post("/load_model")
async def load_model(request: ModelLoadRequest):
    """Explicitly load or reload a model"""
    global model

    try:
        model = YOLO(request.model_name)
        return {
            "status": "success",
            "message": f"Model {request.model_name} loaded successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/detect")
async def detect_objects(image: UploadFile = File(...)):
    """Detect objects in the uploaded image"""
    global model

    try:
        # Get image from request
        img_data = await image.read()
        img = Image.open(io.BytesIO(img_data))

        # Run inference
        results = model(img)

        # Process results
        result_data = []
        for result in results:
            boxes = result.boxes.cpu().numpy()
            for i, box in enumerate(boxes):
                result_data.append(
                    Detection(
                        box=box.xyxy[0].tolist(),
                        confidence=float(box.conf[0]),
                        class_name=result.names[int(box.cls[0])],
                    )
                )

        # Draw boxes on image
        annotated_img = draw_boxes(img.copy(), result_data)

        # Save image to bytes
        img_byte_arr = io.BytesIO()
        annotated_img.save(img_byte_arr, format="JPEG")
        img_byte_arr.seek(0)

        # Save the image temporarily
        temp_path = "annotated_image.jpg"
        with open(temp_path, "wb") as f:
            f.write(img_byte_arr.getvalue())

        # Return the image as a file response ( in the format of a blob )
        return FileResponse(
            temp_path, media_type="image/jpeg", filename="annotated_image.jpg"
        )

        # Delete the temporary file
        os.remove(temp_path)

    except Exception as e:
        error_msg = f"Error processing image: {str(e)}"
        print(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
