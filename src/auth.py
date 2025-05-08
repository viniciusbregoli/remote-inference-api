from datetime import datetime, timedelta, UTC
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Optional, Tuple, Union

import secrets
import string
import os
from dotenv import load_dotenv

from src.database import get_db, User, APIKey
from src.schemas import TokenData

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")  # endpoint for token

api_key_header = APIKeyHeader(name="X-API-Key")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_context.hash(password)


def create_access_token(data: TokenData) -> str:
    to_encode = data.model_dump()
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = db.query(User).filter(func.lower(User.username) == username.lower()).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# Token verification
def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("username")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token_data = TokenData(username=username)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.username == token_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# Admin check
def get_current_active_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user


# API Key verification
def verify_api_key(
    api_key: str = Depends(api_key_header), db: Session = Depends(get_db)
):
    """Verify an API key.
    Returns a dictionary containing the API key and the associated user.
    Raises an HTTPException if the API key is invalid or expired.
    """
    db_api_key = (
        db.query(APIKey).filter(APIKey.key == api_key, APIKey.is_active == True).first()
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


# Generate a random API key
def generate_api_key(length=32) -> str:
    """Generate a random API key."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


# Authenticate request using either API key or JWT token
def authenticate_request(
    request: Request, db: Session
) -> Tuple[Optional[int], Optional[Dict]]:
    """
    Authenticate a request using either API key or JWT token.
    Returns a tuple of (user_id, api_key_data) where api_key_data is None if JWT token was used.
    Raises an HTTPException with status code 401 if authentication fails.
    """
    # Try API key authentication first
    api_key_data = None
    # Step 1: Try API key authentication
    api_key = request.headers.get("x-api-key")
    if api_key:
        try:
            api_key_data = verify_api_key(api_key, db)
            return api_key_data["user"].id, api_key_data
        except HTTPException:
            # If API key auth fails, we'll try JWT token auth next
            pass

    # Step 2: Try JWT token authentication
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
        try:
            # Verify the JWT token
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("username")

            if username:
                current_user = db.query(User).filter(User.username == username).first()
                if current_user and current_user.is_active:
                    return current_user.id, None
        except Exception:
            # JWT verification failed, continue to the next authentication method
            pass

    # If we reach here, no authentication method succeeded
    raise HTTPException(
        status_code=401,
        detail="Authentication required. Please provide a valid API key or JWT token.",
        headers={"WWW-Authenticate": "Bearer or APIKey"},
    )
