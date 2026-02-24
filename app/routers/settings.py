from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, UserSettings
from ..schemas import UserSettingsOut, UserSettingsUpdate
from ..deps import get_current_user

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/", response_model=UserSettingsOut)
def get_user_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's settings.
    If settings don't exist, create default settings.
    """
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()
    
    if not settings:
        # Create default settings for user
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return settings


@router.put("/", response_model=UserSettingsOut)
def update_user_settings(
    settings_update: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's settings.
    """
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()
    
    if not settings:
        # Create settings if they don't exist
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
    
    # Update only provided fields
    update_data = settings_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    db.commit()
    db.refresh(settings)
    
    return settings


@router.post("/reset", response_model=UserSettingsOut)
def reset_user_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reset user settings to defaults.
    """
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()
    
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
    else:
        # Reset to defaults
        settings.email_notifications = True
        settings.sms_notifications = False
        settings.push_notifications = True
        settings.two_factor_enabled = False
        settings.auto_backup = True
        settings.language = "en"
        settings.theme = "light"
        settings.profile_visible = True
        settings.data_sharing = False
    
    db.commit()
    db.refresh(settings)
    
    return settings
