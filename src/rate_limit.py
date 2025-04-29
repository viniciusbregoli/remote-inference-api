from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, Depends, status

from database import get_db, User, RateLimit, UsageLog
from auth import verify_api_key


# Check if a user has exceeded their rate limits
def check_rate_limits(user_id: int, db: Session):
    # Get user's rate limits
    rate_limit = db.query(RateLimit).filter(RateLimit.user_id == user_id).first()

    # If no rate limit entry exists for this user, create one with default values
    if not rate_limit:
        rate_limit = RateLimit(user_id=user_id)
        db.add(rate_limit)
        db.commit()
        db.refresh(rate_limit)

    # Get the start of today and the start of the current month
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = datetime.now().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    # Count daily and monthly usage
    daily_usage = (
        db.query(func.count(UsageLog.id))
        .filter(UsageLog.user_id == user_id, UsageLog.timestamp >= today_start)
        .scalar()
    )

    monthly_usage = (
        db.query(func.count(UsageLog.id))
        .filter(UsageLog.user_id == user_id, UsageLog.timestamp >= month_start)
        .scalar()
    )

    # Check if limits have been exceeded
    if daily_usage >= rate_limit.daily_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily limit of {rate_limit.daily_limit} requests exceeded. Limit resets at midnight UTC.",
        )

    if monthly_usage >= rate_limit.monthly_limit:
        # Calculate days until the next month
        next_month = month_start + timedelta(days=32)
        next_month_start = next_month.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        days_until_reset = (next_month_start - datetime.now()).days

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Monthly limit of {rate_limit.monthly_limit} requests exceeded. Limit resets in {days_until_reset} days.",
        )

    # Return the usage statistics
    return {
        "daily_usage": daily_usage,
        "monthly_usage": monthly_usage,
        "daily_limit": rate_limit.daily_limit,
        "monthly_limit": rate_limit.monthly_limit,
        "daily_percentage": (daily_usage / rate_limit.daily_limit) * 100,
        "monthly_percentage": (monthly_usage / rate_limit.monthly_limit) * 100,
    }


# Dependency to check rate limits using API key
def check_rate_limits_with_api_key(
    api_key_data=Depends(verify_api_key), db: Session = Depends(get_db)
):
    user = api_key_data["user"]
    return check_rate_limits(user.id, db)


# Log API usage
def log_api_usage(
    user_id: int,
    api_key_id: int,
    endpoint: str,
    request_size: int,
    processing_time: float,
    status_code: int,
    model_id: int = None,
    request_ip: str = None,
    user_agent: str = None,
    db: Session = Depends(get_db),
):
    log_entry = UsageLog(
        user_id=user_id,
        api_key_id=api_key_id,
        model_id=model_id,
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


# Get user statistics
def get_user_stats(user_id: int, db: Session = Depends(get_db)):
    # Get rate limits
    rate_limit = db.query(RateLimit).filter(RateLimit.user_id == user_id).first()

    if not rate_limit:
        rate_limit = RateLimit(user_id=user_id)
        db.add(rate_limit)
        db.commit()
        db.refresh(rate_limit)

    # Get usage counts
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = datetime.now().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    daily_usage = (
        db.query(func.count(UsageLog.id))
        .filter(UsageLog.user_id == user_id, UsageLog.timestamp >= today_start)
        .scalar()
    )

    monthly_usage = (
        db.query(func.count(UsageLog.id))
        .filter(UsageLog.user_id == user_id, UsageLog.timestamp >= month_start)
        .scalar()
    )

    return {
        "daily_usage": daily_usage,
        "monthly_usage": monthly_usage,
        "daily_limit": rate_limit.daily_limit,
        "monthly_limit": rate_limit.monthly_limit,
        "daily_percentage": (
            (daily_usage / rate_limit.daily_limit) * 100
            if rate_limit.daily_limit > 0
            else 0
        ),
        "monthly_percentage": (
            (monthly_usage / rate_limit.monthly_limit) * 100
            if rate_limit.monthly_limit > 0
            else 0
        ),
    }
