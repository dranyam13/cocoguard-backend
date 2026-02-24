from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import List, Optional

from .. import models
from ..deps import get_db, get_current_user, get_current_admin

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard/summary")
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get dashboard summary for current user"""
    
    # Calculate today's date boundaries
    now = datetime.utcnow()
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_yesterday = start_of_today - timedelta(days=1)
    
    # Total scans
    total_scans = db.query(func.count(models.Scan.id))\
        .filter(models.Scan.user_id == current_user.id).scalar() or 0
    
    # Today's scans for this user
    today_scans = db.query(func.count(models.Scan.id))\
        .filter(
            and_(
                models.Scan.user_id == current_user.id,
                models.Scan.created_at >= start_of_today
            )
        ).scalar() or 0
    
    # Yesterday's scans for this user
    yesterday_scans = db.query(func.count(models.Scan.id))\
        .filter(
            and_(
                models.Scan.user_id == current_user.id,
                models.Scan.created_at >= start_of_yesterday,
                models.Scan.created_at < start_of_today
            )
        ).scalar() or 0
    
    # Verified scans
    verified_scans = db.query(func.count(models.Scan.id))\
        .filter(
            and_(
                models.Scan.user_id == current_user.id,
                models.Scan.status == models.ScanStatus.verified
            )
        ).scalar() or 0
    
    # Total farms
    total_farms = db.query(func.count(models.Farm.id))\
        .filter(models.Farm.user_id == current_user.id).scalar() or 0
    
    # Recent scans
    recent_scans = db.query(models.Scan)\
        .filter(models.Scan.user_id == current_user.id)\
        .order_by(models.Scan.created_at.desc())\
        .limit(10).all()
    
    recent_scans_data = [
        {
            "id": scan.id,
            "farm_id": scan.farm_id,
            "pest_type": scan.pest_type.name if scan.pest_type else "Unknown",
            "confidence": float(scan.confidence) if scan.confidence else 0,
            "status": scan.status.value,
            "created_at": scan.created_at.isoformat(),
        }
        for scan in recent_scans
    ]
    
    return {
        "total_scans": total_scans,
        "today_scans": today_scans,
        "yesterday_scans": yesterday_scans,
        "verified_scans": verified_scans,
        "total_farms": total_farms,
        "recent_scans": recent_scans_data,
    }


@router.get("/scans/by-pest")
def get_scans_by_pest(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    days: int = 30,
):
    """Get scan distribution by pest type"""
    
    since = datetime.utcnow() - timedelta(days=days)
    
    scans_by_pest = db.query(
        models.PestType.name,
        func.count(models.Scan.id).label("count")
    ).join(models.Scan, models.Scan.pest_type_id == models.PestType.id)\
    .filter(
        and_(
            models.Scan.user_id == current_user.id,
            models.Scan.created_at >= since
        )
    ).group_by(models.PestType.name).all()
    
    return [
        {"pest": pest, "count": count}
        for pest, count in scans_by_pest
    ]


@router.get("/scans/by-status")
def get_scans_by_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get scan distribution by status"""
    
    scans_by_status = db.query(
        models.Scan.status,
        func.count(models.Scan.id).label("count")
    ).filter(models.Scan.user_id == current_user.id)\
    .group_by(models.Scan.status).all()
    
    return [
        {"status": status.value if status else "Unknown", "count": count}
        for status, count in scans_by_status
    ]


@router.get("/scans/trends")
def get_scan_trends(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    days: int = 30,
):
    """Get daily scan trends"""
    
    since = datetime.utcnow() - timedelta(days=days)
    
    daily_scans = db.query(
        func.date(models.Scan.created_at).label("date"),
        func.count(models.Scan.id).label("count")
    ).filter(
        and_(
            models.Scan.user_id == current_user.id,
            models.Scan.created_at >= since
        )
    ).group_by(func.date(models.Scan.created_at))\
    .order_by(func.date(models.Scan.created_at)).all()
    
    return [
        {"date": date.isoformat(), "count": count}
        for date, count in daily_scans
    ]


@router.get("/farms/summary")
def get_farms_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get summary of farms for current user"""
    
    farms = db.query(models.Farm)\
        .filter(models.Farm.user_id == current_user.id).all()
    
    farms_data = []
    for farm in farms:
        scan_count = db.query(func.count(models.Scan.id))\
            .filter(models.Scan.farm_id == farm.id).scalar() or 0
        
        farms_data.append({
            "id": farm.id,
            "name": farm.name,
            "plantation_name": farm.plantation_name,
            "total_trees": farm.total_trees,
            "scan_count": scan_count,
            "location": f"{farm.city}, {farm.province}" if farm.city else "Not specified",
        })
    
    return farms_data


@router.get("/admin/system-stats")
def get_system_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin),
):
    """Get system-wide statistics (admin only)"""
    
    total_users = db.query(func.count(models.User.id)).scalar() or 0
    total_scans = db.query(func.count(models.Scan.id)).scalar() or 0
    total_farms = db.query(func.count(models.Farm.id)).scalar() or 0
    
    pending_verifications = db.query(func.count(models.Scan.id))\
        .filter(models.Scan.status == models.ScanStatus.pending).scalar() or 0
    
    high_risk_scans = db.query(func.count(models.Scan.id))\
        .join(models.PestType)\
        .filter(models.PestType.risk_level == models.PestRiskLevel.high).scalar() or 0
    
    return {
        "total_users": total_users,
        "total_scans": total_scans,
        "total_farms": total_farms,
        "pending_verifications": pending_verifications,
        "high_risk_scans": high_risk_scans,
    }


@router.get("/admin/dashboard/summary")
def get_admin_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin),
):
    """Get admin dashboard summary with system-wide statistics (admin only)"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Current month boundaries
    now = datetime.utcnow()
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    first_of_prev_month = (first_of_month - timedelta(days=1)).replace(day=1)
    
    # Today's scans (start of today UTC)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_scans = db.query(func.count(models.Scan.id))\
        .filter(models.Scan.created_at >= start_of_today).scalar() or 0
    
    logger.info(f"[ANALYTICS] UTC now: {now}, start_of_today: {start_of_today}, today_scans: {today_scans}")
    print(f"[ANALYTICS] UTC now: {now}, start_of_today: {start_of_today}, today_scans: {today_scans}")
    
    # Yesterday's scans for comparison
    start_of_yesterday = start_of_today - timedelta(days=1)
    yesterday_scans = db.query(func.count(models.Scan.id))\
        .filter(
            and_(
                models.Scan.created_at >= start_of_yesterday,
                models.Scan.created_at < start_of_today
            )
        ).scalar() or 0
    
    # Total scans (ALL users)
    total_scans = db.query(func.count(models.Scan.id)).scalar() or 0
    
    # Total scans from previous month
    prev_month_total_scans = db.query(func.count(models.Scan.id))\
        .filter(
            and_(
                models.Scan.created_at >= first_of_prev_month,
                models.Scan.created_at < first_of_month
            )
        ).scalar() or 0
    
    # Verified scans (ALL users)
    verified_scans = db.query(func.count(models.Scan.id))\
        .filter(models.Scan.status == models.ScanStatus.verified).scalar() or 0
    
    # Previous month verified scans
    prev_month_verified_scans = db.query(func.count(models.Scan.id))\
        .filter(
            and_(
                models.Scan.status == models.ScanStatus.verified,
                models.Scan.created_at >= first_of_prev_month,
                models.Scan.created_at < first_of_month
            )
        ).scalar() or 0
    
    # Total users (active users)
    total_users = db.query(func.count(models.User.id)).scalar() or 0
    active_users = db.query(func.count(models.User.id))\
        .filter(models.User.status == 'active').scalar() or 0
    prev_month_active_users = 0  # Could be tracked if needed
    
    # Total farms
    total_farms = db.query(func.count(models.Farm.id)).scalar() or 0
    
    # Recent scans (ALL users, for admin view)
    recent_scans = db.query(models.Scan)\
        .order_by(models.Scan.created_at.desc())\
        .limit(10).all()
    
    recent_scans_data = [
        {
            "id": scan.id,
            "user_id": scan.user_id,
            "farm_id": scan.farm_id,
            "pest_type": scan.pest_type.name if scan.pest_type else "Unknown",
            "confidence": float(scan.confidence) if scan.confidence else 0,
            "status": scan.status.value,
            "location_text": scan.location_text or "Unknown Location",
            "created_at": scan.created_at.isoformat(),
        }
        for scan in recent_scans
    ]
    
    return {
        "total_scans": total_scans,
        "prev_month_total_scans": prev_month_total_scans,
        "today_scans": today_scans,
        "yesterday_scans": yesterday_scans,
        "verified_scans": verified_scans,
        "prev_month_verified_scans": prev_month_verified_scans,
        "total_users": total_users,
        "active_users": active_users,
        "prev_month_active_users": prev_month_active_users,
        "total_farms": total_farms,
        "recent_scans": recent_scans_data,
    }


@router.get("/admin/scans/by-pest")
def get_admin_scans_by_pest(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin),
    days: int = 365,
):
    """Get system-wide scan distribution by pest type (admin only)"""
    
    since = datetime.utcnow() - timedelta(days=days)
    
    scans_by_pest = db.query(
        models.PestType.name,
        func.count(models.Scan.id).label("count")
    ).join(models.Scan, models.Scan.pest_type_id == models.PestType.id)\
    .filter(models.Scan.created_at >= since)\
    .group_by(models.PestType.name)\
    .order_by(func.count(models.Scan.id).desc())\
    .limit(5).all()
    
    return [
        {"pest": pest, "count": count}
        for pest, count in scans_by_pest
    ]


@router.get("/admin/scans/by-farm")
def get_admin_scans_by_farm(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin),
    days: int = 365,
):
    """Get system-wide scan distribution by farm (admin only)"""
    
    since = datetime.utcnow() - timedelta(days=days)
    
    # Get scans with farm_id set
    scans_by_farm = db.query(
        models.Farm.name,
        func.count(models.Scan.id).label("count")
    ).join(models.Scan, models.Scan.farm_id == models.Farm.id)\
    .filter(models.Scan.created_at >= since)\
    .group_by(models.Farm.name)\
    .order_by(func.count(models.Scan.id).desc())\
    .limit(5).all()
    
    # If no farm data, return scans by user instead
    if not scans_by_farm:
        scans_by_user = db.query(
            models.User.username,
            func.count(models.Scan.id).label("count")
        ).join(models.Scan, models.Scan.user_id == models.User.id)\
        .filter(models.Scan.created_at >= since)\
        .group_by(models.User.username)\
        .order_by(func.count(models.Scan.id).desc())\
        .limit(5).all()
        
        return [
            {"farm": f"User: {username}", "count": count}
            for username, count in scans_by_user
        ]
    
    return [
        {"farm": farm, "count": count}
        for farm, count in scans_by_farm
    ]


@router.get("/admin/monthly-scans")
def get_admin_monthly_scans(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin),
    months: int = 6,
):
    """Get monthly scan counts for the last N months (admin only)"""
    
    now = datetime.utcnow()
    result = []
    
    for i in range(months - 1, -1, -1):
        # Calculate month boundaries
        month_date = now - timedelta(days=i * 30)
        first_of_month = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if i == 0:
            last_of_month = now
        else:
            next_month = (first_of_month + timedelta(days=32)).replace(day=1)
            last_of_month = next_month - timedelta(seconds=1)
        
        count = db.query(func.count(models.Scan.id))\
            .filter(
                and_(
                    models.Scan.created_at >= first_of_month,
                    models.Scan.created_at <= last_of_month
                )
            ).scalar() or 0
        
        result.append({
            "month": first_of_month.strftime("%b"),
            "year": first_of_month.year,
            "count": count
        })
    
    return result


@router.get("/admin/daily-scans")
def get_admin_daily_scans(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin),
    days: int = 7,
):
    """Get daily scan counts for the last N days (admin only)"""
    
    now = datetime.utcnow()
    result = []
    
    for i in range(days - 1, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1) - timedelta(seconds=1)
        
        count = db.query(func.count(models.Scan.id))\
            .filter(
                and_(
                    models.Scan.created_at >= day_start,
                    models.Scan.created_at <= day_end
                )
            ).scalar() or 0
        
        result.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "count": count
        })
    
    return result