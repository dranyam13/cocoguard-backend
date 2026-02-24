from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import os

from .. import models, schemas
from ..deps import get_db, get_current_user, get_current_admin
from ..config import settings
from ..utils.timezone import to_manila_iso, to_manila_time

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post("", response_model=schemas.ScanItem)
def create_scan(
    scan_in: schemas.ScanCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):

    pest_type_id = scan_in.pest_type_id
    if pest_type_id is None and scan_in.pest_type:
        pest_type = db.query(models.PestType).filter(
            models.PestType.name == scan_in.pest_type
        ).first()
        if pest_type:
            pest_type_id = pest_type.id

    scan = models.Scan(
        user_id=current_user.id,
        farm_id=scan_in.farm_id,
        tree_code=scan_in.tree_code,
        location_text=scan_in.location_text,
        latitude=scan_in.latitude,
        longitude=scan_in.longitude,
        pest_type_id=pest_type_id,
        confidence=scan_in.confidence,
        image_url=scan_in.image_url,
        source=scan_in.source or "image",
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    return schemas.ScanItem(
        id=scan.id,
        tree_code=scan.tree_code,
        date_time=to_manila_time(scan.created_at),
        location_text=scan.location_text,
        pest_type=scan.pest_type.name if scan.pest_type else 'Out-of-Scope Pest Detection',
        risk_level=scan.pest_type.risk_level if scan.pest_type else None,
        confidence=float(scan.confidence) if scan.confidence is not None else None,
        status=scan.status,
        image_url=scan.image_url,
        latitude=float(scan.latitude) if scan.latitude is not None else None,
        longitude=float(scan.longitude) if scan.longitude is not None else None,
        source=scan.source or "image",
    )


@router.get("/my", response_model=schemas.MyScansResponse)
@router.get("/my-scans", response_model=schemas.MyScansResponse)
def my_scans(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    scans = (
        db.query(models.Scan)
        .filter(models.Scan.user_id == current_user.id)
        .order_by(models.Scan.created_at.desc())
        .all()
    )
    farm = db.query(models.Farm).filter(models.Farm.user_id == current_user.id).first()
    items = [
        schemas.ScanItem(
            id=s.id,
            tree_code=s.tree_code,
            date_time=to_manila_time(s.created_at),
            location_text=s.location_text,
            pest_type=s.pest_type.name if s.pest_type else 'Out-of-Scope Pest Detection',
            risk_level=s.pest_type.risk_level if s.pest_type else None,
            confidence=float(s.confidence) if s.confidence is not None else None,
            status=s.status,
            image_url=s.image_url,
            latitude=float(s.latitude) if s.latitude is not None else None,
            longitude=float(s.longitude) if s.longitude is not None else None,
            source=s.source or "image",
        )
        for s in scans
    ]
    return schemas.MyScansResponse(
        total_scans=len(scans),
        total_trees=farm.total_trees if farm else 0,
        records=items,
    )


# Admin: list all scans for Scan History table
@router.get("/admin", dependencies=[Depends(get_current_admin)])
def admin_scans(db: Session = Depends(get_db)):
    scans = (
        db.query(models.Scan)
        .order_by(models.Scan.created_at.desc())
        .all()
    )
    return [
        {
            "id": s.id,
            "user": s.user.username,
            "datetime": to_manila_iso(s.created_at),
            "pest_type": s.pest_type.name if s.pest_type else "Out-of-Scope Pest Detection",
            "confidence": float(s.confidence) if s.confidence is not None else None,
            "status": s.status,
            "image_url": s.image_url,
            "location_text": s.location_text or "Unknown Location",
            "source": s.source or "image",
        }
        for s in scans
    ]


# Admin: update scan status (verify/reject)
from pydantic import BaseModel

class StatusUpdate(BaseModel):
    status: str

@router.put("/{scan_id:int}/status", dependencies=[Depends(get_current_admin)])
def update_scan_status(
    scan_id: int,
    status_update: StatusUpdate,
    db: Session = Depends(get_db)
):
    scan = db.query(models.Scan).filter(models.Scan.id == scan_id).first()
    if not scan:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Scan not found")
    
    new_status = status_update.status or "pending"
    # Validate status
    valid_statuses = ["pending", "verified", "rejected"]
    if new_status.lower() not in valid_statuses:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    scan.status = new_status.lower()
    db.commit()
    db.refresh(scan)
    
    return {
        "id": scan.id,
        "status": scan.status,
        "message": f"Scan #{scan.id} status updated to {scan.status}"
    }


def _delete_scan_image(image_url: str | None):
    """Delete the scan image file from disk if it exists."""
    if not image_url:
        return
    # image_url is like "/uploads/scans/scan_xxx.jpg"
    relative_path = image_url.lstrip("/")
    file_path = os.path.join(os.path.dirname(settings.upload_dir), relative_path)
    # Also try relative to CWD
    if not os.path.exists(file_path):
        file_path = os.path.join(".", relative_path)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"[INFO] 🗑️ Deleted scan image: {file_path}")
        except OSError as e:
            print(f"[WARN] Failed to delete scan image {file_path}: {e}")


# Delete a single scan (user can delete their own scans)
@router.delete("/{scan_id:int}")
def delete_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    scan = db.query(models.Scan).filter(models.Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Users can only delete their own scans; admins can delete any
    if scan.user_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this scan")
    
    # Delete the image file from disk
    _delete_scan_image(scan.image_url)
    
    db.delete(scan)
    db.commit()
    
    return {"message": f"Scan #{scan_id} deleted successfully"}


# Delete all scans for the current user
@router.delete("")
def delete_all_my_scans(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    scans = db.query(models.Scan).filter(models.Scan.user_id == current_user.id).all()
    
    # Delete all image files
    for scan in scans:
        _delete_scan_image(scan.image_url)
    
    count = len(scans)
    for scan in scans:
        db.delete(scan)
    db.commit()
    
    return {"message": f"Deleted {count} scan(s) successfully", "deleted_count": count}
