from datetime import datetime, UTC
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Dict, Optional

import secrets
import string

from src.database import get_db, User, APIKey
from src.schemas import AuthenticateResponse, ApiKeyAuthenticateResponse


def verify_api_key(api_key: str, db: Session) -> ApiKeyAuthenticateResponse:
    """Verify an API key.
    Returns a dictionary containing the API key and the associated user.
    Raises an HTTPException if the API key is invalid or expired.
    """
    # Defensive programming: strip whitespace from the key
    clean_api_key = api_key.strip()

    db_api_key = (
        db.query(APIKey)
        .filter(APIKey.key == clean_api_key, APIKey.is_active == True)
        .first()
    )

    if not db_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "APIKey"},
        )

    if db_api_key.expires_at is not None and db_api_key.expires_at.replace(
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

    return ApiKeyAuthenticateResponse(
        user_id=getattr(user, "id"),
        api_key_id=getattr(db_api_key, "id"),
    )


def generate_api_key(length=32) -> str:
    """Generate a random API key."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def authenticate_request(
    request: Request, db: Session = Depends(get_db)
) -> AuthenticateResponse:
    """
    Authenticate a request using an API key from the 'X-API-Key' header.
    Returns an AuthenticateResponse object with user_id and api_key_id.
    Raises an HTTPException with status code 401 if authentication fails.
    """
    api_key = request.headers.get("x-api-key")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "APIKey"},
        )
    try:
        api_key_data = verify_api_key(api_key, db)
        return AuthenticateResponse(
            user_id=api_key_data.user_id,
            api_key_id=api_key_data.api_key_id,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during authentication.",
        )
