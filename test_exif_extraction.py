"""
Test script for EXIF GPS extraction
This demonstrates how the system extracts GPS coordinates from photo metadata
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.exif_service import (
    extract_gps_from_bytes,
    extract_full_metadata,
    has_gps_data
)


def test_exif_extraction():
    """Test the EXIF extraction functionality"""
    
    print("=" * 60)
    print("EXIF GPS Extraction Test")
    print("=" * 60)
    
    # Create a simple test image with GPS data
    # Note: This creates a minimal JPEG without actual GPS data for testing
    # In production, real photos from smartphones will have GPS embedded
    
    from PIL import Image
    from io import BytesIO
    import piexif
    
    # Create a test image
    img = Image.new('RGB', (100, 100), color='green')
    
    # Create EXIF data with GPS coordinates
    # GPS coordinates for: Philippines (Davao region - coconut farming area)
    # Lat: 7.0736° N, Long: 125.6126° E
    
    def to_deg_min_sec(decimal_value):
        """Convert decimal degrees to (degrees, minutes, seconds) tuple"""
        d = int(decimal_value)
        m = int((decimal_value - d) * 60)
        s = (decimal_value - d - m/60) * 3600
        return ((d, 1), (m, 1), (int(s * 100), 100))
    
    lat = 7.0736
    lon = 125.6126
    
    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef: 'N',
        piexif.GPSIFD.GPSLatitude: to_deg_min_sec(lat),
        piexif.GPSIFD.GPSLongitudeRef: 'E',
        piexif.GPSIFD.GPSLongitude: to_deg_min_sec(lon),
    }
    
    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: "Test Camera",
            piexif.ImageIFD.Model: "Test Model",
        },
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: "2026:02:05 10:30:00",
        },
        "GPS": gps_ifd,
    }
    
    exif_bytes = piexif.dump(exif_dict)
    
    # Save image to bytes with EXIF
    buffer = BytesIO()
    img.save(buffer, format='JPEG', exif=exif_bytes)
    image_bytes = buffer.getvalue()
    
    print(f"\n📸 Created test image with GPS data")
    print(f"   Original coordinates: lat={lat}, lon={lon}")
    
    # Test extraction
    print("\n🔍 Testing extract_gps_from_bytes()...")
    extracted_lat, extracted_lon = extract_gps_from_bytes(image_bytes)
    
    if extracted_lat and extracted_lon:
        print(f"   ✅ SUCCESS! Extracted: lat={extracted_lat:.6f}, lon={extracted_lon:.6f}")
        
        # Check accuracy
        lat_diff = abs(lat - extracted_lat)
        lon_diff = abs(lon - extracted_lon)
        print(f"   📏 Accuracy: lat diff={lat_diff:.8f}, lon diff={lon_diff:.8f}")
    else:
        print("   ❌ FAILED to extract GPS data")
    
    # Test full metadata extraction
    print("\n🔍 Testing extract_full_metadata()...")
    metadata = extract_full_metadata(image_bytes)
    
    print(f"   has_gps: {metadata.get('has_gps')}")
    print(f"   latitude: {metadata.get('latitude')}")
    print(f"   longitude: {metadata.get('longitude')}")
    print(f"   camera_make: {metadata.get('camera_make')}")
    print(f"   camera_model: {metadata.get('camera_model')}")
    print(f"   timestamp: {metadata.get('timestamp')}")
    
    # Test has_gps_data helper
    print("\n🔍 Testing has_gps_data()...")
    print(f"   has GPS: {has_gps_data(image_bytes)}")
    
    # Test with image without GPS
    print("\n📸 Testing with image WITHOUT GPS data...")
    img_no_gps = Image.new('RGB', (100, 100), color='blue')
    buffer_no_gps = BytesIO()
    img_no_gps.save(buffer_no_gps, format='JPEG')
    image_bytes_no_gps = buffer_no_gps.getvalue()
    
    extracted_lat_no_gps, extracted_lon_no_gps = extract_gps_from_bytes(image_bytes_no_gps)
    print(f"   lat: {extracted_lat_no_gps}, lon: {extracted_lon_no_gps}")
    print(f"   has GPS: {has_gps_data(image_bytes_no_gps)}")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        import piexif
    except ImportError:
        print("⚠️  piexif not installed. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "piexif"])
        import piexif
    
    test_exif_extraction()
