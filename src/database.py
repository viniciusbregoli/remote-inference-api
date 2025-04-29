from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Float,
    Text,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://yolo_user:your_secure_password@localhost/yolo_api"
)

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Database Models
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    api_keys = relationship("APIKey", back_populates="user")
    usage_logs = relationship("UsageLog", back_populates="user")
    rate_limit = relationship("RateLimit", back_populates="user", uselist=False)


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    key = Column(String, unique=True, index=True)
    name = Column(String)  # Description for the key
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="api_keys")
    usage_logs = relationship("UsageLog", back_populates="api_key")


class Model(Base):
    __tablename__ = "models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    file_path = Column(String)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    usage_logs = relationship("UsageLog", back_populates="model")


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    api_key_id = Column(Integer, ForeignKey("api_keys.id"))
    model_id = Column(Integer, ForeignKey("models.id"))
    timestamp = Column(DateTime, default=func.now())
    endpoint = Column(String)
    request_size = Column(Integer)  # Size of the request in bytes
    processing_time = Column(Float)  # Time taken to process in seconds
    status_code = Column(Integer)
    request_ip = Column(String)
    user_agent = Column(String)

    # Relationships
    user = relationship("User", back_populates="usage_logs")
    api_key = relationship("APIKey", back_populates="usage_logs")
    model = relationship("Model", back_populates="usage_logs")


class RateLimit(Base):
    __tablename__ = "rate_limits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    daily_limit = Column(Integer, default=100)
    monthly_limit = Column(Integer, default=3000)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="rate_limit")


# Create all tables in the database
def create_tables():
    Base.metadata.create_all(bind=engine)


# Initialize the database with default data
def init_db():
    db = SessionLocal()

    # Create default admin user if it doesn't exist
    admin_exists = db.query(User).filter(User.username == "admin").first()
    if not admin_exists:
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        admin_user = User(
            username="admin",
            email="admin@example.com",
            password_hash=pwd_context.hash(
                "admin_password"
            ),  # Change this in production!
            is_admin=True,
        )
        db.add(admin_user)

        # Add default YOLOv8 model
        yolo_model = Model(
            name="yolov8n",
            file_path="yolov8n.pt",
            description="YOLOv8 Nano - the smallest and fastest model variant, designed for resource-constrained environments.",
        )
        db.add(yolo_model)

        db.commit()

    db.close()


if __name__ == "__main__":
    create_tables()
    init_db()
    print("Database initialized successfully!")
