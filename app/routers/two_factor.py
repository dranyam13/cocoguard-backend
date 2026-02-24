"""
Two-Factor Authentication (2FA) Router
Uses email-based verification codes for 2FA
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import secrets
import string
import logging

from ..database import get_db
from ..models import User, UserSettings, VerificationCode
from ..deps import get_current_user
from ..services.email_service import send_verification_email
from ..auth_utils import verify_password, create_access_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/2fa", tags=["two-factor-auth"])


# Pydantic models
class TwoFactorSetupResponse(BaseModel):
    success: bool
    message: str
    email: str = None


class TwoFactorVerifyRequest(BaseModel):
    code: str


class TwoFactorDisableRequest(BaseModel):
    password: str


class TwoFactorLoginRequest(BaseModel):
    email: str


class TwoFactorLoginVerifyRequest(BaseModel):
    email: str
    code: str


class TwoFactorVerifyResponse(BaseModel):
    success: bool
    message: str
    two_factor_enabled: bool = False


class TwoFactorStatusResponse(BaseModel):
    enabled: bool
    email: str


def generate_code() -> str:
    """Generate a 6-digit verification code"""
    return ''.join(secrets.choice(string.digits) for _ in range(6))


@router.get("/status", response_model=TwoFactorStatusResponse)
async def get_2fa_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current 2FA status for the user"""
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()
    
    enabled = settings.two_factor_enabled if settings else False
    
    # Mask email for privacy
    email = current_user.email
    if email:
        parts = email.split('@')
        if len(parts) == 2:
            name = parts[0]
            domain = parts[1]
            masked_name = name[0] + '*' * (len(name) - 2) + name[-1] if len(name) > 2 else name
            email = f"{masked_name}@{domain}"
    
    return TwoFactorStatusResponse(enabled=enabled, email=email)


@router.post("/setup", response_model=TwoFactorSetupResponse)
async def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initiate 2FA setup by sending a verification code to user's email
    """
    try:
        logger.info(f"User {current_user.id} initiating 2FA setup")
        
        # Generate verification code
        code = generate_code()
        
        # Set expiration time (10 minutes)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        
        # Invalidate any existing 2FA setup codes
        db.query(VerificationCode).filter(
            VerificationCode.user_id == current_user.id,
            VerificationCode.type == "2fa_setup",
            VerificationCode.is_used == False
        ).update({"is_used": True})
        
        # Save verification code
        verification = VerificationCode(
            user_id=current_user.id,
            code=code,
            type="2fa_setup",
            recipient=current_user.email,
            expires_at=expires_at
        )
        db.add(verification)
        db.commit()
        
        # Send email
        email_sent = await send_verification_email(
            current_user.email, 
            code,
            subject="CocoGuard - Enable Two-Factor Authentication",
            template_type="2fa_setup"
        )
        
        if email_sent:
            logger.info(f"2FA setup code sent to {current_user.email}")
            return TwoFactorSetupResponse(
                success=True,
                message="Verification code sent to your email",
                email=current_user.email
            )
        else:
            logger.warning(f"Failed to send 2FA setup code to {current_user.email}")
            return TwoFactorSetupResponse(
                success=False,
                message="Failed to send verification email. Please try again."
            )
            
    except Exception as e:
        logger.error(f"Error in 2FA setup: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate 2FA setup: {str(e)}"
        )


@router.post("/enable", response_model=TwoFactorVerifyResponse)
async def enable_2fa(
    request: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify code and enable 2FA for the user
    """
    try:
        logger.info(f"User {current_user.id} attempting to enable 2FA with code: {request.code[:2]}***")
        
        # Find valid verification code
        verification = db.query(VerificationCode).filter(
            VerificationCode.user_id == current_user.id,
            VerificationCode.type == "2fa_setup",
            VerificationCode.code == request.code,
            VerificationCode.is_used == False,
            VerificationCode.expires_at > datetime.now(timezone.utc)
        ).first()
        
        if not verification:
            logger.warning(f"Invalid or expired 2FA code for user {current_user.id}")
            return TwoFactorVerifyResponse(
                success=False,
                message="Invalid or expired verification code",
                two_factor_enabled=False
            )
        
        # Mark code as used
        verification.is_used = True
        
        # Enable 2FA in user settings
        settings = db.query(UserSettings).filter(
            UserSettings.user_id == current_user.id
        ).first()
        
        if not settings:
            settings = UserSettings(user_id=current_user.id)
            db.add(settings)
        
        settings.two_factor_enabled = True
        
        # Also update user model
        current_user.two_factor_enabled = True
        
        db.commit()
        
        logger.info(f"2FA enabled successfully for user {current_user.id}")
        return TwoFactorVerifyResponse(
            success=True,
            message="Two-Factor Authentication enabled successfully!",
            two_factor_enabled=True
        )
        
    except Exception as e:
        logger.error(f"Error enabling 2FA: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable 2FA: {str(e)}"
        )


@router.post("/disable", response_model=TwoFactorVerifyResponse)
async def disable_2fa(
    request: TwoFactorDisableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disable 2FA for the user. Requires password confirmation.
    """
    try:
        # Verify password before disabling 2FA
        if not current_user.password_hash or not verify_password(request.password, current_user.password_hash):
            return TwoFactorVerifyResponse(
                success=False,
                message="Incorrect password. Please enter your current password to disable 2FA.",
                two_factor_enabled=True
            )
        
        logger.info(f"User {current_user.id} disabling 2FA")
        
        # Update settings
        settings = db.query(UserSettings).filter(
            UserSettings.user_id == current_user.id
        ).first()
        
        if settings:
            settings.two_factor_enabled = False
        
        # Also update user model
        current_user.two_factor_enabled = False
        current_user.two_factor_secret = None
        
        db.commit()
        
        logger.info(f"2FA disabled for user {current_user.id}")
        return TwoFactorVerifyResponse(
            success=True,
            message="Two-Factor Authentication has been disabled",
            two_factor_enabled=False
        )
        
    except Exception as e:
        logger.error(f"Error disabling 2FA: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable 2FA: {str(e)}"
        )


@router.post("/send-login-code", response_model=TwoFactorSetupResponse)
async def send_login_2fa_code(
    request: TwoFactorLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Send 2FA verification code during login (called after password verification)
    """
    try:
        # Find user by email
        user = db.query(User).filter(User.email == request.email).first()
        
        if not user:
            # Don't reveal if user exists
            return TwoFactorSetupResponse(
                success=True,
                message="If the account exists, a code has been sent"
            )
        
        # Check if 2FA is enabled
        settings = db.query(UserSettings).filter(
            UserSettings.user_id == user.id
        ).first()
        
        if not settings or not settings.two_factor_enabled:
            return TwoFactorSetupResponse(
                success=False,
                message="2FA is not enabled for this account"
            )
        
        # Generate and send code
        code = generate_code()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        
        verification = VerificationCode(
            user_id=user.id,
            code=code,
            type="2fa_login",
            recipient=user.email,
            expires_at=expires_at
        )
        db.add(verification)
        db.commit()
        
        await send_verification_email(
            user.email,
            code,
            subject="CocoGuard - Login Verification Code",
            template_type="2fa_login"
        )
        
        return TwoFactorSetupResponse(
            success=True,
            message="Verification code sent to your email",
            email=user.email
        )
        
    except Exception as e:
        logger.error(f"Error sending login 2FA code: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification code"
        )


@router.post("/verify-login")
async def verify_login_2fa(
    request: TwoFactorLoginVerifyRequest,
    db: Session = Depends(get_db)
):
    """
    Verify 2FA code during login. Returns JWT token on success.
    """
    try:
        user = db.query(User).filter(User.email == request.email).first()
        
        if not user:
            return {"success": False, "message": "Invalid credentials"}
        
        verification = db.query(VerificationCode).filter(
            VerificationCode.user_id == user.id,
            VerificationCode.type == "2fa_login",
            VerificationCode.code == request.code,
            VerificationCode.is_used == False,
            VerificationCode.expires_at > datetime.now(timezone.utc)
        ).first()
        
        if not verification:
            return {"success": False, "message": "Invalid or expired code"}
        
        verification.is_used = True
        db.commit()
        
        # Issue JWT token after successful 2FA verification
        token = create_access_token({"sub": str(user.id)})
        return {
            "success": True,
            "message": "2FA verification successful",
            "access_token": token,
            "token_type": "bearer",
            "user_id": user.id
        }
        
    except Exception as e:
        logger.error(f"Error verifying login 2FA: {str(e)}", exc_info=True)
        return {"success": False, "message": "Verification failed"}
