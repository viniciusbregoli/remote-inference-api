from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, UTC
import bcrypt
import uuid

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    is_active = db.Column(db.Boolean, default=True)
    role = db.Column(db.String(20), default="user")

    # Relationships
    api_keys = db.relationship(
        "ApiKey", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    models = db.relationship("Model", backref="user", lazy=True)
    usage_logs = db.relationship("UsageLog", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    def check_password(self, password):
        return bcrypt.checkpw(
            password.encode("utf-8"), self.password_hash.encode("utf-8")
        )

    def generate_api_key(self, name):
        api_key = uuid.uuid4().hex
        new_key = ApiKey(user_id=self.id, api_key=api_key, name=name)
        db.session.add(new_key)
        db.session.commit()
        return api_key


class ApiKey(db.Model):
    __tablename__ = "api_keys"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    api_key = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    last_used_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    __table_args__ = (db.UniqueConstraint("user_id", "name", name="_user_key_name_uc"),)

    def update_last_used(self):
        self.last_used_at = datetime.now(UTC)
        db.session.commit()


class Model(db.Model):
    __tablename__ = "models"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    name = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    model_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        db.UniqueConstraint("user_id", "name", name="_user_model_name_uc"),
    )

    # Relationships
    usage_logs = db.relationship("UsageLog", backref="model", lazy=True)


class UsageLog(db.Model):
    __tablename__ = "usage_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    api_key_id = db.Column(db.Integer, db.ForeignKey("api_keys.id"))
    model_id = db.Column(db.Integer, db.ForeignKey("models.id"))
    endpoint = db.Column(db.String(50), nullable=False)
    status_code = db.Column(db.Integer, nullable=False)
    request_size = db.Column(db.Integer)
    response_size = db.Column(db.Integer)
    processing_time = db.Column(db.Integer)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    # Relationships
    api_key = db.relationship("ApiKey", backref="usage_logs")


class DetectionResult(db.Model):
    __tablename__ = "detection_results"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    model_id = db.Column(db.Integer, db.ForeignKey("models.id"))
    image_hash = db.Column(db.String(64))
    results = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    # Relationships
    user = db.relationship("User", backref="detection_results")
