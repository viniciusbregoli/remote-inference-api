from datetime import datetime, UTC
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Dict, Optional, Tuple

import secrets
import string

from src.database import get_db, User, APIKey


def verify_api_key(api_key: str, db: Session) -> Dict:
    """Verify an API key.
    Returns a dictionary containing the API key and the associated user.
    Raises an HTTPException if the API key is invalid or expired.
    """
    # Defensive programming: strip whitespace from the key
    clean_api_key = api_key.strip() if api_key else None
    
    if not clean_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "APIKey"},
        )

    db_api_key = (
        db.query(APIKey).filter(APIKey.key == clean_api_key, APIKey.is_active == True).first()
    )

    if not db_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "APIKey"},
        )

    if db_api_key.expires_at and db_api_key.expires_at.replace(
        tzinfo=UTC
    ) < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
            headers={"WWW-Authenticate": "APIKey"},
        )

    user = (
        db.query(User)
        .filter(User.id == db_api_key.user_id, User.is_active == True)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive or not found",
            headers={"WWW-Authenticate": "APIKey"},
        )

    return {"api_key": db_api_key, "user": user}


def generate_api_key(length=32) -> str:
    """Generate a random API key."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def authenticate_request(
    request: Request, db: Session
) -> Tuple[Optional[int], Optional[Dict]]:
    """
    Authenticate a request using an API key from the 'X-API-Key' header.
    Returns a tuple of (user_id, api_key_data).
    Raises an HTTPException with status code 401 if authentication fails.
    """
    api_key = request.headers.get("x-api-key")
    try:
        api_key_data = verify_api_key(api_key, db)
        return api_key_data["user"].id, api_key_data
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred during authentication."
        )
