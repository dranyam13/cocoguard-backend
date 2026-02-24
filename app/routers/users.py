from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional

from .. import models, schemas
from ..deps import get_db, get_current_user, get_current_admin
from ..auth_utils import get_password_hash

router = APIRouter(prefix="/users", tags=["users"])


# Schema for admin creating a user
class AdminUserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: str = "user"  # "admin" or "user"


# Admin creates a new user
@router.post("", dependencies=[Depends(get_current_admin)])
def create_user(data: AdminUserCreate, db: Session = Depends(get_db)):
    # Check email uniqueness
    if db.query(models.User).filter(models.User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check username uniqueness
    if db.query(models.User).filter(models.User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Validate role
    if data.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin' or 'user'")
    
    # Hash password
    hashed_password = get_password_hash(data.password)
    
    # Create user
    new_user = models.User(
        username=data.username,
        email=data.email,
        password_hash=hashed_password,
        full_name=data.full_name,
        phone=data.phone,
        role=models.UserRole.admin if data.role == "admin" else models.UserRole.user,
        status=models.UserStatus.active  # New users created by admin are active
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "success": True,
        "message": "User created successfully",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "role": new_user.role,
            "status": new_user.status
        }
    }


# Activate or deactivate a user (admin only)
@router.put("/{user_id}/status", dependencies=[Depends(get_current_admin)])
def set_user_status(user_id: int, status: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if status not in ("active", "inactive"):
        raise HTTPException(status_code=400, detail="Invalid status")
    user.status = status
    db.commit()
    db.refresh(user)
    return {"success": True, "user_id": user.id, "status": user.status}

@router.get("/me", response_model=schemas.UserOut)
def read_me(current_user: models.User = Depends(get_current_user)):
    return current_user


# admin listing users (for User Management page)
@router.get("", dependencies=[Depends(get_current_admin)])
def list_users(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "status": u.status,
            "date_joined": u.created_at,
            "full_name": u.full_name,
            "phone": u.phone,
            "address_line": u.address_line,
            "region": u.region,
            "province": u.province,
            "city": u.city,
            "barangay": u.barangay,
            "created_at": u.created_at,
            "updated_at": u.updated_at,
        }
        for u in users
    ]


# Schema for FCM token update
class FCMTokenUpdate(BaseModel):
    fcm_token: str


# Update FCM token for push notifications
@router.post("/fcm-token")
def update_fcm_token(
    data: FCMTokenUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Update the FCM (Firebase Cloud Messaging) token for the current user.
    This token is used to send push notifications to the user's device.
    """
    current_user.fcm_token = data.fcm_token
    db.commit()
    
    return {
        "success": True,
        "message": "FCM token updated successfully"
    }


# Get users with FCM tokens (for sending push notifications)
@router.get("/fcm-tokens", dependencies=[Depends(get_current_admin)])
def get_fcm_tokens(db: Session = Depends(get_db)):
    """
    Get all active users with FCM tokens.
    Used by the notification service to send push notifications.
    """
    users_with_tokens = db.query(models.User).filter(
        models.User.status == models.UserStatus.active,
        models.User.fcm_token != None,
        models.User.fcm_token != ""
    ).all()
    
    return [
        {
            "user_id": u.id,
            "username": u.username
        }
        for u in users_with_tokens
    ]
