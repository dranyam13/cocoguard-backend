"""
Pest Detection API Router
Endpoints for pest prediction using the TFLite model
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import os
import uuid
from datetime import datetime

from .. import models, schemas
from ..deps import get_db, get_current_user, get_optional_current_user
from ..config import settings
from ..services.prediction_service import get_prediction_service
from ..services.exif_service import extract_gps_from_bytes, extract_full_metadata
from .notifications import create_pest_alert_for_all_users, check_and_create_outbreak_alert

router = APIRouter(prefix="/predict", tags=["prediction"])

# Dangerous pests that trigger alerts to all users
DANGEROUS_PESTS = ['APW Adult', 'APW Larvae']  # Asiatic Palm Weevil variants

# All valid coconut pests that can trigger outbreak alerts when threshold is reached
OUTBREAK_ALERT_PESTS = ['Brontispa Adult', 'Brontispa Pupa', 'Rhinoceros Beetle', 'Slug Caterpillar', 'White Grub']


@router.get("/model-info")
def get_model_info():
    """Get information about the loaded pest detection model"""
    service = get_prediction_service()
    return service.get_model_info()


@router.get("/labels")
def get_labels():
    """Get list of pest types the model can detect"""
    service = get_prediction_service()
    return {
        "labels": service.labels,
        "count": len(service.labels)
    }


@router.post("")
async def predict_pest(
    file: UploadFile = File(..., description="Image file to analyze for pest detection"),
    confidence_threshold: float = Query(0.25, ge=0.0, le=1.0, description="25% initial confidence threshold for YOLO detection. Backend applies stricter post-filters to reject non-pest objects."),
    save_image: bool = Query(True, description="Save uploaded image to server"),
    tree_code: Optional[str] = Form(None, description="Tree code/identifier"),
    location_text: Optional[str] = Form(None, description="Location description"),
    latitude: Optional[float] = Form(None, description="GPS latitude coordinate"),
    longitude: Optional[float] = Form(None, description="GPS longitude coordinate"),
    farm_id: Optional[int] = Form(None, description="Farm ID"),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """
    Analyze an image for pest detection
    
    - **file**: Image file (JPEG, PNG, etc.)
    - **confidence_threshold**: Minimum confidence to report (default 0.3 = 30%)
    - **save_image**: Whether to save the image on the server
    - **tree_code**: Optional tree identifier
    - **location_text**: Optional location description
    - **latitude**: Optional GPS latitude coordinate
    - **longitude**: Optional GPS longitude coordinate
    - **farm_id**: Optional farm ID to associate with scan
    
    Returns detected pests with confidence scores
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
        )
    
    # Read image bytes
    image_bytes = await file.read()
    
    # Extract GPS coordinates from photo EXIF data if not provided
    # This automatically gets location from where the photo was taken
    exif_latitude, exif_longitude = None, None
    photo_metadata = None
    
    if latitude is None or longitude is None:
        exif_latitude, exif_longitude = extract_gps_from_bytes(image_bytes)
        if exif_latitude is not None and exif_longitude is not None:
            print(f"[EXIF] 📍 Extracted GPS from photo: lat={exif_latitude:.6f}, lon={exif_longitude:.6f}")
            # Use EXIF coordinates if not explicitly provided
            if latitude is None:
                latitude = exif_latitude
            if longitude is None:
                longitude = exif_longitude
    
    # Get full metadata for logging/debugging
    photo_metadata = extract_full_metadata(image_bytes)
    if photo_metadata.get("has_gps"):
        print(f"[EXIF] 📸 Photo metadata - Camera: {photo_metadata.get('camera_make')} {photo_metadata.get('camera_model')}, "
              f"Timestamp: {photo_metadata.get('timestamp')}")
    
    # Get prediction service and run inference
    service = get_prediction_service()
    result = service.predict_from_bytes(image_bytes, confidence_threshold)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Prediction failed"))
    
    # Save image if requested
    image_url = None
    if save_image:
        # Create unique filename
        ext = os.path.splitext(file.filename)[1] or ".jpg"
        filename = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
        
        # Ensure uploads directory exists
        upload_dir = os.path.join(settings.upload_dir, "scans")
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_dir, filename)
        with open(file_path, "wb") as f:
            f.write(image_bytes)
        
        image_url = f"/uploads/scans/{filename}"
    
    # Get best prediction for scan record
    best_prediction = result["predictions"][0] if result["predictions"] else None
    pest_type_id = None
    confidence = None
    detected_pest_name = None
    
    if best_prediction:
        detected_pest_name = best_prediction["pest_type"]
        confidence = best_prediction["confidence"]
        
        # Find matching pest type in database (only active pest types)
        pest_type = db.query(models.PestType).filter(
            models.PestType.name.ilike(f"%{detected_pest_name}%"),
            models.PestType.is_active == True
        ).first()
        
        if pest_type:
            pest_type_id = pest_type.id
        else:
            # Check if pest type exists but is disabled
            disabled_pest = db.query(models.PestType).filter(
                models.PestType.name.ilike(f"%{detected_pest_name}%"),
                models.PestType.is_active == False
            ).first()
            if disabled_pest:
                print(f"[INFO] ⚠ Pest type '{detected_pest_name}' is disabled, treating as out-of-scope")
                # Treat disabled pest type as out-of-scope
                best_prediction = None
                detected_pest_name = None
                confidence = None
    
    # ── Determine detection status BEFORE saving scan ──
    # A valid pest detection must meet these criteria:
    # 1. Confidence must be >= 50% (above the 50% sigmoid baseline)
    # 2. Must be one of the 7 known coconut pests
    # 3. If no predictions at all, it's immediately OUT_OF_SCOPE (unfamiliar image)
    # The model is trained ONLY on 7 pest classes, so genuine pests get 55%+
    # while non-pest objects produce scattered noise that gets caught by
    # verification threshold, multi-class filter, and min anchors in prediction_service
    
    MIN_CONFIDENCE_THRESHOLD = 50.0
    
    VALID_COCONUT_PESTS = [
        'APW Adult', 'APW Larvae', 'Brontispa Adult', 'Brontispa Pupa',
        'Rhinoceros Beetle', 'Slug Caterpillar', 'White Grub'
    ]
    
    # Default to OUT_OF_SCOPE - any unfamiliar image goes here immediately
    detection_status = "OUT_OF_SCOPE"
    status_message = "Out-of-Scope Pest Detection"
    scan_notes = "Out-of-Scope Pest Detection - Not a recognized coconut pest"
    
    if best_prediction and confidence is not None:
        print(f"[DEBUG] Top: {detected_pest_name} ({confidence}%)")
        
        is_valid_pest = detected_pest_name in VALID_COCONUT_PESTS
        is_confident_enough = confidence >= MIN_CONFIDENCE_THRESHOLD
        
        if is_valid_pest and is_confident_enough:
            detection_status = "DETECTED"
            status_message = f"Coconut pest detected: {detected_pest_name}"
            scan_notes = f"Detected: {detected_pest_name} ({confidence}%)"
            print(f"[INFO] \u2705 DETECTED: {detected_pest_name} (conf={confidence}%)")
        else:
            # Out-of-scope: low confidence or unrecognized pest
            reasons = []
            if not is_valid_pest:
                reasons.append(f"unknown pest type '{detected_pest_name}'")
            if not is_confident_enough:
                reasons.append(f"confidence {confidence}% < {MIN_CONFIDENCE_THRESHOLD}% minimum")
            scan_notes = f"Out-of-Scope Pest Detection - {', '.join(reasons)}"
            # Don't save pest_type_id for out-of-scope detections
            pest_type_id = None
            print(f"[INFO] \u274c OUT_OF_SCOPE: {', '.join(reasons)}")
    else:
        scan_notes = "Out-of-Scope Pest Detection - No pest detections found (unfamiliar image)"
        print(f"[INFO] \u274c OUT_OF_SCOPE: No pest detections found in image (unfamiliar image)")
    
    # ── Create scan record if user is authenticated ──
    # ALL scans are recorded including Out-of-Scope detections
    scan_id = None
    if current_user:
        scan = models.Scan(
            user_id=current_user.id,
            farm_id=farm_id,
            tree_code=tree_code,
            location_text=location_text,
            latitude=latitude,
            longitude=longitude,
            pest_type_id=pest_type_id,
            confidence=confidence,
            image_url=image_url,
            status=models.ScanStatus.pending,
            notes=scan_notes
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)
        scan_id = scan.id
        
        print(f"[INFO] \U0001F4BE Scan #{scan_id} recorded: {detection_status} - {scan_notes}")
        
        # Check if the detected pest is a DANGEROUS pest (Asiatic Palm Weevil)
        # Only send alerts when the pest was actually DETECTED (not OUT_OF_SCOPE)
        if detection_status == "DETECTED" and detected_pest_name and detected_pest_name in DANGEROUS_PESTS:
            try:
                notifications_sent = create_pest_alert_for_all_users(
                    db=db,
                    pest_type=detected_pest_name,
                    scan_id=scan_id,
                    location_text=location_text,
                    detected_by_user_id=current_user.id
                )
                print(f"[INFO] \u26a0\ufe0f DANGEROUS PEST DETECTED: {detected_pest_name}")
                print(f"[INFO] \U0001F4E2 Sent {notifications_sent} notifications to all users!")
            except Exception as e:
                print(f"[WARNING] Failed to send pest alert notifications: {e}")
        
        # Check for OUTBREAK ALERT
        # Only send alerts when the pest was actually DETECTED (not OUT_OF_SCOPE)
        if detection_status == "DETECTED" and detected_pest_name and detected_pest_name in OUTBREAK_ALERT_PESTS:
            try:
                outbreak_notifications = check_and_create_outbreak_alert(
                    db=db,
                    pest_type=detected_pest_name,
                    scan_id=scan_id,
                    location_text=location_text,
                    detected_by_user_id=current_user.id
                )
                if outbreak_notifications > 0:
                    print(f"[INFO] \U0001F6A8 OUTBREAK ALERT for {detected_pest_name}")
                    print(f"[INFO] \U0001F4E2 Sent {outbreak_notifications} outbreak notifications to all users!")
            except Exception as e:
                print(f"[WARNING] Failed to check/send outbreak alert: {e}")
    
    # Build response
    # For OUT_OF_SCOPE, still provide best_match info so the client knows what was analyzed
    best_match_response = None
    if detection_status == "DETECTED" and best_prediction:
        best_match_response = {
            "pest_type": detected_pest_name,
            "confidence": confidence,
            "pest_type_id": pest_type_id
        }
    else:
        # Out-of-Scope: report as Out-of-Scope Pest Detection
        best_match_response = {
            "pest_type": "Out-of-Scope Pest Detection",
            "confidence": confidence,
            "pest_type_id": None
        }
    
    response = {
        "success": True,
        "status": detection_status,
        "message": status_message,
        "predictions": result["predictions"],
        "total_detections": result["total_detections"],
        "best_match": best_match_response,
        "image_url": image_url,
        "scan_id": scan_id,
        "location": {
            "latitude": latitude,
            "longitude": longitude,
            "source": "exif" if (exif_latitude is not None or exif_longitude is not None) else "manual",
            "has_gps": latitude is not None and longitude is not None
        },
        "photo_metadata": {
            "camera_make": photo_metadata.get("camera_make") if photo_metadata else None,
            "camera_model": photo_metadata.get("camera_model") if photo_metadata else None,
            "photo_timestamp": photo_metadata.get("timestamp").isoformat() if photo_metadata and photo_metadata.get("timestamp") else None
        }
    }
    
    # Add risk level if pest found in database
    if pest_type_id:
        pest_type = db.query(models.PestType).filter(models.PestType.id == pest_type_id).first()
        if pest_type:
            response["best_match"]["risk_level"] = pest_type.risk_level.value
            response["best_match"]["scientific_name"] = pest_type.scientific_name
    
    return response


@router.post("/batch")
async def predict_batch(
    files: list[UploadFile] = File(..., description="Multiple image files to analyze"),
    confidence_threshold: float = Query(0.55, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """
    Analyze multiple images for pest detection
    
    Returns predictions for each image
    """
    results = []
    service = get_prediction_service()
    
    # Detection thresholds (same as main endpoint)
    MIN_CONFIDENCE_THRESHOLD = 75.0
    VALID_COCONUT_PESTS = [
        'APW Adult', 'APW Larvae', 'Brontispa Adult', 'Brontispa Pupa',
        'Rhinoceros Beetle', 'Slug Caterpillar', 'White Grub'
    ]
    
    for file in files:
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
        if file.content_type not in allowed_types:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": f"Invalid file type: {file.content_type}"
            })
            continue
        
        # Read and predict
        image_bytes = await file.read()
        result = service.predict_from_bytes(image_bytes, confidence_threshold)
        
        # Apply detection criteria (same as main endpoint)
        predictions = result.get("predictions", [])
        best_prediction = predictions[0] if predictions else None
        detection_status = "OUT_OF_SCOPE"
        
        if best_prediction:
            confidence = best_prediction.get("confidence", 0)
            pest_type = best_prediction.get("pest_type", "")
            
            is_valid_pest = pest_type in VALID_COCONUT_PESTS
            is_confident_enough = confidence >= MIN_CONFIDENCE_THRESHOLD
            
            if is_valid_pest and is_confident_enough:
                detection_status = "DETECTED"
        
        results.append({
            "filename": file.filename,
            "success": result["success"],
            "status": detection_status,
            "predictions": result.get("predictions", []),
            "total_detections": result.get("total_detections", 0),
            "error": result.get("error")
        })
    
    return {
        "total_files": len(files),
        "results": results
    }


@router.post("/url")
async def predict_from_url(
    image_url: str = Form(..., description="URL of image to analyze"),
    confidence_threshold: float = Query(0.55, ge=0.0, le=1.0),
    current_user: models.User = Depends(get_current_user)
):
    """
    Analyze an image from URL for pest detection (authenticated)
    """
    import httpx
    from urllib.parse import urlparse
    
    # Security: validate URL to prevent SSRF attacks
    try:
        parsed = urlparse(image_url)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL format")
    
    # Only allow http/https schemes
    if parsed.scheme not in ('http', 'https'):
        raise HTTPException(status_code=400, detail="Only http and https URLs are allowed")
    
    # Block internal/private network addresses
    hostname = parsed.hostname or ''
    blocked_hosts = ['localhost', '127.0.0.1', '0.0.0.0', '::1', '169.254.169.254', 'metadata.google.internal']
    if hostname in blocked_hosts:
        raise HTTPException(status_code=400, detail="Internal URLs are not allowed")
    
    # Block private IP ranges
    try:
        import ipaddress
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise HTTPException(status_code=400, detail="Private/internal IP addresses are not allowed")
    except ValueError:
        pass  # hostname is a domain name, not an IP — that's fine
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url, timeout=30.0, follow_redirects=False)
            response.raise_for_status()
            
            # Validate content type
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="URL must point to an image file")
            
            # Limit response size to 10MB
            if len(response.content) > 10 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="Image too large (max 10MB)")
            
            image_bytes = response.content
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch image: {str(e)}")
    
    service = get_prediction_service()
    result = service.predict_from_bytes(image_bytes, confidence_threshold)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Prediction failed"))
    
    return result


@router.get("/health")
def prediction_health_check():
    """Check if the prediction service is healthy and model is loaded"""
    service = get_prediction_service()
    
    return {
        "status": "healthy" if service.model_loaded else "unhealthy",
        "model_loaded": service.model_loaded,
        "num_classes": len(service.labels),
        "labels": service.labels
    }
