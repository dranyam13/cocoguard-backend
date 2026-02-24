from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr

from .models import UserRole, PestRiskLevel, ScanStatus

__all__ = [
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserOut",
    "Token",
    "TokenWithUser",
    "LoginRequest",
    "ChangePasswordRequest",
    "DeleteAccountRequest",
    "SendVerificationRequest",
    "VerifyCodeRequest",
    "VerificationResponse",
    "FarmBase",
    "FarmUpdate",
    "PestTypeBase",
    "PestTypeCreate",
    "PestTypeOut",
    "ScanCreate",
    "SurveyResultCreate",
    "ScanItem",
    "MyScansResponse",
    "DashboardResponse",
    "UserSettingsBase",
    "UserSettingsUpdate",
    "UserSettingsOut",
    "FeedbackCreate",
    "FeedbackOut",
    "FeedbackRespond",
]

# ---------- AUTH & USER ----------

class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(BaseModel):
    full_name: str
    username: str
    email: EmailStr
    password: str

    # optional profile fields
    phone: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None

    # required address field
    address_line: str

    # optional registration extras (farm info)
    region: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    barangay: Optional[str] = None
    address_line: Optional[str] = None


class UserCreateWithCode(BaseModel):
    """Registration with email verification code"""
    email: EmailStr
    code: str
    password: str
    full_name: str
    username: str
    phone: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    region: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    barangay: Optional[str] = None
    address_line: Optional[str] = None


class RegistrationEmailRequest(BaseModel):
    """Request to send registration verification code"""
    email: EmailStr


class RegistrationVerifyRequest(BaseModel):
    """Request to verify registration code"""
    email: EmailStr
    code: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    address_line: Optional[str] = None
    region: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    barangay: Optional[str] = None

    class Config:
        from_attributes = True


class UserOut(UserBase):
    id: int
    role: UserRole

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenWithUser(Token):
    user: UserOut


class LoginRequest(BaseModel):
    email_or_username: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class DeleteAccountRequest(BaseModel):
    """Request to delete user account with password verification"""
    current_password: str


class ChangePasswordWithCode(BaseModel):
    """Change password with verification code"""
    current_password: str
    new_password: str
    code: str


# ---------- VERIFICATION ----------

class SendVerificationRequest(BaseModel):
    type: str  # 'email' or 'sms'
    recipient: str  # email address or phone number


class VerifyCodeRequest(BaseModel):
    type: str  # 'email' or 'sms'
    recipient: str
    code: str


class VerificationResponse(BaseModel):
    success: bool
    message: str


# ---------- PASSWORD RESET ----------

class PasswordResetRequest(BaseModel):
    """Request to send a password reset code"""
    email: EmailStr
    source: Optional[str] = None  # 'web' or 'app' - to validate role-based access


class PasswordResetVerify(BaseModel):
    """Verify the reset code"""
    email: EmailStr
    code: str


class PasswordResetConfirm(BaseModel):
    """Set new password after verification"""
    email: EmailStr
    code: str
    new_password: str


class PasswordResetResponse(BaseModel):
    success: bool
    message: str


# ---------- ADMIN REGISTRATION ----------

class AdminRegisterSendCode(BaseModel):
    """Request to send verification code for admin registration"""
    email: EmailStr


class AdminRegisterVerifyCode(BaseModel):
    """Verify registration code"""
    email: EmailStr
    code: str


class AdminRegisterComplete(BaseModel):
    """Complete admin registration after email verification"""
    email: EmailStr
    code: str
    username: str
    full_name: str
    password: str


class GoogleSignInRequest(BaseModel):
    """Google Sign-In / Sign-Up request"""
    google_token: str  # Google ID token or access token from frontend
    token_type: str = 'id_token'  # 'id_token' (mobile) or 'access_token' (web)
    

class GoogleSetPasswordRequest(BaseModel):
    """Set password after Google sign-in registration"""
    email: EmailStr
    password: str


# ---------- FARM ----------

class FarmBase(BaseModel):
    id: int
    name: str
    plantation_name: Optional[str] = None
    total_trees: int
    region: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    barangay: Optional[str] = None
    address_line: Optional[str] = None

    class Config:
        from_attributes = True


class FarmUpdate(BaseModel):
    name: Optional[str] = None
    plantation_name: Optional[str] = None
    total_trees: Optional[int] = None


# ---------- PEST TYPES ----------

class PestTypeBase(BaseModel):
    name: str
    scientific_name: Optional[str]
    risk_level: PestRiskLevel
    is_active: bool = True


class PestTypeCreate(PestTypeBase):
    pass


class PestTypeOut(PestTypeBase):
    id: int

    class Config:
        from_attributes = True


# ---------- SCANS ----------

class SurveyResultCreate(BaseModel):
    pest_type: str
    answer_counts: dict = {}
    location_text: Optional[str] = "Survey Assessment"


class ScanCreate(BaseModel):
    farm_id: Optional[int] = None
    tree_code: Optional[str] = None
    location_text: Optional[str] = None
    pest_type_id: Optional[int] = None
    pest_type: Optional[str] = None  # Can pass name instead of ID
    confidence: Optional[float] = None
    image_url: Optional[str] = None  # for now; later multipart file upload
    latitude: Optional[float] = None  # GPS latitude coordinate
    longitude: Optional[float] = None  # GPS longitude coordinate
    source: Optional[str] = "image"  # "image" or "survey"


class ScanItem(BaseModel):
    id: int
    tree_code: Optional[str]
    date_time: datetime
    location_text: Optional[str]
    pest_type: Optional[str]
    risk_level: Optional[PestRiskLevel]
    confidence: Optional[float]
    status: ScanStatus
    image_url: Optional[str]
    latitude: Optional[float] = None  # GPS latitude coordinate
    longitude: Optional[float] = None  # GPS longitude coordinate
    source: Optional[str] = "image"  # "image" or "survey"

    class Config:
        from_attributes = True


class MyScansResponse(BaseModel):
    total_scans: int
    total_trees: int
    records: List[ScanItem]


# ---------- DASHBOARD ----------

class DashboardResponse(BaseModel):
    greeting_name: str
    farm: Optional[FarmBase]
    stats: dict
    recent_scans: List[ScanItem]


# ---------- USER SETTINGS ----------

class UserSettingsBase(BaseModel):
    email_notifications: bool = True
    sms_notifications: bool = False
    push_notifications: bool = True
    two_factor_enabled: bool = False
    auto_backup: bool = True
    language: str = "en"
    theme: str = "light"
    profile_visible: bool = True
    data_sharing: bool = False


class UserSettingsUpdate(BaseModel):
    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    two_factor_enabled: Optional[bool] = None
    auto_backup: Optional[bool] = None
    language: Optional[str] = None
    theme: Optional[str] = None
    profile_visible: Optional[bool] = None
    data_sharing: Optional[bool] = None


class UserSettingsOut(UserSettingsBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------- FEEDBACK ----------

class FeedbackCreate(BaseModel):
    message: str
    type: Optional[str] = None
    user_id: Optional[int] = None
    scan_id: Optional[int] = None  # Link to scan record (used for OOS reports)



# For feedback user info
class FeedbackUser(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None

    class Config:
        orm_mode = True


class FeedbackRespond(BaseModel):
    """Schema for admin to respond to feedback"""
    status: str  # Real Pest, New Pest, Not a Pest, In Review, Resolved
    admin_response: Optional[str] = None  # Optional response message


class FeedbackOut(BaseModel):
    id: int
    message: str
    type: Optional[str] = None
    status: Optional[str] = None
    user_id: Optional[int] = None
    user: Optional[FeedbackUser] = None
    admin_response: Optional[str] = None
    admin_response_by: Optional[int] = None
    responder: Optional[FeedbackUser] = None
    responded_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        orm_mode = True


class PasswordResetResponse(BaseModel):
    success: bool
    message: str
