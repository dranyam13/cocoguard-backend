"""
Admin Registration API Endpoints
Handles admin account creation with email verification,
Google Sign-In for admin, and setting password after Google auth.
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import random
import string
import logging
import httpx
import urllib.parse
import secrets as sec_module

from .. import models, schemas
from ..deps import get_db, get_current_user
from ..auth_utils import get_password_hash, create_access_token
from ..services.email_service import send_verification_email
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin-register", tags=["admin-registration"])

GOOGLE_TOKEN_INFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def generate_verification_code() -> str:
    """Generate a 6-digit verification code"""
    return ''.join(random.choices(string.digits, k=6))


@router.post("/send-code", response_model=schemas.PasswordResetResponse)
async def send_registration_code(
    request: schemas.AdminRegisterSendCode,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Send a verification code to the email for admin registration.
    Only existing admins can register new admin accounts.
    If the email is already registered, return an error.
    """
    # Bootstrap mode: allow unauthenticated registration only if no admin exists yet.
    # Once an admin account exists, this public endpoint is blocked.
    has_admin = db.query(models.User).filter(models.User.role == models.UserRole.admin).first() is not None
    if has_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account already exists. Please login as admin to manage accounts."
        )
    # Check if email is already registered
    existing_user = db.query(models.User).filter(
        models.User.email == request.email
    ).first()
    
    if existing_user:
        return schemas.PasswordResetResponse(
            success=False,
            message="This email is already registered. Please login instead."
        )
    
    # Invalidate any existing unused registration tokens for this email
    db.query(models.RegistrationToken).filter(
        models.RegistrationToken.email == request.email,
        models.RegistrationToken.is_used == False
    ).update({"is_used": True})
    db.commit()
    
    # Generate verification code
    code = generate_verification_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    # Store registration token
    reg_token = models.RegistrationToken(
        email=request.email,
        token=code,
        expires_at=expires_at
    )
    db.add(reg_token)
    db.commit()
    
    # Send verification email
    background_tasks.add_task(
        send_verification_email,
        to_email=request.email,
        code=code,
        subject="CocoGuard - Admin Registration Verification Code",
        template_type="verification"
    )
    
    logger.info(f"Admin registration verification code sent to {request.email}")
    
    return schemas.PasswordResetResponse(
        success=True,
        message="A 6-digit verification code has been sent to your email."
    )


@router.post("/verify-code", response_model=schemas.PasswordResetResponse)
async def verify_registration_code(
    request: schemas.AdminRegisterVerifyCode,
    db: Session = Depends(get_db)
):
    """
    Verify the registration code without creating the account.
    """
    token = db.query(models.RegistrationToken).filter(
        models.RegistrationToken.email == request.email,
        models.RegistrationToken.token == request.code,
        models.RegistrationToken.is_used == False
    ).first()
    
    if not token:
        return schemas.PasswordResetResponse(
            success=False,
            message="Invalid or expired verification code. Please request a new one."
        )
    
    # Check expiration
    now = datetime.now(timezone.utc)
    token_expires = token.expires_at
    if token_expires.tzinfo is None:
        token_expires = token_expires.replace(tzinfo=timezone.utc)
    
    if now > token_expires:
        return schemas.PasswordResetResponse(
            success=False,
            message="Verification code has expired. Please request a new one."
        )
    
    # Mark as verified (but not used - will be used on complete)
    token.is_verified = True
    db.commit()
    
    return schemas.PasswordResetResponse(
        success=True,
        message="Email verified successfully. You can now complete your registration."
    )


@router.post("/complete")
async def complete_admin_registration(
    request: schemas.AdminRegisterComplete,
    db: Session = Depends(get_db)
):
    """
    Complete admin registration after email verification.
    Creates admin account with verified email.
    """
    # Verify the code is valid and verified
    token = db.query(models.RegistrationToken).filter(
        models.RegistrationToken.email == request.email,
        models.RegistrationToken.token == request.code,
        models.RegistrationToken.is_used == False,
        models.RegistrationToken.is_verified == True
    ).first()
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification. Please start the registration process again."
        )
    
    # Check expiration
    now = datetime.now(timezone.utc)
    token_expires = token.expires_at
    if token_expires.tzinfo is None:
        token_expires = token_expires.replace(tzinfo=timezone.utc)
    
    if now > token_expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration code has expired. Please start again."
        )
    
    # Check if email is already registered (race condition check)
    if db.query(models.User).filter(models.User.email == request.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email is already registered."
        )
    
    # Check username uniqueness
    if db.query(models.User).filter(models.User.username == request.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken. Please choose a different username."
        )
    
    # Validate password
    if len(request.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters."
        )
    
    # Create admin user
    hashed_password = get_password_hash(request.password)
    new_user = models.User(
        username=request.username,
        email=request.email,
        password_hash=hashed_password,
        full_name=request.full_name,
        role=models.UserRole.admin,  # Admin account!
        auth_provider="email"
    )
    
    db.add(new_user)
    
    # Mark token as used
    token.is_used = True
    
    db.commit()
    db.refresh(new_user)
    
    # Create JWT token
    access_token = create_access_token({"sub": str(new_user.id)})
    
    logger.info(f"Admin account created: {request.email}")
    
    return {
        "success": True,
        "message": "Admin account created successfully!",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "full_name": new_user.full_name,
            "role": new_user.role.value
        }
    }


@router.post("/resend-code", response_model=schemas.PasswordResetResponse)
async def resend_registration_code(
    request: schemas.AdminRegisterSendCode,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Resend registration verification code."""
    return await send_registration_code(request=request, background_tasks=background_tasks, db=db)


# ====================================================
# SERVER-SIDE GOOGLE OAUTH FLOW
# Works from any origin (LAN IP, localhost, etc.)
# Only http://localhost:8000 needs to be in Google Console
# ====================================================

@router.get("/google-login")
async def google_login_redirect(request: Request):
    """
    Step 1: Redirect user to Google's OAuth consent screen.
    The frontend opens this URL in a popup window.
    """
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google Client ID not configured in .env"
        )
    
    # Store the frontend origin so we can postMessage back to it
    frontend_origin = request.query_params.get("origin", "*")
    
    # Generate a state parameter with the frontend origin embedded
    state = urllib.parse.quote(frontend_origin)
    
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": state,
        "prompt": "select_account",
    }
    
    auth_url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/google-callback")
async def google_callback(
    code: str = None,
    state: str = None,
    error: str = None,
    db: Session = Depends(get_db)
):
    """
    Step 2: Google redirects here with an authorization code.
    We exchange it for tokens, get user info, create/login the user,
    and return an HTML page that sends the result back to the opener window.
    """
    frontend_origin = urllib.parse.unquote(state) if state else "*"
    
    if error:
        return _google_callback_html(
            success=False,
            error=f"Google authorization failed: {error}",
            frontend_origin=frontend_origin
        )
    
    if not code:
        return _google_callback_html(
            success=False,
            error="No authorization code received from Google.",
            frontend_origin=frontend_origin
        )
    
    # Exchange authorization code for tokens
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if token_response.status_code != 200:
                logger.error(f"Google token exchange failed: {token_response.text}")
                return _google_callback_html(
                    success=False,
                    error="Failed to exchange authorization code. Please try again.",
                    frontend_origin=frontend_origin
                )
            
            token_data = token_response.json()
            access_token_google = token_data.get("access_token")
            
            # Get user info from Google
            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token_google}"}
            )
            
            if userinfo_response.status_code != 200:
                return _google_callback_html(
                    success=False,
                    error="Failed to get user info from Google.",
                    frontend_origin=frontend_origin
                )
            
            google_data = userinfo_response.json()
    except httpx.RequestError as e:
        logger.error(f"Google OAuth request failed: {e}")
        return _google_callback_html(
            success=False,
            error="Network error communicating with Google. Please try again.",
            frontend_origin=frontend_origin
        )
    
    google_email = google_data.get("email")
    google_id = google_data.get("sub")
    google_name = google_data.get("name", "")
    email_verified = google_data.get("email_verified", False)
    
    if not google_email or not email_verified:
        return _google_callback_html(
            success=False,
            error="Google email not verified.",
            frontend_origin=frontend_origin
        )
    
    # --- Same user creation/login logic as the POST /google-signin endpoint ---
    
    # Check if user exists by google_id
    user = db.query(models.User).filter(
        models.User.google_id == google_id
    ).first()
    
    if user:
        if user.status == models.UserStatus.inactive:
            return _google_callback_html(
                success=False,
                error="Account is deactivated. Please contact admin.",
                frontend_origin=frontend_origin
            )
        
        token = create_access_token({"sub": str(user.id)})
        return _google_callback_html(
            success=True,
            frontend_origin=frontend_origin,
            result={
                "success": True,
                "is_new_user": False,
                "needs_password": False,
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role.value,
                    "auth_provider": user.auth_provider or "google"
                }
            }
        )
    
    # Check if user exists by email
    user = db.query(models.User).filter(
        models.User.email == google_email
    ).first()
    
    if user:
        user.google_id = google_id
        if not user.full_name and google_name:
            user.full_name = google_name
        db.commit()
        
        if user.status == models.UserStatus.inactive:
            return _google_callback_html(
                success=False,
                error="Account is deactivated. Please contact admin.",
                frontend_origin=frontend_origin
            )
        
        token = create_access_token({"sub": str(user.id)})
        return _google_callback_html(
            success=True,
            frontend_origin=frontend_origin,
            result={
                "success": True,
                "is_new_user": False,
                "needs_password": False,
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role.value,
                    "auth_provider": user.auth_provider or "google"
                }
            }
        )
    
    # New user - create admin account
    base_username = google_email.split("@")[0]
    username = base_username
    counter = 1
    while db.query(models.User).filter(models.User.username == username).first():
        username = f"{base_username}{counter}"
        counter += 1
    
    temp_password = sec_module.token_urlsafe(32)
    
    new_user = models.User(
        username=username,
        email=google_email,
        password_hash=get_password_hash(temp_password),
        full_name=google_name,
        role=models.UserRole.admin,
        google_id=google_id,
        auth_provider="google"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    token = create_access_token({"sub": str(new_user.id)})
    logger.info(f"New admin account created via Google: {google_email}")
    
    return _google_callback_html(
        success=True,
        frontend_origin=frontend_origin,
        result={
            "success": True,
            "is_new_user": True,
            "needs_password": True,
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
                "full_name": new_user.full_name,
                "role": new_user.role.value,
                "auth_provider": "google"
            }
        }
    )


def _google_callback_html(success: bool, frontend_origin: str, result: dict = None, error: str = None):
    """
    Redirect the popup back to the frontend's origin with the result
    encoded in the URL hash. This makes the popup same-origin as the
    parent window, so postMessage and window.close() work without
    Cross-Origin-Opener-Policy issues.
    """
    import json
    import base64
    
    if success:
        payload = json.dumps({"type": "google-oauth-result", "result": result})
    else:
        payload = json.dumps({"type": "google-oauth-result", "error": error})
    
    # Base64-encode the result to safely pass in URL hash
    encoded = base64.urlsafe_b64encode(payload.encode()).decode()
    
    # Redirect to the frontend callback page (same origin as opener)
    # URL fragment (#) is never sent to the server, keeping tokens safe
    redirect_url = f"{frontend_origin}/cocoguard_web/google-callback.html#result={encoded}"
    
    return RedirectResponse(url=redirect_url)


@router.post("/google-signin")
async def google_sign_in(
    request: schemas.GoogleSignInRequest,
    db: Session = Depends(get_db)
):
    """
    Sign in or register with Google for admin accounts.
    - If the Google account is already linked, log them in.
    - If the email exists but no Google link, link it and log in.
    - If new email, create admin account (will need to set password).
    """
    # Verify Google token
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GOOGLE_TOKEN_INFO_URL}?id_token={request.google_token}"
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Google token. Please try again."
                )
            
            google_data = response.json()
            
            # Validate token
            google_email = google_data.get("email")
            google_id = google_data.get("sub")
            google_name = google_data.get("name", "")
            email_verified = google_data.get("email_verified", "false")
            
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
        # Existing Google-linked user - log them in
        if user.status == models.UserStatus.inactive:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Please contact admin."
            )
        
        token = create_access_token({"sub": str(user.id)})
        return {
            "success": True,
            "is_new_user": False,
            "needs_password": False,
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "auth_provider": user.auth_provider or "google"
            }
        }
    
    # Check if user exists by email
    user = db.query(models.User).filter(
        models.User.email == google_email
    ).first()
    
    if user:
        # Existing email user - link Google account
        user.google_id = google_id
        if not user.full_name and google_name:
            user.full_name = google_name
        db.commit()
        
        if user.status == models.UserStatus.inactive:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Please contact admin."
            )
        
        token = create_access_token({"sub": str(user.id)})
        return {
            "success": True,
            "is_new_user": False,
            "needs_password": False,
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "auth_provider": user.auth_provider or "google"
            }
        }
    
    # New user - create admin account with Google
    # Generate a username from email
    base_username = google_email.split("@")[0]
    username = base_username
    counter = 1
    while db.query(models.User).filter(models.User.username == username).first():
        username = f"{base_username}{counter}"
        counter += 1
    
    # Create user with a temporary password hash (they need to set a real password)
    import secrets
    temp_password = secrets.token_urlsafe(32)
    
    new_user = models.User(
        username=username,
        email=google_email,
        password_hash=get_password_hash(temp_password),
        full_name=google_name,
        role=models.UserRole.admin,  # Admin account!
        google_id=google_id,
        auth_provider="google"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    token = create_access_token({"sub": str(new_user.id)})
    
    logger.info(f"New admin account created via Google: {google_email}")
    
    return {
        "success": True,
        "is_new_user": True,
        "needs_password": True,
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "full_name": new_user.full_name,
            "role": new_user.role.value,
            "auth_provider": "google"
        }
    }


@router.post("/google-set-password")
async def google_set_password(
    request: schemas.GoogleSetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Set password for a Google-authenticated admin user.
    Called after Google sign-in for new users.
    """
    user = db.query(models.User).filter(
        models.User.email == request.email
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    
    if len(request.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters."
        )
    
    user.password_hash = get_password_hash(request.password)
    db.commit()
    
    logger.info(f"Password set for Google user: {request.email}")
    
    return {
        "success": True,
        "message": "Password set successfully! You can now login with email and password too."
    }
