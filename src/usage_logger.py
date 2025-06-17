from sqlalchemy.orm import Session
from src.database import ApiLog
from src.schemas import ApiLogCreate


def log_api_call(db: Session, log_data: ApiLogCreate) -> ApiLog:
    """
    Logs an API call to the database.
    """
    log_entry = ApiLog(**log_data.model_dump())
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry
