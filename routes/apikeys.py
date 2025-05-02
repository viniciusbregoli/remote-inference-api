from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from src.database import get_db, APIKey as APIKeyModel, User
from src.schemas import APIKeyCreate, APIKey
from src.auth import get_current_user, get_current_active_admin, generate_api_key

router = APIRouter(
    prefix="/api-keys",
    tags=["api-keys"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=APIKey)
def create_api_key(
    api_key: APIKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),  # Changed from get_current_active_admin
):
    # Check if the user is authorized to create keys for this user_id
    if not current_user.is_admin and current_user.id != api_key.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create API keys for yourself unless you're an admin",
        )

    # Check if the user exists
    user = db.query(User).filter(User.id == api_key.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Generate a new API key
    key = generate_api_key()

    # Set default expiration date to 1 year from now if not provided
    if not api_key.expires_at:
        expires_at = datetime.utcnow() + timedelta(days=365)
    else:
        expires_at = api_key.expires_at

    # Create new API key in database
    db_api_key = APIKeyModel(
        user_id=api_key.user_id, key=key, name=api_key.name, expires_at=expires_at
    )

    db.add(db_api_key)
    db.commit()
    db.refresh(db_api_key)

    return db_api_key


@router.get("/", response_model=List[APIKey])
def read_api_keys(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Get all API keys (admin only)"""
    # Modified to include user information
    api_keys = db.query(APIKeyModel).offset(skip).limit(limit).all()

    # Add user information
    for key in api_keys:
        user = db.query(User).filter(User.id == key.user_id).first()
        if user:
            key.user_username = user.username

    return api_keys


@router.get("/user/{user_id}", response_model=List[APIKey])
def read_user_api_keys(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all API keys for a specific user

    - Admin users can view keys for any user
    - Regular users can only view their own keys
    """
    # Check if current user is admin or the user being requested
    if not current_user.is_admin and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    # Check if the user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    api_keys = db.query(APIKeyModel).filter(APIKeyModel.user_id == user_id).all()
    return api_keys


@router.get("/me", response_model=List[APIKey])
def read_my_api_keys(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get all API keys for the current user"""
    api_keys = (
        db.query(APIKeyModel).filter(APIKeyModel.user_id == current_user.id).all()
    )
    return api_keys


@router.get("/{api_key_id}", response_model=APIKey)
def read_api_key(
    api_key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific API key by ID

    - Admin users can view any key
    - Regular users can only view their own keys
    """
    # Get the API key
    db_api_key = db.query(APIKeyModel).filter(APIKeyModel.id == api_key_id).first()

    if not db_api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    # Check permissions
    if not current_user.is_admin and db_api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    return db_api_key


@router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(
    api_key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete an API key

    - Admin users can delete any key
    - Regular users can only delete their own keys
    """
    # Get the API key
    db_api_key = db.query(APIKeyModel).filter(APIKeyModel.id == api_key_id).first()

    if not db_api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    # Check permissions
    if not current_user.is_admin and db_api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    # Delete the API key
    db.delete(db_api_key)
    db.commit()

    return None


@router.put("/{api_key_id}/deactivate", response_model=APIKey)
def deactivate_api_key(
    api_key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Deactivate an API key

    - Admin users can deactivate any key
    - Regular users can only deactivate their own keys
    """
    # Get the API key
    db_api_key = db.query(APIKeyModel).filter(APIKeyModel.id == api_key_id).first()

    if not db_api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    # Check permissions
    if not current_user.is_admin and db_api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    # Deactivate the API key
    db_api_key.is_active = False
    db.commit()
    db.refresh(db_api_key)

    return db_api_key


@router.put("/{api_key_id}/activate", response_model=APIKey)
def activate_api_key(
    api_key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Activate an API key

    - Admin users can activate any key
    - Regular users can only activate their own keys
    """
    # Get the API key
    db_api_key = db.query(APIKeyModel).filter(APIKeyModel.id == api_key_id).first()

    if not db_api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    # Check permissions
    if not current_user.is_admin and db_api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    # Check if the key has expired
    if db_api_key.expires_at and db_api_key.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key has expired and cannot be activated",
        )

    # Activate the API key
    db_api_key.is_active = True
    db.commit()
    db.refresh(db_api_key)

    return db_api_key
