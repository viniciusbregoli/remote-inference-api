import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional
from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont
import io

app = FastAPI(title="YOLO Object Detection API")

# Load YOLO model
model = None


class Detection(BaseModel):
    box: List[float]
    confidence: float
    class_name: str


class ModelLoadRequest(BaseModel):
    model_name: str = "yolov8n.pt"


def draw_boxes(image: Image.Image, detections: List[Detection]) -> Image.Image:
    draw = ImageDraw.Draw(image)

    # Try to load a smaller font size
    try:
        # Calculate font size based on image dimensions - reduced further
        font_size = 30
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        # If Arial is not available, try to find any available font
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size
            )
        except:
            font = ImageFont.load_default()

    for detection in detections:
        box = detection.box
        confidence = detection.confidence
        class_name = detection.class_name

        # Draw rectangle with thinner lines
        draw.rectangle(box, outline="red", width=3)

        # Draw label with smaller text and background
        label = f"{class_name} {confidence:.2f}"

        # Get text size using the correct method
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
    return {"status": "healthy"}


@app.post("/load_model")
async def load_model(request: ModelLoadRequest):
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
    global model

    if model is None:
        raise HTTPException(
            status_code=400, detail="No model loaded. Call /load_model first"
        )

    try:
        # Get image from request
        img = Image.open(io.BytesIO(await image.read()))

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

        # Return the image
        return FileResponse(
            temp_path, media_type="image/jpeg", filename="annotated_image.jpg"
        )

        # Delete the temporary file
        os.remove(temp_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
