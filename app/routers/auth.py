from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import random
import string
import logging
import httpx

from .. import models, schemas
from ..auth_utils import get_password_hash, verify_password, create_access_token
from ..deps import get_db, get_current_user
from ..services.email_service import send_password_reset_email, send_verification_email

GOOGLE_TOKEN_INFO_URL = "https://oauth2.googleapis.com/tokeninfo"

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# Rate limiter (uses the limiter from main app state)
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

# Brute-force protection: track failed login attempts per IP
from collections import defaultdict
import time

_failed_logins: dict[str, list[float]] = defaultdict(list)
_LOCKOUT_THRESHOLD = 5  # max failed attempts
_LOCKOUT_WINDOW = 900  # 15 minutes in seconds


def _check_login_lockout(ip: str):
    """Check if an IP is locked out due to too many failed login attempts"""
    now = time.time()
    # Clean old entries
    _failed_logins[ip] = [t for t in _failed_logins[ip] if now - t < _LOCKOUT_WINDOW]
    if len(_failed_logins[ip]) >= _LOCKOUT_THRESHOLD:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again in 15 minutes."
        )


def _record_failed_login(ip: str):
    _failed_logins[ip].append(time.time())


def _clear_failed_logins(ip: str):
    _failed_logins.pop(ip, None)


def generate_verification_code() -> str:
    """Generate a 6-digit verification code"""
    return ''.join(random.choices(string.digits, k=6))


@router.post("/register", response_model=schemas.TokenWithUser)
@limiter.limit("10/minute")
def register(request: Request, data: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check email uniqueness
    if db.query(models.User).filter(models.User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check username uniqueness
    if db.query(models.User).filter(models.User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    # Hash password
    hashed_password = get_password_hash(data.password)

    # Create user object mapping EXACT SQL COLUMN NAMES
    new_user = models.User(
        username=data.username,
        email=data.email,
        password_hash=hashed_password,  # VERY IMPORTANT
        full_name=data.full_name,
        phone=data.phone,
        gender=data.gender,
        date_of_birth=data.date_of_birth,
        address_line=data.address_line,
        region=data.region,
        province=data.province,
        city=data.city,
        barangay=data.barangay,
        role=models.UserRole.user
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create JWT token (use user ID as subject for consistency with login)
    token = create_access_token({"sub": str(new_user.id)})

    return schemas.TokenWithUser(
        access_token=token,
        token_type="bearer",
        user=new_user
    )


# In-memory storage for registration verification codes (production should use Redis/DB)
_registration_codes: dict[str, dict] = {}


@router.post("/register/send-code")
@limiter.limit("5/minute")
async def send_registration_code(
    request: Request,
    data: schemas.RegistrationEmailRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Send verification code to email for registration"""
    # Check if email is already registered
    existing = db.query(models.User).filter(models.User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Generate code
    code = generate_verification_code()
    
    # Store code with expiration (10 minutes)
    _registration_codes[data.email] = {
        "code": code,
        "expires": datetime.now(timezone.utc) + timedelta(minutes=10),
        "verified": False
    }
    
    # Send email
    try:
        success = await send_verification_email(data.email, code, template_type='verification')
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send verification email")
    except Exception as e:
        logger.error(f"Failed to send registration verification email: {e}")
        raise HTTPException(status_code=500, detail="Failed to send verification email")
    
    return {"success": True, "message": "Verification code sent to your email"}


@router.post("/register/verify-code")
@limiter.limit("10/minute")
def verify_registration_code(
    request: Request,
    data: schemas.RegistrationVerifyRequest
):
    """Verify registration code"""
    stored = _registration_codes.get(data.email)
    
    if not stored:
        raise HTTPException(status_code=400, detail="No verification code found. Please request a new one.")
    
    if datetime.now(timezone.utc) > stored["expires"]:
        del _registration_codes[data.email]
        raise HTTPException(status_code=400, detail="Verification code has expired. Please request a new one.")
    
    if stored["code"] != data.code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    # Mark as verified
    _registration_codes[data.email]["verified"] = True
    
    return {"success": True, "message": "Email verified successfully"}


@router.post("/register/resend-code")
@limiter.limit("3/minute")
async def resend_registration_code(
    request: Request,
    data: schemas.RegistrationEmailRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Resend registration verification code"""
    # Check if email is already registered
    existing = db.query(models.User).filter(models.User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Generate new code
    code = generate_verification_code()
    
    # Store code with expiration (10 minutes)
    _registration_codes[data.email] = {
        "code": code,
        "expires": datetime.now(timezone.utc) + timedelta(minutes=10),
        "verified": False
    }
    
    # Send email
    try:
        success = await send_verification_email(data.email, code, template_type='verification')
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send verification email")
    except Exception as e:
        logger.error(f"Failed to resend registration verification email: {e}")
        raise HTTPException(status_code=500, detail="Failed to send verification email")
    
    return {"success": True, "message": "Verification code resent to your email"}


@router.post("/register/complete", response_model=schemas.TokenWithUser)
@limiter.limit("10/minute")
def complete_registration(
    request: Request,
    data: schemas.UserCreateWithCode,
    db: Session = Depends(get_db)
):
    """Complete registration with verified email"""
    # Check if verification was done
    stored = _registration_codes.get(data.email)
    
    if not stored:
        raise HTTPException(status_code=400, detail="Please verify your email first")
    
    if not stored.get("verified"):
        raise HTTPException(status_code=400, detail="Please verify your email first")
    
    if stored["code"] != data.code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    # Check email uniqueness again
    if db.query(models.User).filter(models.User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check username uniqueness
    if db.query(models.User).filter(models.User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Hash password
    hashed_password = get_password_hash(data.password)
    
    # Create user
    new_user = models.User(
        username=data.username,
        email=data.email,
        password_hash=hashed_password,
        full_name=data.full_name,
        phone=data.phone,
        gender=data.gender,
        date_of_birth=data.date_of_birth,
        address_line=data.address_line,
        region=data.region,
        province=data.province,
        city=data.city,
        barangay=data.barangay,
        role=models.UserRole.user
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Clean up verification code
    del _registration_codes[data.email]
    
    # Create JWT token
    token = create_access_token({"sub": str(new_user.id)})
    
    return schemas.TokenWithUser(
        access_token=token,
        token_type="bearer",
        user=new_user
    )


@router.post("/login")
@limiter.limit("5/minute")
def login(request: Request, login_in: schemas.LoginRequest, db: Session = Depends(get_db)):
    client_ip = get_remote_address(request)
    _check_login_lockout(client_ip)
    
    q = db.query(models.User).filter(
        (models.User.email == login_in.email_or_username)
        | (models.User.username == login_in.email_or_username)
    )
    user = q.first()
    if not user or not verify_password(login_in.password, user.password_hash):
        _record_failed_login(client_ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if user.status == models.UserStatus.inactive:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated. Please contact admin.")

    _clear_failed_logins(client_ip)
    
    # If 2FA is enabled, return challenge instead of token
    if getattr(user, 'two_factor_enabled', False) and user.two_factor_enabled:
        import secrets
        # Generate opaque challenge token
        challenge_token = secrets.token_urlsafe(32)
        # Store mapping in-memory (for demo, use a dict; for production, use Redis or DB)
        if not hasattr(router, '_2fa_challenges'):
            router._2fa_challenges = {}
        router._2fa_challenges[challenge_token] = user.id
        return {
            "requires_2fa": True,
            "challenge_token": challenge_token,
            "message": "Two-factor authentication required. Please verify with your 2FA code."
        }
    
    token = create_access_token({"sub": str(user.id)})
    return schemas.TokenWithUser(access_token=token, user=user)


@router.get("/me")
def get_current_user_info(
    current_user: models.User = Depends(get_current_user),
):
    """Get current authenticated user information"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "phone": current_user.phone,
        "gender": current_user.gender,
        "date_of_birth": current_user.date_of_birth,
        "address_line": current_user.address_line,
        "region": current_user.region,
        "province": current_user.province,
        "city": current_user.city,
        "barangay": current_user.barangay,
        "role": current_user.role,
        "status": current_user.status,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
    }


@router.put("/me")
def update_current_user(
    data: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current authenticated user information"""
    # Update only provided fields
    if data.full_name is not None:
        current_user.full_name = data.full_name
    if data.phone is not None:
        current_user.phone = data.phone
    if data.gender is not None:
        current_user.gender = data.gender
    if data.date_of_birth is not None:
        current_user.date_of_birth = data.date_of_birth
    if data.address_line is not None:
        current_user.address_line = data.address_line
    if data.region is not None:
        current_user.region = data.region
    if data.province is not None:
        current_user.province = data.province
    if data.city is not None:
        current_user.city = data.city
    if data.barangay is not None:
        current_user.barangay = data.barangay
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "success": True,
        "message": "Profile updated successfully",
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "phone": current_user.phone,
            "gender": current_user.gender,
            "date_of_birth": current_user.date_of_birth,
            "address_line": current_user.address_line,
            "region": current_user.region,
            "province": current_user.province,
            "city": current_user.city,
            "barangay": current_user.barangay,
            "role": current_user.role,
            "status": current_user.status,
        }
    }


@router.post("/change-password")
def change_password(
    data: schemas.ChangePasswordRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify current password
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password length
    if len(data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters"
        )
    
    # Hash and update new password
    current_user.password_hash = get_password_hash(data.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}


@router.post("/change-password/request-code")
async def request_change_password_code(
    data: schemas.ChangePasswordRequest,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Request verification code for changing password.
    Verifies current password first, then sends code to user's email.
    """
    # Verify current password
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password length
    if len(data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters"
        )
    
    # Invalidate any existing unused tokens for this user
    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == current_user.id,
        models.PasswordResetToken.is_used == False
    ).update({"is_used": True})
    db.commit()
    
    # Generate new verification code
    code = generate_verification_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    # Create verification token
    reset_token = models.PasswordResetToken(
        user_id=current_user.id,
        token=code,
        email=current_user.email,
        expires_at=expires_at
    )
    db.add(reset_token)
    db.commit()
    
    # Send email in background
    background_tasks.add_task(
        send_password_reset_email,
        to_email=current_user.email,
        code=code,
        username=current_user.username or current_user.full_name or ""
    )
    
    logger.info(f"Change password verification code sent to {current_user.email}")
    
    return {
        "success": True,
        "message": "A 6-digit verification code has been sent to your email.",
        "email": current_user.email
    }


@router.post("/change-password/verify")
async def verify_and_change_password(
    data: schemas.ChangePasswordWithCode,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify code and change password.
    """
    # Verify current password again for security
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password length
    if len(data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters"
        )
    
    # Find the verification token
    token = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == current_user.id,
        models.PasswordResetToken.token == data.code,
        models.PasswordResetToken.is_used == False
    ).first()
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )
    
    # Check if token is expired
    now = datetime.now(timezone.utc)
    token_expires = token.expires_at
    if token_expires.tzinfo is None:
        token_expires = token_expires.replace(tzinfo=timezone.utc)
    
    if now > token_expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired. Please request a new one."
        )
    
    # Update password
    current_user.password_hash = get_password_hash(data.new_password)
    
    # Mark token as used
    token.is_used = True
    
    db.commit()
    
    logger.info(f"Password changed successfully for user: {current_user.email}")
    
    return {
        "success": True,
        "message": "Password changed successfully"
    }


@router.post("/logout")
def logout(current_user: models.User = Depends(get_current_user)):
    """
    Logout current user.
    Since we use stateless JWTs, this is mainly a signal endpoint.
    The client is expected to clear its stored token.
    """
    logger.info(f"User logged out: {current_user.email}")
    return {"success": True, "message": "Logged out successfully"}


@router.post("/logout-all")
def logout_all_devices(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sign out from all devices.
    Invalidates all password reset tokens and returns confirmation.
    Since we use stateless JWTs, full token revocation is not supported,
    but this clears any active verification tokens.
    """
    # Invalidate all password reset tokens for this user
    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == current_user.id,
        models.PasswordResetToken.is_used == False
    ).update({"is_used": True})
    db.commit()

    logger.info(f"User signed out from all devices: {current_user.email}")
    return {"success": True, "message": "Signed out from all devices. All active sessions will expire shortly."}


@router.delete("/delete-account")
def delete_account(
    data: schemas.DeleteAccountRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permanently delete the current user's account and all associated data.
    Requires password verification.
    """
    # Verify password
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is incorrect"
        )

    user_email = current_user.email
    user_id = current_user.id

    try:
        # Delete user settings
        db.query(models.UserSettings).filter(
            models.UserSettings.user_id == user_id
        ).delete()

        # Delete password reset tokens
        db.query(models.PasswordResetToken).filter(
            models.PasswordResetToken.user_id == user_id
        ).delete()

        # Delete feedbacks
        db.query(models.Feedback).filter(
            models.Feedback.user_id == user_id
        ).delete()

        # Delete scans
        from .scans import _delete_scan_image
        user_scans = db.query(models.Scan).filter(
            models.Scan.user_id == user_id
        ).all()
        for scan in user_scans:
            _delete_scan_image(scan.image_url)
            db.delete(scan)

        # Delete farms
        db.query(models.Farm).filter(
            models.Farm.user_id == user_id
        ).delete()

        # Delete the user
        db.delete(current_user)
        db.commit()

        logger.info(f"Account deleted successfully for user: {user_email} (ID: {user_id})")

        return {
            "success": True,
            "message": "Account and all associated data have been permanently deleted."
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete account for user {user_email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account. Please try again."
        )


@router.post("/google-signup", response_model=None)
async def google_signup(
    request: schemas.GoogleSignInRequest,
    db: Session = Depends(get_db)
):
    """
    Sign up or sign in with Google for mobile app users.
    - If the Google account is already linked, log them in.
    - If the email exists but no Google link, link it and log in.
    - If new email, create a regular user account.
    """
    # Verify Google token (supports both ID tokens and access tokens)
    try:
        async with httpx.AsyncClient() as client:
            if request.token_type == 'access_token':
                # Web: verify access token via Google userinfo endpoint
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {request.google_token}"}
                )
            else:
                # Mobile: verify ID token via Google tokeninfo endpoint
                response = await client.get(
                    f"{GOOGLE_TOKEN_INFO_URL}?id_token={request.google_token}"
                )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Google token. Please try again."
                )

            google_data = response.json()

            google_email = google_data.get("email")
            google_id = google_data.get("sub")
            google_name = google_data.get("name", "")
            email_verified = google_data.get("email_verified", "false")

            # Handle both string (tokeninfo) and boolean (userinfo) formats
            if isinstance(email_verified, bool):
                email_verified = "true" if email_verified else "false"

            if not google_email or email_verified != "true":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Google email not verified."
                )
    except httpx.RequestError as e:
        logger.error(f"Google token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not verify Google token. Please try again."
        )

    # Check if user exists by google_id
    user = db.query(models.User).filter(
        models.User.google_id == google_id
    ).first()

    if user:
        if user.status == models.UserStatus.inactive:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Please contact support."
            )

        token = create_access_token({"sub": str(user.id)})
        return {
            "success": True,
            "is_new_user": False,
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "gender": user.gender,
                "phone": user.phone,
                "date_of_birth": str(user.date_of_birth) if user.date_of_birth else None,
                "address_line": user.address_line,
            }
        }

    # Check if user exists by email
    user = db.query(models.User).filter(
        models.User.email == google_email
    ).first()

    if user:
        # Link Google account to existing user
        user.google_id = google_id
        if not user.full_name and google_name:
            user.full_name = google_name
        db.commit()

        if user.status == models.UserStatus.inactive:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Please contact support."
            )

        token = create_access_token({"sub": str(user.id)})
        return {
            "success": True,
            "is_new_user": False,
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "gender": user.gender,
                "phone": user.phone,
                "date_of_birth": str(user.date_of_birth) if user.date_of_birth else None,
                "address_line": user.address_line,
            }
        }

    # New user - create regular user account with Google
    base_username = google_email.split("@")[0]
    username = base_username
    counter = 1
    while db.query(models.User).filter(models.User.username == username).first():
        username = f"{base_username}{counter}"
        counter += 1

    import secrets
    temp_password = secrets.token_urlsafe(32)

    new_user = models.User(
        username=username,
        email=google_email,
        password_hash=get_password_hash(temp_password),
        full_name=google_name,
        role=models.UserRole.user,  # Regular user for mobile
        google_id=google_id,
        auth_provider="google"
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({"sub": str(new_user.id)})

    logger.info(f"New user account created via Google: {google_email}")

    return {
        "success": True,
        "is_new_user": True,
        "needs_password_setup": True,
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "full_name": new_user.full_name,
            "role": new_user.role.value,
            "gender": new_user.gender,
            "phone": new_user.phone,
            "date_of_birth": None,
            "address_line": new_user.address_line,
        }
    }


@router.post("/google-set-password", response_model=None)
async def google_set_password(
    request: schemas.GoogleSetPasswordRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Set a password for the currently authenticated user who signed up via Google.
    This allows them to also log in with email/password on mobile.
    """
    if len(request.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long."
        )

    # Use the authenticated user instead of trusting email from request body
    user = current_user

    if user.auth_provider != "google":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account was not created via Google sign-up."
        )

    # Set the new password and update auth_provider to allow both methods
    user.password_hash = get_password_hash(request.password)
    user.auth_provider = "google+email"
    db.commit()

    logger.info(f"Password set for Google user: {user.email}")

    token = create_access_token({"sub": str(user.id)})

    return {
        "success": True,
        "message": "Password set successfully. You can now log in with your email and password.",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "gender": user.gender,
            "phone": user.phone,
            "date_of_birth": str(user.date_of_birth) if user.date_of_birth else None,
            "address_line": user.address_line,
        }
    }
