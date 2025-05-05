from sqlalchemy.orm import Session
from src.database import UsageLog


def log_api_usage(
    user_id: int,
    api_key_id: int,
    endpoint: str,
    request_size: int,
    processing_time: float,
    status_code: int,
    model_name: str = None,
    request_ip: str = None,
    user_agent: str = None,
    db: Session = None,
):
    """Log API usage without rate limiting"""
    if db is None:
        return None

    log_entry = UsageLog(
        user_id=user_id,
        api_key_id=api_key_id,
        model_name=model_name,
        endpoint=endpoint,
        request_size=request_size,
        processing_time=processing_time,
        status_code=status_code,
        request_ip=request_ip,
        user_agent=user_agent,
    )

    db.add(log_entry)
    db.commit()
    return log_entry
