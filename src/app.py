import os
import time
from fastapi import (
    FastAPI,
    File,
    UploadFile,
    HTTPException,
    Depends,
    Request,
    BackgroundTasks,
)
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import io
from contextlib import asynccontextmanager
from datetime import timedelta

from routes.apikeys import router as apikeys_router
from routes.users import router as users_router
from src.database import get_db, create_tables, init_db, User, Model, UsageLog
from src.schemas import (
    ModelCreate,
    Model as ModelSchema,
    Detection,
    Token,
)
from src.auth import (
    authenticate_user,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_active_admin,
    verify_api_key,
)
from src.rate_limit import check_rate_limits_with_api_key, log_api_usage
from src.utils import draw_boxes, get_image_size

# Import YOLO model
from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont

# Model instance
MODEL = None
DEFAULT_MODEL_NAME = "yolov8n"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global MODEL

    # Initialize database
    create_tables()
    init_db()

    # Load default model
    db = next(get_db())
    default_model = db.query(Model).filter(Model.name == DEFAULT_MODEL_NAME).first()

    if default_model and default_model.is_active:
        try:
            print(f"Loading {default_model.name} on startup...")
            MODEL = YOLO(default_model.file_path)
            print(f"Model {default_model.name} loaded successfully!")
        except Exception as e:
            print(f"ERROR loading model on startup: {str(e)}")

    yield

    # Cleanup on shutdown
    print("Shutting down application...")


app = FastAPI(
    title="YOLO Object Detection API",
    description="API for object detection using YOLOv8 models",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(apikeys_router)
app.include_router(users_router)
# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Endpoints
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Check if the API is healthy and if the model is loaded"""
    global MODEL

    # Check database connection
    try:
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    # Get loaded model info
    model_info = None
    if MODEL is not None:
        try:
            model_name = (
                db.query(Model).filter(Model.file_path == MODEL.ckpt_path).first()
            )
            model_info = model_name.name if model_name else "unknown"
        except Exception:
            model_info = "unknown"

    return {
        "status": "healthy",
        "database": db_status,
        "model_loaded": MODEL is not None,
        "model_name": model_info,
    }


@app.post("/token", response_model=Token, tags=["authentication"])
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """Login to get access token"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "is_admin": user.is_admin},
        expires_delta=access_token_expires,
    )

    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/models/", response_model=ModelSchema)
async def create_model(
    model: ModelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Register a new model (admin only)"""
    # Check if model with this name already exists
    existing_model = db.query(Model).filter(Model.name == model.name).first()

    if existing_model:
        raise HTTPException(
            status_code=400, detail="Model with this name already exists"
        )

    # Create new model
    db_model = Model(
        name=model.name, file_path=model.file_path, description=model.description
    )

    db.add(db_model)
    db.commit()
    db.refresh(db_model)

    return db_model


@app.post("/load_model")
async def load_model(
    model_name: str, db: Session = Depends(get_db), api_key_data=Depends(verify_api_key)
):
    """Load a specific model for object detection"""
    global MODEL

    # Check rate limits
    check_rate_limits_with_api_key(api_key_data, db)

    start_time = time.time()

    # Get the model from database
    db_model = (
        db.query(Model)
        .filter(Model.name == model_name, Model.is_active == True)
        .first()
    )

    if not db_model:
        end_time = time.time()
        processing_time = end_time - start_time

        # Log the failed request
        log_api_usage(
            user_id=api_key_data["user"].id,
            api_key_id=api_key_data["api_key"].id,
            endpoint="/load_model",
            request_size=len(model_name),
            processing_time=processing_time,
            status_code=404,
            db=db,
        )

        raise HTTPException(status_code=404, detail="Model not found or not active")

    try:
        MODEL = YOLO(db_model.file_path)

        end_time = time.time()
        processing_time = end_time - start_time

        # Log the successful request
        log_api_usage(
            user_id=api_key_data["user"].id,
            api_key_id=api_key_data["api_key"].id,
            endpoint="/load_model",
            request_size=len(model_name),
            processing_time=processing_time,
            status_code=200,
            model_id=db_model.id,
            db=db,
        )

        return {
            "status": "success",
            "message": f"Model {model_name} loaded successfully",
            "processing_time": processing_time,
        }
    except Exception as e:
        end_time = time.time()
        processing_time = end_time - start_time

        # Log the failed request
        log_api_usage(
            user_id=api_key_data["user"].id,
            api_key_id=api_key_data["api_key"].id,
            endpoint="/load_model",
            request_size=len(model_name),
            processing_time=processing_time,
            status_code=500,
            model_id=db_model.id,
            db=db,
        )

        raise HTTPException(status_code=500, detail=str(e))


@app.post("/detect")
async def detect_objects(
    image: UploadFile = File(...),
    request: Request = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    api_key_data=Depends(verify_api_key),
):
    """Detect objects in the uploaded image"""
    global MODEL

    # Check if model is loaded
    if MODEL is None:
        raise HTTPException(
            status_code=500, detail="No model loaded. Please load a model first."
        )

    # Check rate limits
    check_rate_limits_with_api_key(api_key_data, db)

    start_time = time.time()
    request_size = get_image_size(image)

    try:
        # Get image from request
        img_data = await image.read()
        img = Image.open(io.BytesIO(img_data))

        # Get current model from database
        current_model = (
            db.query(Model).filter(Model.file_path == MODEL.ckpt_path).first()
        )

        # Run inference
        results = MODEL(img)

        # Process results
        detection_results = []
        for result in results:
            boxes = result.boxes.cpu().numpy()
            for i, box in enumerate(boxes):
                detection_results.append(
                    Detection(
                        box=box.xyxy[0].tolist(),
                        confidence=float(box.conf[0]),
                        class_name=result.names[int(box.cls[0])],
                    )
                )

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

        # Log the successful request in background
        if background_tasks:
            background_tasks.add_task(
                log_api_usage,
                user_id=api_key_data["user"].id,
                api_key_id=api_key_data["api_key"].id,
                endpoint="/detect",
                request_size=request_size,
                processing_time=processing_time,
                status_code=200,
                model_id=current_model.id if current_model else None,
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
        if background_tasks:
            background_tasks.add_task(
                log_api_usage,
                user_id=api_key_data["user"].id,
                api_key_id=api_key_data["api_key"].id,
                endpoint="/detect",
                request_size=request_size,
                processing_time=processing_time,
                status_code=500,
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
