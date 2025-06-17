import os
import time
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

from src.database import get_db, create_tables
from src.auth import (
    authenticate_request,
)
from src.usage_logger import log_api_usage
from src.utils import draw_boxes, get_image_size, process_detection_results
from src.model_manager import ModelManager

from PIL import Image


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    create_tables()

    model_manager = ModelManager()
    model_manager.load_model("yolov8n")

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


@app.post("/detect")
async def detect_objects(
    image: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
):
    # Authenticate the request - this will raise an HTTPException if authentication fails
    user_id, api_key_data = authenticate_request(request, db)

    # Get the current model already initialized in lifespan
    model_manager = ModelManager()
    model, model_name = model_manager.get_current_model()

    # Check if model is loaded
    if not model:
        raise HTTPException(
            status_code=500, detail="No model loaded. Please load a model first."
        )

    start_time = time.time()
    request_size = get_image_size(image)

    try:
        # Get image from request
        img_data = await image.read()
        img = Image.open(io.BytesIO(img_data))

        # Run inference
        results = model(img)

        # Process results using the helper function
        detection_results = process_detection_results(results)

        # Draw boxes on image
        annotated_img = draw_boxes(img.copy(), detection_results)

        # Save image to bytes
        img_byte_arr = io.BytesIO()
        annotated_img.save(img_byte_arr, format="JPEG")
        img_byte_arr.seek(0)

        # Save the image temporarily
        temp_path = "annotated_image.jpg"
        with open(temp_path, "wb") as f:
            f.write(img_byte_arr.getvalue())

        end_time = time.time()
        processing_time = end_time - start_time

        log_api_usage(
            user_id=user_id,
            api_key_id=api_key_data["api_key"].id if api_key_data else None,
            endpoint="/detect",
            request_size=request_size,
            processing_time=processing_time,
            status_code=200,
            model_name=model_name,
            request_ip=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None,
            db=db,
        )

        # Return the image as a file response
        return FileResponse(
            temp_path, media_type="image/jpeg", filename="annotated_image.jpg"
        )


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
            model_name=model_name,
            request_ip=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None,
            db=db,
        )

        error_msg = f"Error processing image: {str(e)}"
        print(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
