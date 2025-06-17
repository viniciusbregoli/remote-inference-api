import os
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
)
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.sql import func
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./api.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "User"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    api_keys = relationship("APIKey", back_populates="user")
    usage_logs = relationship("ApiLog", back_populates="user")


class APIKey(Base):
    __tablename__ = "ApiKey"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("User.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="api_keys")
    usage_logs = relationship("ApiLog", back_populates="api_key")


class ApiLog(Base):
    __tablename__ = "ApiLog"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("User.id"), nullable=False)
    api_key_id = Column(Integer, ForeignKey("ApiKey.id"), nullable=False)
    endpoint = Column(String, nullable=False)
    model_name = Column(String)
    request_size = Column(Integer)  # in bytes
    status_code = Column(Integer)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="usage_logs")
    api_key = relationship("APIKey", back_populates="usage_logs")
    detection = relationship("Detection", back_populates="api_log", uselist=False)


class Detection(Base):
    __tablename__ = "Detection"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("ApiLog.id"), nullable=False, unique=True)
    model_name = Column(String, nullable=False)
    image_width = Column(Integer, nullable=False)
    image_height = Column(Integer, nullable=False)
    processing_time = Column(Float, nullable=False)  # in seconds

    api_log = relationship("ApiLog", back_populates="detection")
    bounding_boxes = relationship("BoundingBox", back_populates="detection")


class BoundingBox(Base):
    __tablename__ = "BoundingBox"
    id = Column(Integer, primary_key=True, index=True)
    detection_id = Column(Integer, ForeignKey("Detection.id"), nullable=False)
    class_name = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    x1 = Column(Float, nullable=False)
    y1 = Column(Float, nullable=False)
    x2 = Column(Float, nullable=False)
    y2 = Column(Float, nullable=False)

    detection = relationship("Detection", back_populates="bounding_boxes")


def create_tables():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
