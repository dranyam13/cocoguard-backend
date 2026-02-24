from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import secrets
import string
import logging

from app.deps import get_db, get_current_user
from app.models import User, VerificationCode
from app.schemas import SendVerificationRequest, VerifyCodeRequest, VerificationResponse
from app.services.email_service import send_verification_email
from app.services.sms_service import send_verification_sms
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/verification", tags=["verification"])


def generate_code() -> str:
    """Generate a 6-digit verification code"""
    return ''.join(secrets.choice(string.digits) for _ in range(6))


@router.post("/send", response_model=VerificationResponse)
async def send_verification_code(
    request: SendVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a verification code via email or SMS"""
    try:
        logger.info(f"User {current_user.id} requesting {request.type} verification to {request.recipient}")
        
        # Generate verification code
        code = generate_code()
        
        # Set expiration time (10 minutes from now)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        
        # Save to database
        verification = VerificationCode(
            user_id=current_user.id,
            code=code,
            type=request.type,
            recipient=request.recipient,
            expires_at=expires_at
        )
        db.add(verification)
        db.commit()
        logger.info(f"Verification code saved to database for user {current_user.id}")
        
        # Send code based on type
        if request.type == "email":
            if not settings.smtp_username or not settings.smtp_password:
                logger.warning("SMTP not configured")
                return VerificationResponse(
                    success=False,
                    message="Email service not configured. Please contact administrator."
                )
            success = await send_verification_email(request.recipient, code)
            message = "Verification code sent to your email" if success else "Failed to send email. Please try again later."
        elif request.type == "sms":
            if not settings.twilio_account_sid or not settings.twilio_auth_token:
                logger.warning("Twilio not configured")
                return VerificationResponse(
                    success=False,
                    message="SMS service not configured. Please contact administrator or use email verification."
                )
            success = await send_verification_sms(request.recipient, code)
            message = "Verification code sent via SMS" if success else "Failed to send SMS. Please try again later."
        else:
            raise HTTPException(status_code=400, detail="Invalid verification type")
        
        logger.info(f"Verification code send result: {success}")
        return VerificationResponse(success=success, message=message)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending verification code: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send verification code: {str(e)}"
        )


@router.post("/verify", response_model=VerificationResponse)
async def verify_code(
    request: VerifyCodeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify a code sent via email or SMS"""
    try:
        # Find the most recent unused code for this user and recipient
        verification = db.query(VerificationCode).filter(
            VerificationCode.user_id == current_user.id,
            VerificationCode.type == request.type,
            VerificationCode.recipient == request.recipient,
            VerificationCode.code == request.code,
            VerificationCode.is_used == False
        ).order_by(VerificationCode.created_at.desc()).first()
        
        if not verification:
            return VerificationResponse(
                success=False,
                message="Invalid verification code"
            )
        
        # Check if code has expired
        if datetime.now(timezone.utc) > verification.expires_at:
            return VerificationResponse(
                success=False,
                message="Verification code has expired"
            )
        
        # Mark code as used
        verification.is_used = True
        db.commit()
        
        return VerificationResponse(
            success=True,
            message="Verification successful"
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {str(e)}"
        )
