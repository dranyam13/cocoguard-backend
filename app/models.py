from sqlalchemy import (
    Column,
    Integer,
    String,
    Enum,
    Text,
    Date,
    ForeignKey,
    Boolean,
    DECIMAL,
    TIMESTAMP,
    func,
    DateTime,
)
from sqlalchemy.orm import relationship
import enum
from datetime import datetime, timezone

from .database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class UserStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.user, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.active, nullable=False)

    full_name = Column(String(100))
    date_of_birth = Column(Date)
    gender = Column(String(20))
    phone = Column(String(30))
    address_line = Column(String(255))
    region = Column(String(100))
    province = Column(String(100))
    city = Column(String(100))
    barangay = Column(String(100))
    
    # FCM token for push notifications
    fcm_token = Column(String(512), nullable=True)
    
    # Two-Factor Authentication
    two_factor_secret = Column(String(32), nullable=True)  # TOTP secret key
    two_factor_enabled = Column(Boolean, default=False)
    
    # Google OAuth
    google_id = Column(String(255), nullable=True, unique=True)  # Google sub ID
    auth_provider = Column(String(20), default="email")  # 'email' or 'google'

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    farms = relationship("Farm", back_populates="owner")
    scans = relationship("Scan", back_populates="user")
    feedbacks = relationship("Feedback", back_populates="user", foreign_keys="[Feedback.user_id]")


class Farm(Base):
    __tablename__ = "farms"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(150), nullable=False)
    address_line = Column(String(255))
    region = Column(String(100))
    province = Column(String(100))
    city = Column(String(100))
    barangay = Column(String(100))

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    owner = relationship("User", back_populates="farms")
    scans = relationship("Scan", back_populates="farm")


class PestRiskLevel(str, enum.Enum):
    low = "Low"
    medium = "Medium"
    high = "High"
    critical = "Critical"


class PestType(Base):
    __tablename__ = "pest_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    scientific_name = Column(String(150))
    risk_level = Column(Enum(PestRiskLevel), nullable=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    scans = relationship("Scan", back_populates="pest_type")


class ScanStatus(str, enum.Enum):
    pending = "Pending"
    verified = "Verified"
    rejected = "Rejected"


class ScanSource(str, enum.Enum):
    image = "image"
    survey = "survey"


class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    farm_id = Column(Integer, ForeignKey("farms.id"))
    tree_code = Column(String(50))
    pest_type_id = Column(Integer, ForeignKey("pest_types.id"))
    image_url = Column(String(255))
    confidence = Column(DECIMAL(5, 2))
    status = Column(Enum(ScanStatus), default=ScanStatus.pending)
    source = Column(Enum(ScanSource), default=ScanSource.image)  # image or survey
    notes = Column(Text)
    location_text = Column(String(255))
    latitude = Column(DECIMAL(10, 8))  # GPS latitude coordinate
    longitude = Column(DECIMAL(11, 8))  # GPS longitude coordinate
    created_at = Column(TIMESTAMP, server_default=func.now())
    verified_at = Column(TIMESTAMP)

    user = relationship("User", back_populates="scans")
    farm = relationship("Farm", back_populates="scans")
    pest_type = relationship("PestType", back_populates="scans")


class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    code = Column(String(6), nullable=False)
    type = Column(String(20), nullable=False)  # 'email' or 'sms'
    recipient = Column(String(255), nullable=False)  # email address or phone number
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
    
    user = relationship("User")


class KnowledgeArticle(Base):
    __tablename__ = "knowledge_articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)  # pest-management, disease-control, best-practices, etc.
    tags = Column(Text)  # Store as JSON string or comma-separated
    image_url = Column(String(255))
    author_id = Column(Integer, ForeignKey("users.id"))
    views = Column(Integer, default=0)
    is_published = Column(Boolean, default=True)
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    author = relationship("User")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Notification Settings
    email_notifications = Column(Boolean, default=True)
    sms_notifications = Column(Boolean, default=False)
    push_notifications = Column(Boolean, default=True)
    
    # Security Settings
    two_factor_enabled = Column(Boolean, default=False)
    
    # Data Settings
    auto_backup = Column(Boolean, default=True)
    
    # Display Settings
    language = Column(String(10), default="en")
    theme = Column(String(20), default="light")
    
    # Privacy Settings
    profile_visible = Column(Boolean, default=True)
    data_sharing = Column(Boolean, default=False)
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    user = relationship("User")


class FeedbackStatus(str, enum.Enum):
    received = "Received"
    in_review = "In Review"
    real_pest = "Real Pest"
    new_pest = "New Pest"
    not_pest = "Not a Pest"
    resolved = "Resolved"


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    message = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    type = Column(String(50), nullable=True)  # Feedback type (e.g., Out-of-Scope Report)
    status = Column(String(30), nullable=False, default="Received")
    admin_response = Column(Text, nullable=True)  # Admin's response message
    admin_response_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Admin who responded
    responded_at = Column(TIMESTAMP, nullable=True)  # When admin responded
    created_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="feedbacks", foreign_keys=[user_id])
    responder = relationship("User", foreign_keys=[admin_response_by])


class PasswordResetToken(Base):
    """Store password reset tokens with expiration"""
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(6), nullable=False)  # 6-digit code
    email = Column(String(255), nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
    
    user = relationship("User")


class NotificationType(str, enum.Enum):
    pest_alert = "pest_alert"
    system = "system"
    info = "info"
    out_of_scope_report = "out_of_scope_report"


class Notification(Base):
    """Notifications for users - especially for dangerous pest alerts"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # NULL means for all users
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(Enum(NotificationType), default=NotificationType.pest_alert)
    pest_type = Column(String(100), nullable=True)  # e.g., "Asiatic Palm Weevil"
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=True)  # Reference to the scan that triggered it
    location_text = Column(String(255), nullable=True)  # Location where pest was detected
    is_read = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    user = relationship("User")
    scan = relationship("Scan")


class RegistrationToken(Base):
    """Store registration verification tokens for email verification during signup"""
    __tablename__ = "registration_tokens"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False)
    token = Column(String(6), nullable=False)  # 6-digit code
    is_used = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
