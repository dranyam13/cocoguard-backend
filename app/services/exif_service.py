"""
EXIF Data Extraction Service
Extracts GPS coordinates and other metadata from uploaded photos

Photos taken with smartphone cameras often contain EXIF metadata including:
- GPS coordinates (latitude, longitude)
- Timestamp when photo was taken
- Camera model and settings
- Orientation information
"""

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from io import BytesIO
from typing import Optional, Dict, Any, Tuple
from datetime import datetime


def _get_exif_data(image: Image.Image) -> Dict[str, Any]:
    """Extract all EXIF data from an image"""
    exif_data = {}
    try:
        info = image._getexif()
        if info:
            for tag_id, value in info.items():
                tag = TAGS.get(tag_id, tag_id)
                exif_data[tag] = value
    except (AttributeError, KeyError, IndexError):
        pass
    return exif_data


def _get_gps_info(exif_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract GPS information from EXIF data"""
    gps_info = {}
    if "GPSInfo" not in exif_data:
        return gps_info
    
    for key, value in exif_data["GPSInfo"].items():
        gps_tag = GPSTAGS.get(key, key)
        gps_info[gps_tag] = value
    
    return gps_info


def _convert_to_degrees(value) -> Optional[float]:
    """
    Convert GPS coordinates from EXIF format (degrees, minutes, seconds) to decimal degrees
    
    EXIF stores coordinates as:
    - Degrees: value[0]
    - Minutes: value[1]  
    - Seconds: value[2]
    """
    try:
        # Handle IFDRational objects from Pillow
        d = float(value[0])
        m = float(value[1])
        s = float(value[2])
        
        return d + (m / 60.0) + (s / 3600.0)
    except (TypeError, ValueError, IndexError, ZeroDivisionError):
        return None


def extract_gps_from_bytes(image_bytes: bytes) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract GPS coordinates from image bytes
    
    Args:
        image_bytes: Raw image file bytes
        
    Returns:
        Tuple of (latitude, longitude) or (None, None) if not available
    """
    try:
        image = Image.open(BytesIO(image_bytes))
        exif_data = _get_exif_data(image)
        gps_info = _get_gps_info(exif_data)
        
        if not gps_info:
            return None, None
        
        # Extract latitude
        lat = None
        if "GPSLatitude" in gps_info and "GPSLatitudeRef" in gps_info:
            lat = _convert_to_degrees(gps_info["GPSLatitude"])
            if lat is not None:
                # South latitudes are negative
                if gps_info["GPSLatitudeRef"] == "S":
                    lat = -lat
        
        # Extract longitude
        lon = None
        if "GPSLongitude" in gps_info and "GPSLongitudeRef" in gps_info:
            lon = _convert_to_degrees(gps_info["GPSLongitude"])
            if lon is not None:
                # West longitudes are negative
                if gps_info["GPSLongitudeRef"] == "W":
                    lon = -lon
        
        return lat, lon
        
    except Exception as e:
        print(f"[EXIF] Error extracting GPS data: {e}")
        return None, None


def extract_full_metadata(image_bytes: bytes) -> Dict[str, Any]:
    """
    Extract comprehensive metadata from image including GPS, timestamp, camera info
    
    Args:
        image_bytes: Raw image file bytes
        
    Returns:
        Dictionary with extracted metadata
    """
    result = {
        "latitude": None,
        "longitude": None,
        "timestamp": None,
        "camera_make": None,
        "camera_model": None,
        "has_gps": False,
    }
    
    try:
        image = Image.open(BytesIO(image_bytes))
        exif_data = _get_exif_data(image)
        
        # Extract GPS coordinates
        gps_info = _get_gps_info(exif_data)
        if gps_info:
            lat, lon = None, None
            
            if "GPSLatitude" in gps_info and "GPSLatitudeRef" in gps_info:
                lat = _convert_to_degrees(gps_info["GPSLatitude"])
                if lat is not None and gps_info["GPSLatitudeRef"] == "S":
                    lat = -lat
            
            if "GPSLongitude" in gps_info and "GPSLongitudeRef" in gps_info:
                lon = _convert_to_degrees(gps_info["GPSLongitude"])
                if lon is not None and gps_info["GPSLongitudeRef"] == "W":
                    lon = -lon
            
            if lat is not None and lon is not None:
                result["latitude"] = lat
                result["longitude"] = lon
                result["has_gps"] = True
        
        # Extract timestamp (when photo was taken)
        datetime_original = exif_data.get("DateTimeOriginal")
        if datetime_original:
            try:
                result["timestamp"] = datetime.strptime(datetime_original, "%Y:%m:%d %H:%M:%S")
            except ValueError:
                pass
        
        # Extract camera information
        result["camera_make"] = exif_data.get("Make")
        result["camera_model"] = exif_data.get("Model")
        
    except Exception as e:
        print(f"[EXIF] Error extracting metadata: {e}")
    
    return result


# Convenience function for quick GPS check
def has_gps_data(image_bytes: bytes) -> bool:
    """Check if image contains GPS data"""
    lat, lon = extract_gps_from_bytes(image_bytes)
    return lat is not None and lon is not None
