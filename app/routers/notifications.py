"""
Notifications Router - Handles pest alert notifications for all users
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta

from .. import models
from ..deps import get_db, get_current_user, get_current_admin
from ..utils.timezone import to_manila_iso
from ..services.fcm_service import send_pest_alert_notification

router = APIRouter(prefix="/notifications", tags=["notifications"])

# Threshold for outbreak alert - when any pest reaches this many total scans across all users
OUTBREAK_THRESHOLD = 3


# Schemas for notifications
class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    type: str
    pest_type: Optional[str] = None
    location_text: Optional[str] = None
    scan_id: Optional[int] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationCreate(BaseModel):
    title: str
    message: str
    type: str = "pest_alert"
    pest_type: Optional[str] = None
    location_text: Optional[str] = None
    scan_id: Optional[int] = None


class MarkReadRequest(BaseModel):
    notification_ids: List[int]


# Helper function to create notifications for all users when dangerous pest is detected
def create_pest_alert_for_all_users(
    db: Session,
    pest_type: str,
    scan_id: int,
    location_text: str = None,
    detected_by_user_id: int = None
):
    """
    Create a pest alert notification for ALL users when a dangerous pest is detected.
    This is called when Asiatic Palm Weevil (APW Adult or APW Larvae) is detected.
    Also sends push notifications via Firebase Cloud Messaging.
    """
    # Get all active users
    users = db.query(models.User).filter(
        models.User.status == models.UserStatus.active
    ).all()
    
    # Create notification message
    title = "⚠️ Mapanganib na Peste ang Natuklasan!"
    message = (
        f"Ang Asiatic Palm Weevil ({pest_type}) ay natuklasan sa lugar na: "
        f"{location_text or 'Hindi matukoy ang lokasyon'}.\n\n"
        "Ang pesteng ito ay lubhang mapanganib sa mga puno ng niyog at maaaring "
        "mabilis na kumalat. Mangyaring suriin ang inyong mga puno at makipag-ugnayan "
        "sa PCA kung makakita ng mga senyales ng impeksyon.\n\n"
        "⚠️ BABALA: Kailangang gumawa ng agarang aksyon para maiwasan ang pagkalat!"
    )
    
    notifications_created = []
    fcm_tokens = []  # Collect FCM tokens for push notifications
    
    for user in users:
        # Create notification for each user
        notification = models.Notification(
            user_id=user.id,
            title=title,
            message=message,
            type=models.NotificationType.pest_alert,
            pest_type=pest_type,
            scan_id=scan_id,
            location_text=location_text,
            is_read=False
        )
        db.add(notification)
        notifications_created.append(notification)
        
        # Collect FCM token if available
        if user.fcm_token:
            fcm_tokens.append(user.fcm_token)
    
    # Also create a global notification (user_id=NULL) for admin dashboard
    global_notification = models.Notification(
        user_id=None,  # NULL means global/admin notification
        title=title,
        message=message,
        type=models.NotificationType.pest_alert,
        pest_type=pest_type,
        scan_id=scan_id,
        location_text=location_text,
        is_read=False
    )
    db.add(global_notification)
    
    db.commit()
    
    # Send push notifications via FCM - ONLY to topic, not individual tokens
    # This prevents duplicate notifications since users are already subscribed to the topic
    try:
        fcm_result = send_pest_alert_notification(
            pest_type=pest_type,
            location_text=location_text,
            scan_id=scan_id,
            fcm_tokens=None,  # Don't send to individual tokens to avoid duplicates
            send_to_topic=True  # Only broadcast to topic subscribers
        )
        print(f"[FCM] Push notification result: {fcm_result}")
    except Exception as e:
        print(f"[FCM] Failed to send push notifications: {e}")
        # Don't raise - push notification failure shouldn't break the flow
    
    return len(notifications_created) + 1  # +1 for global notification


def check_and_create_outbreak_alert(
    db: Session,
    pest_type: str,
    scan_id: int,
    location_text: str = None,
    detected_by_user_id: int = None
):
    """
    Check if a pest has reached the OUTBREAK_THRESHOLD (3 total scans across all users).
    Sends notification every time the threshold is hit (3, 6, 9, 12, etc.)
    
    This implements the feature: when ANY combination of users scans the same pest
    3 times total (e.g., User A scans Rhinoceros Beetle, User B scans it, User C scans it),
    ALL users get notified about the potential outbreak.
    
    Notifications are sent at every multiple of OUTBREAK_THRESHOLD:
    - 3 scans → 1st outbreak notification
    - 6 scans → 2nd outbreak notification  
    - 9 scans → 3rd outbreak notification
    - etc.
    
    Returns:
        - Number of notifications sent if outbreak threshold reached
        - 0 if not at a threshold multiple
    """
    # Skip APW pests as they already have their own alert system
    dangerous_pests = ['APW Adult', 'APW Larvae']
    if pest_type in dangerous_pests:
        return 0  # APW has its own notification, skip outbreak check
    
    # Find the pest_type in the database to get the pest_type_id
    pest_type_record = db.query(models.PestType).filter(
        models.PestType.name.ilike(f"%{pest_type}%")
    ).first()
    
    if not pest_type_record:
        print(f"[OUTBREAK] Pest type '{pest_type}' not found in database")
        return 0
    
    pest_type_id = pest_type_record.id
    
    # Count total scans of this pest type across ALL users
    total_scans = db.query(func.count(models.Scan.id)).filter(
        models.Scan.pest_type_id == pest_type_id
    ).scalar()
    
    print(f"[OUTBREAK] Pest '{pest_type}' has {total_scans} total scans across all users")
    
    # Check if we're at an exact multiple of the threshold (3, 6, 9, 12, etc.)
    # Only send notification when we hit exactly 3, 6, 9, 12... not in between
    if total_scans < OUTBREAK_THRESHOLD or total_scans % OUTBREAK_THRESHOLD != 0:
        print(f"[OUTBREAK] Not at threshold multiple ({total_scans} scans, threshold={OUTBREAK_THRESHOLD})")
        return 0
    
    # Calculate which outbreak wave this is (1st, 2nd, 3rd, etc.)
    outbreak_wave = total_scans // OUTBREAK_THRESHOLD
    
    # THRESHOLD REACHED! Send outbreak alert to all users
    print(f"[OUTBREAK] 🚨 OUTBREAK WAVE #{outbreak_wave} for '{pest_type}'! ({total_scans} scans)")
    print(f"[OUTBREAK] Sending outbreak alert to all users...")
    
    # Get all active users
    users = db.query(models.User).filter(
        models.User.status == models.UserStatus.active
    ).all()
    
    # Create notification message with wave number
    if outbreak_wave == 1:
        title = f"🚨 Posibleng Pagkalat ng {pest_type}!"
    else:
        title = f"🚨 Patuloy na Pagkalat ng {pest_type}! (#{outbreak_wave})"
    
    message = (
        f"BABALA: Ang {pest_type} ay nakitaan na ng {total_scans} beses sa iba't ibang lokasyon ng mga magsasaka.\n\n"
        f"Ito ay posibleng senyales ng {'malawakang ' if outbreak_wave > 1 else ''}pagkalat ng peste sa inyong lugar. "
        f"Mangyaring suriin ang inyong mga puno ng niyog at gumawa ng mga hakbang para maiwasan ang pagdami.\n\n"
        f"📍 Huling lokasyon: {location_text or 'Hindi matukoy'}\n\n"
        "Makipag-ugnayan sa PCA kung makakita ng mga senyales ng impeksyon."
    )
    
    notifications_created = []
    fcm_tokens = []  # Collect FCM tokens for push notifications
    
    for user in users:
        # Create notification for each user
        notification = models.Notification(
            user_id=user.id,
            title=title,
            message=message,
            type=models.NotificationType.pest_alert,
            pest_type=pest_type,
            scan_id=scan_id,
            location_text=location_text,
            is_read=False
        )
        db.add(notification)
        notifications_created.append(notification)
        
        # Collect FCM token if available
        if user.fcm_token:
            fcm_tokens.append(user.fcm_token)
    
    # Also create a global notification (user_id=NULL) for admin dashboard
    global_notification = models.Notification(
        user_id=None,  # NULL means global/admin notification
        title=f"🚨 Outbreak Alert #{outbreak_wave}: {pest_type}",
        message=f"Pest outbreak wave #{outbreak_wave}! {pest_type} detected {total_scans} times across all users. Location: {location_text or 'Unknown'}",
        type=models.NotificationType.pest_alert,
        pest_type=pest_type,
        scan_id=scan_id,
        location_text=location_text,
        is_read=False
    )
    db.add(global_notification)
    
    db.commit()
    
    # Send push notifications via FCM - ONLY to topic, not individual tokens
    # This prevents duplicate notifications since users are already subscribed to the topic
    try:
        fcm_result = send_pest_alert_notification(
            pest_type=f"OUTBREAK #{outbreak_wave}: {pest_type}",
            location_text=f"{total_scans} detections - {location_text or 'Multiple locations'}",
            scan_id=scan_id,
            fcm_tokens=None,  # Don't send to individual tokens to avoid duplicates
            send_to_topic=True  # Only broadcast to topic subscribers
        )
        print(f"[FCM] Outbreak push notification result: {fcm_result}")
    except Exception as e:
        print(f"[FCM] Failed to send outbreak push notifications: {e}")
    
    print(f"[OUTBREAK] ✅ Sent {len(notifications_created) + 1} outbreak notifications!")
    return len(notifications_created) + 1  # +1 for global notification


@router.get("", response_model=List[NotificationOut])
def get_my_notifications(
    unread_only: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get notifications for the current user"""
    query = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id
    )
    
    if unread_only:
        query = query.filter(models.Notification.is_read == False)
    
    notifications = query.order_by(
        models.Notification.created_at.desc()
    ).limit(limit).all()
    
    # Convert timestamps to Manila timezone
    return [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.type.value if n.type else "pest_alert",
            "pest_type": n.pest_type,
            "location_text": n.location_text,
            "scan_id": n.scan_id,
            "is_read": n.is_read,
            "created_at": to_manila_iso(n.created_at)
        }
        for n in notifications
    ]


@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get count of unread notifications for current user"""
    count = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False
    ).count()
    
    return {"unread_count": count}


@router.post("/mark-read")
def mark_notifications_read(
    request: MarkReadRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Mark specific notifications as read"""
    updated = db.query(models.Notification).filter(
        models.Notification.id.in_(request.notification_ids),
        models.Notification.user_id == current_user.id
    ).update({"is_read": True}, synchronize_session=False)
    
    db.commit()
    
    return {"message": f"Marked {updated} notifications as read"}


@router.post("/mark-all-read")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Mark all notifications as read for current user"""
    updated = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False
    ).update({"is_read": True}, synchronize_session=False)
    
    db.commit()
    
    return {"message": f"Marked {updated} notifications as read"}


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Delete a specific notification"""
    notification = db.query(models.Notification).filter(
        models.Notification.id == notification_id,
        models.Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    db.delete(notification)
    db.commit()
    
    return {"message": "Notification deleted"}


# Admin endpoints
@router.get("/admin/all", dependencies=[Depends(get_current_admin)])
def admin_get_all_notifications(
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Admin: Get all notifications including global ones"""
    notifications = db.query(models.Notification).order_by(
        models.Notification.created_at.desc()
    ).limit(limit).all()
    
    return [
        {
            "id": n.id,
            "user_id": n.user_id,
            "username": n.user.username if n.user else "Global",
            "title": n.title,
            "message": n.message,
            "type": n.type.value if n.type else "pest_alert",
            "pest_type": n.pest_type,
            "location_text": n.location_text,
            "scan_id": n.scan_id,
            "is_read": n.is_read,
            "created_at": to_manila_iso(n.created_at)
        }
        for n in notifications
    ]


@router.get("/admin/pest-alerts", dependencies=[Depends(get_current_admin)])
def admin_get_pest_alerts(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Admin: Get pest alert and out-of-scope report notifications (global ones) with scan details"""
    notifications = db.query(models.Notification).filter(
        models.Notification.user_id == None,  # Global notifications
        or_(
            models.Notification.type == models.NotificationType.pest_alert,
            models.Notification.type == models.NotificationType.out_of_scope_report,
        )
    ).order_by(
        models.Notification.created_at.desc()
    ).limit(limit).all()
    
    return [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "pest_type": n.pest_type,
            "location_text": n.location_text,
            "scan_id": n.scan_id,
            "created_at": to_manila_iso(n.created_at),
            # Add scan details if scan exists
            "image_url": n.scan.image_url if n.scan else None,
            "latitude": float(n.scan.latitude) if n.scan and n.scan.latitude else None,
            "longitude": float(n.scan.longitude) if n.scan and n.scan.longitude else None,
            "farmer_name": n.scan.user.full_name if n.scan and n.scan.user else None,
        }
        for n in notifications
    ]


@router.post("/admin/test-push", dependencies=[Depends(get_current_admin)])
def admin_test_push_notification():
    """
    Admin: Send a test push notification to verify FCM is working.
    This sends a test notification to the pest_alerts topic.
    """
    try:
        result = send_pest_alert_notification(
            pest_type="APW Adult (TEST)",
            location_text="Test Location - This is a test notification",
            scan_id=None,
            fcm_tokens=None,
            send_to_topic=True
        )
        return {
            "success": result.get("success", False),
            "message": result.get("message", "Unknown result"),
            "details": result
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "details": None
        }
