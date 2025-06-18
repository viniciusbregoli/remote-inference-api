from sqlalchemy.orm import Session
from src.database import ApiLog as ApiLogModel
from src.schemas import ApiLogCreate, ApiLog as ApiLogSchema


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
