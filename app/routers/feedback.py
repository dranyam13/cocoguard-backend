from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from typing import List

from .. import models, schemas
from ..deps import get_db, get_current_user, get_current_admin

router = APIRouter(prefix="/feedback", tags=["feedback"])


# Add Feedback model if not exists

# Use schemas.FeedbackCreate directly (type, message, user_id)



# Use schemas.FeedbackOut directly (id, message, type, user_id, created_at)


from fastapi import Request


def _create_admin_notification_for_oos_report(db: Session, feedback_message: str, user_id: int = None, scan_id: int = None):
    """Create a notification for admin when an out-of-scope pest report is submitted."""
    try:
        # Get the reporter's name
        reporter_name = "Unknown User"
        if user_id:
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if user:
                reporter_name = user.full_name or user.username

        # Look up the scan record to get image_url, location, etc.
        scan_image_url = None
        scan_location_text = None
        resolved_scan_id = scan_id
        if scan_id:
            scan = db.query(models.Scan).filter(models.Scan.id == scan_id).first()
            if scan:
                scan_image_url = scan.image_url
                scan_location_text = scan.location_text
        elif user_id:
            # Fallback: get the user's most recent scan
            scan = db.query(models.Scan).filter(
                models.Scan.user_id == user_id
            ).order_by(models.Scan.created_at.desc()).first()
            if scan:
                resolved_scan_id = scan.id
                scan_image_url = scan.image_url
                scan_location_text = scan.location_text

        # Create notification for all admins
        admins = db.query(models.User).filter(
            models.User.role == models.UserRole.admin,
            models.User.status == models.UserStatus.active
        ).all()

        title = "🔍 Out-of-Scope Pest Detection Report"
        message = (
            f"Si {reporter_name} ay nag-report ng out-of-scope pest detection.\n\n"
            f"Mensahe: {feedback_message}\n\n"
            "Mangyaring suriin ang report sa Reports & Feedback section."
        )

        notifications_created = 0
        for admin in admins:
            notification = models.Notification(
                user_id=admin.id,
                title=title,
                message=message,
                type=models.NotificationType.out_of_scope_report,
                scan_id=resolved_scan_id,
                location_text=scan_location_text,
                pest_type="Out-of-Scope",
                is_read=False
            )
            db.add(notification)
            notifications_created += 1

        # Also create a global notification visible on admin dashboard
        global_notification = models.Notification(
            user_id=None,
            title=title,
            message=message,
            type=models.NotificationType.out_of_scope_report,
            scan_id=resolved_scan_id,
            location_text=scan_location_text,
            pest_type="Out-of-Scope",
            is_read=False
        )
        db.add(global_notification)

        db.commit()
        print(f"[INFO] 🔍 Out-of-scope report notification sent to {notifications_created} admin(s)")
        return notifications_created + 1
    except Exception as e:
        print(f"[WARNING] Failed to create admin notification for OOS report: {e}")
        return 0


@router.post("", response_model=schemas.FeedbackOut)
async def submit_feedback(
    feedback: schemas.FeedbackCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Submit feedback from users (mobile/web, with or without auth)"""
    if not hasattr(models, 'Feedback'):
        raise HTTPException(
            status_code=501,
            detail="Feedback feature is not available yet"
        )
    # Always use the authenticated user's ID — ignore body user_id to prevent impersonation
    user_id = current_user.id
    db_feedback = models.Feedback(
        user_id=user_id,
        message=feedback.message,
        type=feedback.type
    )
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)

    # If this is an out-of-scope report, notify admins
    if feedback.type and feedback.type.lower() == 'out-of-scope report':
        _create_admin_notification_for_oos_report(db, feedback.message, user_id, feedback.scan_id)

    return db_feedback


@router.get("", response_model=List[schemas.FeedbackOut])
def get_feedback(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin),
    limit: int = 50,
    skip: int = 0,
):
    """Get all feedback (admin only)"""
    if not hasattr(models, 'Feedback'):
        return []
    feedback = db.query(models.Feedback)\
        .order_by(desc(models.Feedback.created_at))\
        .offset(skip)\
        .limit(limit)\
        .all()
    return feedback


@router.get("/user/me", response_model=List[schemas.FeedbackOut])
def get_my_feedback(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    limit: int = 50,
):
    """Get current user's feedback"""
    if not hasattr(models, 'Feedback'):
        return []
    feedback = db.query(models.Feedback)\
        .filter(models.Feedback.user_id == current_user.id)\
        .order_by(desc(models.Feedback.created_at))\
        .limit(limit)\
        .all()
    return feedback


# Duplicate trailing-slash routes removed — use POST "" and GET "" above

from sqlalchemy.orm import joinedload


def _create_user_notification_for_feedback_response(
    db: Session, 
    feedback: models.Feedback, 
    admin_name: str,
    status: str,
    admin_response: str = None
):
    """Create a notification for the user when admin responds to their feedback/report."""
    try:
        if not feedback.user_id:
            print("[INFO] No user_id for feedback, skipping notification")
            return 0
        
        # Determine response title based on status
        status_titles = {
            "Real Pest": "✅ Your Report Confirmed - Real Pest",
            "New Pest": "🆕 Your Report Identified - New Pest Species",
            "Not a Pest": "ℹ️ Your Report Reviewed - Not a Pest",
            "In Review": "🔍 Your Report is Being Reviewed",
            "Resolved": "✓ Your Feedback Has Been Resolved",
        }
        title = status_titles.get(status, f"📋 Feedback Update: {status}")
        
        # Build message
        message = f"Admin {admin_name} has reviewed your submission.\n\nStatus: {status}"
        if admin_response:
            message += f"\n\nAdmin Response: {admin_response}"
        
        notification = models.Notification(
            user_id=feedback.user_id,
            title=title,
            message=message,
            type=models.NotificationType.info,
            is_read=False
        )
        db.add(notification)
        db.commit()
        
        print(f"[INFO] 📬 Notification sent to user {feedback.user_id} for feedback response")
        return 1
        
    except Exception as e:
        print(f"[WARNING] Failed to create user notification for feedback response: {e}")
        return 0


@router.put("/{feedback_id}/respond", response_model=schemas.FeedbackOut)
async def respond_to_feedback(
    feedback_id: int,
    response_data: schemas.FeedbackRespond,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin),
):
    """
    Admin responds to a feedback/report.
    
    Status options:
    - "Real Pest" - Confirmed as a real pest detection
    - "New Pest" - Identified as a new pest species not in the system
    - "Not a Pest" - Not a pest (false positive or other object)
    - "In Review" - Still being reviewed
    - "Resolved" - Issue has been resolved
    """
    from datetime import datetime, timezone
    
    # Find the feedback
    feedback = db.query(models.Feedback).filter(models.Feedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    # Validate status
    valid_statuses = ["Received", "In Review", "Real Pest", "New Pest", "Not a Pest", "Resolved"]
    if response_data.status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    # Update feedback with admin response
    feedback.status = response_data.status
    feedback.admin_response = response_data.admin_response
    feedback.admin_response_by = current_admin.id
    feedback.responded_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(feedback)
    
    # Send notification to user
    admin_name = current_admin.full_name or current_admin.username
    _create_user_notification_for_feedback_response(
        db, feedback, admin_name, response_data.status, response_data.admin_response
    )
    
    return feedback


@router.get("/{feedback_id}", response_model=schemas.FeedbackOut)
def get_feedback_by_id(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get a specific feedback by ID (user can only see their own, admin can see all)"""
    feedback = db.query(models.Feedback).filter(models.Feedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    # Check access - user can only see their own feedback unless admin
    if current_user.role != models.UserRole.admin and feedback.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this feedback")
    
    return feedback
