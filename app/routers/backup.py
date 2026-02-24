"""
Backup Router for CocoGuard
Provides endpoints for backup management
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import logging

from ..database import get_db
from ..deps import get_current_user, get_current_admin
from ..models import User, UserSettings
from ..services.backup_service import get_backup_service

router = APIRouter(prefix="/backup", tags=["backup"])
logger = logging.getLogger(__name__)


# Request/Response schemas
class CreateBackupRequest(BaseModel):
    include_database: bool = True
    include_uploads: bool = True
    description: str = ""


class BackupInfo(BaseModel):
    filename: str
    created_at: str
    type: str
    description: str
    size_bytes: int
    size_readable: str
    includes_database: bool
    includes_uploads: bool
    files_count: int


class BackupListResponse(BaseModel):
    backups: List[BackupInfo]
    total_count: int


class BackupStatsResponse(BaseModel):
    total_backups: int
    manual_backups: int
    automatic_backups: int
    total_size_bytes: int
    total_size_readable: str
    last_auto_backup: Optional[str]
    retention_days: int
    backup_directory: str


class RestoreBackupRequest(BaseModel):
    filename: str
    restore_database: bool = True
    restore_uploads: bool = True


# Helper function to trigger auto-backup based on user settings
async def trigger_auto_backup_if_enabled(user_id: int, db: Session):
    """Check if user has auto_backup enabled and trigger backup"""
    try:
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        if settings and settings.auto_backup:
            service = get_backup_service()
            await service.create_backup(
                include_database=True,
                include_uploads=True,
                backup_type="automatic",
                description=f"Auto-backup triggered by user {user_id}"
            )
            logger.info(f"Auto-backup triggered for user {user_id}")
    except Exception as e:
        logger.error(f"Auto-backup failed: {e}")


@router.post("/create", response_model=BackupInfo)
async def create_backup(
    request: CreateBackupRequest,
    current_admin: User = Depends(get_current_admin)
):
    """
    Create a manual backup (Admin only)
    
    Creates a ZIP file containing the database and/or uploaded files.
    """
    service = get_backup_service()
    result = await service.create_backup(
        include_database=request.include_database,
        include_uploads=request.include_uploads,
        backup_type="manual",
        description=request.description
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create backup")
    
    return BackupInfo(**result)


@router.get("/list", response_model=BackupListResponse)
async def list_backups(
    current_admin: User = Depends(get_current_admin)
):
    """
    List all available backups (Admin only)
    """
    service = get_backup_service()
    backups = service.list_backups()
    
    return BackupListResponse(
        backups=[BackupInfo(**b) for b in backups],
        total_count=len(backups)
    )


@router.get("/stats", response_model=BackupStatsResponse)
async def get_backup_stats(
    current_admin: User = Depends(get_current_admin)
):
    """
    Get backup statistics (Admin only)
    """
    service = get_backup_service()
    stats = service.get_backup_stats()
    
    return BackupStatsResponse(**stats)


@router.get("/download/{filename}")
async def download_backup(
    filename: str,
    current_admin: User = Depends(get_current_admin)
):
    """
    Download a backup file (Admin only)
    
    Returns the backup ZIP file for download.
    """
    service = get_backup_service()
    backup_path = service.get_backup_path(filename)
    
    if not backup_path:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    return FileResponse(
        path=str(backup_path),
        filename=filename,
        media_type="application/zip"
    )


@router.delete("/{filename}")
async def delete_backup(
    filename: str,
    current_admin: User = Depends(get_current_admin)
):
    """
    Delete a backup file (Admin only)
    """
    service = get_backup_service()
    
    if not service.delete_backup(filename):
        raise HTTPException(status_code=404, detail="Backup not found or could not be deleted")
    
    return {"message": "Backup deleted successfully", "filename": filename}


@router.post("/restore")
async def restore_backup(
    request: RestoreBackupRequest,
    current_admin: User = Depends(get_current_admin)
):
    """
    Restore from a backup file (Admin only)
    
    WARNING: This will overwrite the current database and/or uploads.
    A pre-restore backup is created automatically.
    """
    service = get_backup_service()
    
    success = await service.restore_backup(
        filename=request.filename,
        restore_database=request.restore_database,
        restore_uploads=request.restore_uploads
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to restore backup")
    
    return {
        "message": "Backup restored successfully",
        "filename": request.filename,
        "restored_database": request.restore_database,
        "restored_uploads": request.restore_uploads
    }


@router.post("/cleanup")
async def cleanup_old_backups(
    retention_days: int = 30,
    current_admin: User = Depends(get_current_admin)
):
    """
    Remove backups older than specified retention days (Admin only)
    
    Default retention is 30 days.
    """
    if retention_days < 1:
        raise HTTPException(status_code=400, detail="Retention days must be at least 1")
    
    service = get_backup_service()
    deleted_count = service.cleanup_old_backups(retention_days)
    
    return {
        "message": f"Cleanup completed",
        "deleted_count": deleted_count,
        "retention_days": retention_days
    }


@router.post("/auto")
async def trigger_auto_backup(
    background_tasks: BackgroundTasks,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Trigger an automatic backup (Admin only)
    
    This is typically called by a scheduled task or manually.
    """
    service = get_backup_service()
    result = await service.create_backup(
        include_database=True,
        include_uploads=True,
        backup_type="automatic",
        description="Scheduled automatic backup"
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create automatic backup")
    
    # Also cleanup old backups in background
    background_tasks.add_task(service.cleanup_old_backups, 30)
    
    return {
        "message": "Automatic backup created successfully",
        "backup": BackupInfo(**result)
    }
