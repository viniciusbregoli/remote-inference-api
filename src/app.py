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
from jose import JWTError, jwt

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
    get_current_user,
    SECRET_KEY,
    ALGORITHM,
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



@app.post("/detect")
async def detect_objects(
    image: UploadFile = File(...),
    request: Request = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    global MODEL

    # Get user either from JWT token or API key
    user_id = None
    model_id = None
    api_key_data = None

    # Try to get API key authentication first
    try:
        api_key = request.headers.get("x-api-key")
        if api_key:
            api_key_data = verify_api_key(api_key, db)
            user_id = api_key_data["user"].id

            # Check rate limits for API key users
            check_rate_limits_with_api_key(api_key_data, db)
    except HTTPException:
        # If API key auth fails, try JWT token auth
        pass

    # If no API key or API key auth failed, try JWT token
    if not user_id:
        try:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")

                # Verify the JWT token
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                username: str = payload.get("sub")

                if username:
                    # Get the user from the database
                    current_user = (
                        db.query(User).filter(User.username == username).first()
                    )
                    if current_user and current_user.is_active:
                        user_id = current_user.id
        except Exception as e:
            print(f"JWT verification error: {e}")

    # If no authentication succeeded, return 401
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide a valid API key or JWT token.",
            headers={"WWW-Authenticate": "Bearer or APIKey"},
        )

    # Check if model is loaded
    if MODEL is None:
        raise HTTPException(
            status_code=500, detail="No model loaded. Please load a model first."
        )

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
        if current_model:
            model_id = current_model.id

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
                user_id=user_id,
                api_key_id=api_key_data["api_key"].id if api_key_data else None,
                endpoint="/detect",
                request_size=request_size,
                processing_time=processing_time,
                status_code=200,
                model_id=model_id,
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
                user_id=user_id,
                api_key_id=api_key_data["api_key"].id if api_key_data else None,
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
