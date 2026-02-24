"""
Backup Service for CocoGuard
Creates and manages backups of the database and uploaded files
"""
import os
import shutil
import zipfile
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import asyncio

logger = logging.getLogger(__name__)

# Get the backend root directory (parent of app/)
BACKEND_ROOT = Path(__file__).parent.parent.parent
BACKUP_DIR = BACKEND_ROOT / "backups"
DATABASE_PATH = BACKEND_ROOT / "cocoguard.db"
UPLOADS_DIR = BACKEND_ROOT / "uploads"


class BackupService:
    """Service for managing system backups"""
    
    def __init__(self):
        # Ensure backup directory exists
        BACKUP_DIR.mkdir(exist_ok=True)
    
    def _get_backup_filename(self, prefix: str = "backup") -> str:
        """Generate a timestamped backup filename"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.zip"
    
    def _get_backup_metadata_path(self) -> Path:
        """Get path to backup metadata file"""
        return BACKUP_DIR / "backup_metadata.json"
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load backup metadata from JSON file"""
        metadata_path = self._get_backup_metadata_path()
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading backup metadata: {e}")
        return {"backups": [], "last_auto_backup": None, "retention_days": 30}
    
    def _save_metadata(self, metadata: Dict[str, Any]) -> None:
        """Save backup metadata to JSON file"""
        metadata_path = self._get_backup_metadata_path()
        try:
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving backup metadata: {e}")
    
    async def create_backup(self, 
                           include_database: bool = True, 
                           include_uploads: bool = True,
                           backup_type: str = "manual",
                           description: str = "") -> Optional[Dict[str, Any]]:
        """
        Create a backup of the database and/or uploads
        
        Args:
            include_database: Include SQLite database in backup
            include_uploads: Include uploaded files (images) in backup
            backup_type: 'manual' or 'automatic'
            description: Optional description for the backup
            
        Returns:
            Backup info dict or None if failed
        """
        try:
            filename = self._get_backup_filename(backup_type)
            backup_path = BACKUP_DIR / filename
            
            # Calculate sizes before creating zip
            db_size = 0
            uploads_size = 0
            files_count = 0
            
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add database
                if include_database and DATABASE_PATH.exists():
                    # Create a copy of the database first (to avoid locking issues)
                    db_copy_path = BACKUP_DIR / "temp_db.db"
                    shutil.copy2(DATABASE_PATH, db_copy_path)
                    zipf.write(db_copy_path, "cocoguard.db")
                    db_size = db_copy_path.stat().st_size
                    files_count += 1
                    # Clean up temp copy
                    db_copy_path.unlink()
                    logger.info("Database added to backup")
                
                # Add uploads directory
                if include_uploads and UPLOADS_DIR.exists():
                    for root, dirs, files in os.walk(UPLOADS_DIR):
                        for file in files:
                            file_path = Path(root) / file
                            arcname = Path("uploads") / file_path.relative_to(UPLOADS_DIR)
                            zipf.write(file_path, arcname)
                            uploads_size += file_path.stat().st_size
                            files_count += 1
                    logger.info(f"Uploaded files added to backup ({files_count - 1} files)")
            
            # Get final backup size
            backup_size = backup_path.stat().st_size
            
            # Create backup info
            backup_info = {
                "filename": filename,
                "path": str(backup_path),
                "created_at": datetime.now().isoformat(),
                "type": backup_type,
                "description": description,
                "size_bytes": backup_size,
                "size_readable": self._format_size(backup_size),
                "includes_database": include_database,
                "includes_uploads": include_uploads,
                "database_size": db_size,
                "uploads_size": uploads_size,
                "files_count": files_count
            }
            
            # Update metadata
            metadata = self._load_metadata()
            metadata["backups"].append(backup_info)
            if backup_type == "automatic":
                metadata["last_auto_backup"] = datetime.now().isoformat()
            self._save_metadata(metadata)
            
            logger.info(f"Backup created successfully: {filename} ({self._format_size(backup_size)})")
            return backup_info
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups"""
        metadata = self._load_metadata()
        backups = []
        
        for backup_info in metadata.get("backups", []):
            backup_path = Path(backup_info.get("path", ""))
            if backup_path.exists():
                # Update size in case it changed
                backup_info["size_bytes"] = backup_path.stat().st_size
                backup_info["size_readable"] = self._format_size(backup_info["size_bytes"])
                backups.append(backup_info)
        
        # Sort by created_at descending (newest first)
        backups.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return backups
    
    def get_backup(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get info about a specific backup"""
        backups = self.list_backups()
        for backup in backups:
            if backup.get("filename") == filename:
                return backup
        return None
    
    def get_backup_path(self, filename: str) -> Optional[Path]:
        """Get the full path to a backup file"""
        backup_path = BACKUP_DIR / filename
        if backup_path.exists() and backup_path.suffix == '.zip':
            return backup_path
        return None
    
    def delete_backup(self, filename: str) -> bool:
        """Delete a specific backup"""
        try:
            backup_path = BACKUP_DIR / filename
            if backup_path.exists():
                backup_path.unlink()
                
                # Update metadata
                metadata = self._load_metadata()
                metadata["backups"] = [
                    b for b in metadata.get("backups", []) 
                    if b.get("filename") != filename
                ]
                self._save_metadata(metadata)
                
                logger.info(f"Backup deleted: {filename}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete backup {filename}: {e}")
            return False
    
    def cleanup_old_backups(self, retention_days: int = 30) -> int:
        """
        Remove backups older than retention_days
        Returns number of backups deleted
        """
        metadata = self._load_metadata()
        cutoff_date = datetime.now().timestamp() - (retention_days * 24 * 60 * 60)
        deleted_count = 0
        
        for backup_info in list(metadata.get("backups", [])):
            try:
                created_at = datetime.fromisoformat(backup_info.get("created_at", ""))
                if created_at.timestamp() < cutoff_date:
                    if self.delete_backup(backup_info.get("filename", "")):
                        deleted_count += 1
            except Exception as e:
                logger.error(f"Error processing backup for cleanup: {e}")
        
        logger.info(f"Cleanup completed: {deleted_count} old backups removed")
        return deleted_count
    
    async def restore_backup(self, filename: str, restore_database: bool = True, restore_uploads: bool = True) -> bool:
        """
        Restore from a backup file
        
        Args:
            filename: Name of the backup file
            restore_database: Whether to restore the database
            restore_uploads: Whether to restore uploaded files
            
        Returns:
            True if successful, False otherwise
        """
        try:
            backup_path = self.get_backup_path(filename)
            if not backup_path:
                logger.error(f"Backup not found: {filename}")
                return False
            
            # Create temp directory for extraction
            temp_dir = BACKUP_DIR / "temp_restore"
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            temp_dir.mkdir()
            
            # Extract backup
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(temp_dir)
            
            # Restore database
            if restore_database:
                db_backup = temp_dir / "cocoguard.db"
                if db_backup.exists():
                    # Create a backup of current database first
                    if DATABASE_PATH.exists():
                        pre_restore_backup = DATABASE_PATH.with_suffix('.db.pre_restore')
                        shutil.copy2(DATABASE_PATH, pre_restore_backup)
                    
                    shutil.copy2(db_backup, DATABASE_PATH)
                    logger.info("Database restored")
            
            # Restore uploads
            if restore_uploads:
                uploads_backup = temp_dir / "uploads"
                if uploads_backup.exists():
                    # Merge with existing uploads (don't delete existing files)
                    for root, dirs, files in os.walk(uploads_backup):
                        for file in files:
                            src = Path(root) / file
                            rel_path = src.relative_to(uploads_backup)
                            dst = UPLOADS_DIR / rel_path
                            dst.parent.mkdir(parents=True, exist_ok=True)
                            if not dst.exists():  # Don't overwrite existing files
                                shutil.copy2(src, dst)
                    logger.info("Uploads restored")
            
            # Cleanup temp directory
            shutil.rmtree(temp_dir)
            
            logger.info(f"Backup restored successfully: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore backup {filename}: {e}")
            return False
    
    def get_backup_stats(self) -> Dict[str, Any]:
        """Get statistics about backups"""
        backups = self.list_backups()
        metadata = self._load_metadata()
        
        total_size = sum(b.get("size_bytes", 0) for b in backups)
        manual_count = sum(1 for b in backups if b.get("type") == "manual")
        auto_count = sum(1 for b in backups if b.get("type") == "automatic")
        
        return {
            "total_backups": len(backups),
            "manual_backups": manual_count,
            "automatic_backups": auto_count,
            "total_size_bytes": total_size,
            "total_size_readable": self._format_size(total_size),
            "last_auto_backup": metadata.get("last_auto_backup"),
            "retention_days": metadata.get("retention_days", 30),
            "backup_directory": str(BACKUP_DIR)
        }
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes to human readable size"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


# Singleton instance
_backup_service: Optional[BackupService] = None


def get_backup_service() -> BackupService:
    """Get the backup service singleton"""
    global _backup_service
    if _backup_service is None:
        _backup_service = BackupService()
    return _backup_service
