from pydantic_settings import BaseSettings
from pydantic import ConfigDict, field_validator
import os

class Settings(BaseSettings):
    # API Info
    api_title: str = "CocoGuard API"
    api_version: str = "1.0.0"
    api_description: str = "Coconut Pest Detection and Management System"
    
    # Database
    database_url: str = "sqlite:///./cocoguard.db"
    
    # Security
    secret_key: str = ""  # MUST be set via .env — app will fail-safe if empty
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7 days
    
    # File Upload
    max_upload_size: int = 5242880  # 5MB
    upload_dir: str = "./uploads"
    
    # Email Configuration
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "CocoGuard"
    
    # Google OAuth Configuration
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/admin-register/google-callback"

    # SMS Configuration (Twilio)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # CORS (stored as raw string to avoid JSON parsing errors from env)
    allowed_origins_raw: str = "http://localhost,http://localhost:80,http://127.0.0.1"
    
    model_config = ConfigDict(env_file=".env", case_sensitive=False)

    @field_validator('allowed_origins_raw', mode='before')
    @classmethod
    def validate_origins(cls, v):
        return v or "http://localhost"

    @property
    def allowed_origins(self):
        # Split comma-separated values; default to localhost only
        raw = (self.allowed_origins_raw or "http://localhost").strip()
        return [item.strip() for item in raw.split(",") if item.strip()] or ["http://localhost"]

settings = Settings()

# Fail-safe: refuse to start with empty or default secret key
if not settings.secret_key or settings.secret_key in ("", "change-this-secret-key-to-a-long-random-string"):
    raise RuntimeError(
        "FATAL: SECRET_KEY is not set or is using a default value. "
        "Set a strong random key in .env: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
    )
