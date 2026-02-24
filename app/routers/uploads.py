from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
import os
import shutil
from pathlib import Path
import mimetypes

from .. import models, schemas
from ..deps import get_db, get_current_user, get_current_admin
from ..config import settings
from ..services.exif_service import extract_gps_from_bytes, extract_full_metadata

router = APIRouter(prefix="/uploads", tags=["uploads"])


# Always use the correct uploads directory in cocoguard-backend/uploads/files (outside of app folder)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Go up two levels: app/routers -> app -> cocoguard-backend, then into uploads/files
UPLOAD_DIR = os.path.abspath(os.path.join(BASE_DIR, '../../uploads/files'))
os.makedirs(UPLOAD_DIR, exist_ok=True)
print(f"[DEBUG] Upload directory set to: {UPLOAD_DIR}")


@router.post("/scan-image")
async def upload_scan_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Upload a scan image for pest detection - automatically extracts GPS from photo EXIF data"""
    try:
        # Validate file size
        contents = await file.read()
        if len(contents) > settings.max_upload_size:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum allowed size of {settings.max_upload_size / 1024 / 1024}MB"
            )
        # Validate file type
        allowed_types = {"image/jpeg", "image/png", "image/webp"}
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail="Only JPEG, PNG, and WebP images are allowed"
            )
        
        # Extract GPS and metadata from photo EXIF data
        photo_metadata = extract_full_metadata(contents)
        latitude = photo_metadata.get("latitude")
        longitude = photo_metadata.get("longitude")
        has_gps = photo_metadata.get("has_gps", False)
        
        if has_gps:
            print(f"[EXIF] 📍 Extracted GPS from uploaded photo: lat={latitude:.6f}, lon={longitude:.6f}")
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{current_user.id}_{timestamp}_{file.filename}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        # Save file
        with open(filepath, "wb") as f:
            f.write(contents)
        # Return file path relative to server with GPS data
        return {
            "filename": filename,
            "url": f"/uploads/files/{filename}",
            "size": len(contents),
            "content_type": file.content_type,
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "has_gps": has_gps,
                "source": "exif" if has_gps else None
            },
            "photo_metadata": {
                "camera_make": photo_metadata.get("camera_make"),
                "camera_model": photo_metadata.get("camera_model"),
                "photo_timestamp": photo_metadata.get("timestamp").isoformat() if photo_metadata.get("timestamp") else None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


@router.get("/files/{filename}")
async def get_uploaded_file(filename: str):
    """Retrieve an uploaded file with proper CORS headers"""
    # Security: sanitize filename to prevent path traversal
    safe_filename = os.path.basename(filename)
    if safe_filename != filename or '..' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    filepath = os.path.abspath(os.path.join(UPLOAD_DIR, safe_filename))
    
    # Ensure resolved path is still within UPLOAD_DIR
    if not filepath.startswith(os.path.abspath(UPLOAD_DIR)):
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine the media type
    media_type, _ = mimetypes.guess_type(filepath)
    if media_type is None:
        media_type = "application/octet-stream"
    
    # Return proper FileResponse with CORS headers
    return FileResponse(
        path=filepath,
        media_type=media_type,
        filename=safe_filename,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Cache-Control": "public, max-age=3600",
        }
    )


# Note: The first /knowledge-image endpoint has been removed (duplicate)
# The admin-only version below handles knowledge base image uploads


@router.delete("/files/{filename}")
async def delete_file(
    filename: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete an uploaded file"""
    # Security: sanitize filename to prevent path traversal
    safe_filename = os.path.basename(filename)
    if safe_filename != filename or '..' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    filepath = os.path.abspath(os.path.join(UPLOAD_DIR, safe_filename))
    
    # Ensure resolved path is still within UPLOAD_DIR
    if not filepath.startswith(os.path.abspath(UPLOAD_DIR)):
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    # Validate ownership: filename must start with "<user_id>_" (exact prefix with underscore)
    expected_prefix = f"{current_user.id}_"
    if not safe_filename.startswith(expected_prefix):
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own files"
        )
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        os.remove(filepath)
        return {"message": "File deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")


@router.post("/knowledge-image")
async def upload_knowledge_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin),
):
    """Upload an image for knowledge base article (admin only)"""
    try:
        # Validate file size
        contents = await file.read()
        if len(contents) > settings.max_upload_size:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum allowed size of {settings.max_upload_size / 1024 / 1024}MB"
            )
        # Validate file type
        allowed_types = {"image/jpeg", "image/png", "image/jpg", "image/webp"}
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail="Only JPEG, PNG, and WebP images are allowed"
            )
        # Generate unique filename for knowledge base using original filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"knowledge_{timestamp}_{file.filename}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        # Save file
        with open(filepath, "wb") as f:
            f.write(contents)
        # Return full URL path
        return {
            "filename": filename,
            "url": f"/uploads/files/{filename}",
            "size": len(contents),
            "content_type": file.content_type
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")
