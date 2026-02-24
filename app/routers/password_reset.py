"""
Password Reset API Endpoints
Handles sending reset codes, verifying codes, and resetting passwords
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import random
import string
import logging

from .. import models, schemas
from ..deps import get_db
from ..auth_utils import get_password_hash
from ..services.email_service import send_password_reset_email

from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/password-reset", tags=["password-reset"])


def generate_reset_code() -> str:
    """Generate a 6-digit reset code"""
    return ''.join(random.choices(string.digits, k=6))


@router.post("/request", response_model=schemas.PasswordResetResponse)
@limiter.limit("3/minute")
async def request_password_reset(
    request: Request,
    reset_data: schemas.PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Request a password reset code.
    Sends a 6-digit verification code to the user's email.
    
    source parameter:
    - 'web' = admin website → only allows admin accounts
    - 'app' = mobile app → only allows user (non-admin) accounts
    - None = legacy behavior (allow any)
    """
    # Find user by email
    user = db.query(models.User).filter(models.User.email == reset_data.email).first()
    
    if not user:
        # Clearly tell user the account is not registered
        logger.warning(f"Password reset requested for non-existent email: {reset_data.email}")
        return schemas.PasswordResetResponse(
            success=False,
            message="This email is not registered. Please create an account first."
        )
    
    # Role-based access control for password reset
    source = getattr(reset_data, 'source', None)
    if source == 'web' and user.role != models.UserRole.admin:
        return schemas.PasswordResetResponse(
            success=False,
            message="This account is not an admin account. Admin password reset is only available for admin accounts registered on the website."
        )
    
    if source == 'app' and user.role != models.UserRole.user:
        return schemas.PasswordResetResponse(
            success=False,
            message="This account is an admin account. Please use the admin website to reset your password."
        )
    
    # Check if user is active
    if user.status == models.UserStatus.inactive:
        return schemas.PasswordResetResponse(
            success=False,
            message="This account has been deactivated. Please contact support."
        )
    
    # Invalidate any existing unused tokens for this user
    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == user.id,
        models.PasswordResetToken.is_used == False
    ).update({"is_used": True})
    db.commit()
    
    # Generate new reset code
    code = generate_reset_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    # Create password reset token
    reset_token = models.PasswordResetToken(
        user_id=user.id,
        token=code,
        email=reset_data.email,
        expires_at=expires_at
    )
    db.add(reset_token)
    db.commit()
    
    # Send email in background
    background_tasks.add_task(
        send_password_reset_email,
        to_email=reset_data.email,
        code=code,
        username=user.username or user.full_name or ""
    )
    
    logger.info(f"Password reset code sent to {reset_data.email}")
    
    return schemas.PasswordResetResponse(
        success=True,
        message="A 6-digit reset code has been sent to your email."
    )


@router.post("/verify", response_model=schemas.PasswordResetResponse)
async def verify_reset_code(
    request: schemas.PasswordResetVerify,
    db: Session = Depends(get_db)
):
    """
    Verify the password reset code without changing the password.
    Used to check if code is valid before showing password input form.
    """
    # Find the reset token
    token = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.email == request.email,
        models.PasswordResetToken.token == request.code,
        models.PasswordResetToken.is_used == False
    ).first()
    
    if not token:
        return schemas.PasswordResetResponse(
            success=False,
            message="Invalid or expired reset code. Please request a new one."
        )
    
    # Check if token is expired
    now = datetime.now(timezone.utc)
    token_expires = token.expires_at
    if token_expires.tzinfo is None:
        token_expires = token_expires.replace(tzinfo=timezone.utc)
    
    if now > token_expires:
        return schemas.PasswordResetResponse(
            success=False,
            message="Reset code has expired. Please request a new one."
        )
    
    return schemas.PasswordResetResponse(
        success=True,
        message="Code verified successfully. You can now set a new password."
    )


@router.post("/confirm", response_model=schemas.PasswordResetResponse)
async def confirm_password_reset(
    request: schemas.PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    Complete the password reset process.
    Verifies the code and sets the new password.
    """
    # Validate new password
    if len(request.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long"
        )
    
    # Find the reset token
    token = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.email == request.email,
        models.PasswordResetToken.token == request.code,
        models.PasswordResetToken.is_used == False
    ).first()
    
    if not token:
        return schemas.PasswordResetResponse(
            success=False,
            message="Invalid or expired reset code. Please request a new one."
        )
    
    # Check if token is expired
    now = datetime.now(timezone.utc)
    token_expires = token.expires_at
    if token_expires.tzinfo is None:
        token_expires = token_expires.replace(tzinfo=timezone.utc)
    
    if now > token_expires:
        return schemas.PasswordResetResponse(
            success=False,
            message="Reset code has expired. Please request a new one."
        )
    
    # Find the user
    user = db.query(models.User).filter(models.User.id == token.user_id).first()
    if not user:
        return schemas.PasswordResetResponse(
            success=False,
            message="User account not found."
        )
    
    # Update password
    user.password_hash = get_password_hash(request.new_password)
    
    # Mark token as used
    token.is_used = True
    
    # Invalidate all other tokens for this user
    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == user.id,
        models.PasswordResetToken.id != token.id
    ).update({"is_used": True})
    
    db.commit()
    
    logger.info(f"Password reset successful for user: {user.email}")
    
    return schemas.PasswordResetResponse(
        success=True,
        message="Password has been reset successfully. You can now login with your new password."
    )


@router.post("/resend", response_model=schemas.PasswordResetResponse)
async def resend_reset_code(
    request: schemas.PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Resend the password reset code.
    Generates a new code and sends it to the email.
    """
    # This is essentially the same as requesting a new code
    return await request_password_reset(request, background_tasks, db)
