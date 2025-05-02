from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta, UTC

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
    ),  # User does not need to be admin, but must be the owner of the API key
):
    # Check if the user exists
    user = db.query(User).filter(User.id == api_key.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    # Check if the user is authorized to create keys for this user_id
    if not current_user.is_admin and current_user.id != api_key.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create API keys for yourself unless you're an admin",
        )
    # Generate a new API key
    key = generate_api_key()

    # Set default expiration date to 1 year from now if not provided
    if not api_key.expires_at:
        expires_at = datetime.now(UTC) + timedelta(days=365)
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
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    # Modified to include user information
    api_keys = db.query(APIKeyModel).limit(limit).all()

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
    # Check permissions
    if not current_user.is_admin and db_api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    # Get the API key
    db_api_key = db.query(APIKeyModel).filter(APIKeyModel.id == api_key_id).first()

    if not db_api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    return db_api_key


@router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(
    api_key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check permissions
    if not current_user.is_admin and db_api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    # Get the API key
    db_api_key = db.query(APIKeyModel).filter(APIKeyModel.id == api_key_id).first()

    if not db_api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
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
    # Check permissions
    if not current_user.is_admin and db_api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    # Get the API key
    db_api_key = db.query(APIKeyModel).filter(APIKeyModel.id == api_key_id).first()

    if not db_api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
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
    # Check permissions
    if not current_user.is_admin and db_api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    db_api_key = db.query(APIKeyModel).filter(APIKeyModel.id == api_key_id).first()

    if not db_api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    # Compare expires_at with an offset-aware datetime
    if db_api_key.expires_at and db_api_key.expires_at.replace(
        tzinfo=UTC
    ) < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key has expired and cannot be activated",
        )

    # Activate the API key
    db_api_key.is_active = True
    db.commit()
    db.refresh(db_api_key)

    return db_api_key
