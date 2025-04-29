from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from src.database import get_db, User
from src.schemas import UserCreate, User as UserSchema, UserStats, UserUpdate
from src.auth import (
    get_current_user,
    get_current_active_admin,
    get_password_hash,
)
from src.rate_limit import get_user_stats

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.post("/", response_model=UserSchema)
async def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_active_admin
    ),  # ensures the user is an admin
):
    """Create a new user (admin only)"""
    # Check if user with this username or email already exists
    existing_user = (
        db.query(User)
        .filter((User.username == user.username) | (User.email == user.email))
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400, detail="Username or email already registered"
        )

    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username, email=user.email, password_hash=hashed_password
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@router.get("/", response_model=List[UserSchema])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Get all users (admin only)"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.put("/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Update a user (admin only)"""
    # Check if user exists
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update fields that are provided
    if user_update.username is not None:
        # Check if username is already taken
        if user_update.username != db_user.username:
            existing_user = (
                db.query(User).filter(User.username == user_update.username).first()
            )
            if existing_user:
                raise HTTPException(status_code=400, detail="Username already taken")
        db_user.username = user_update.username

    if user_update.email is not None:
        # Check if email is already taken
        if user_update.email != db_user.email:
            existing_user = (
                db.query(User).filter(User.email == user_update.email).first()
            )
            if existing_user:
                raise HTTPException(status_code=400, detail="Email already taken")
        db_user.email = user_update.email

    if user_update.password is not None:
        db_user.password_hash = get_password_hash(user_update.password)

    if user_update.is_active is not None:
        db_user.is_active = user_update.is_active

    if user_update.is_admin is not None:
        db_user.is_admin = user_update.is_admin

    # Save changes
    db.commit()
    db.refresh(db_user)

    return db_user


@router.delete("/{user_id}", status_code=204)
async def delete_user_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Delete a user (admin only)"""
    # Check if user exists
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete user
    db.delete(db_user)
    db.commit()

    # No content response


@router.get("/me", response_model=UserSchema)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@router.get("/me/stats", response_model=UserStats)
async def read_user_stats_endpoint(  # Renamed to avoid conflict with imported function
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get current user API usage statistics"""
    return get_user_stats(current_user.id, db)


# Ensure __init__.py exists in routes directory if needed for imports
# If routes/__init__.py doesn't exist, create it:
# with open("routes/__init__.py", "w") as f:
#     pass
