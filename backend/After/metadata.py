from typing import Dict, Any, Optional
from datetime import datetime

from PIL import Image
from PIL.ExifTags import TAGS
from pillow_heif import register_heif_opener

from logger_config import logger

register_heif_opener()

class MetadataExtractor:
    def __init__(self):
        # 🚀 V2.1: Cache parsed EXIF data to avoid re-parsing
        self._cache = {}
    
    def get_metadata_from_image(self, pil_image: Image.Image) -> Dict[str, Any]:
        """
        🚀 V2.3: Extract metadata from PIL Image object directly
        This preserves metadata from HEIC files before re-encoding
        """
        result = {"timestamp": None, "latitude": None, "longitude": None}
    
        try:
            # Extract EXIF data from PIL Image object
            exif_data = {}
        
            # Method 1: Try getexif() (works for JPEG, PNG, HEIC)
            if hasattr(pil_image, 'getexif') and callable(pil_image.getexif):
                exif_obj = pil_image.getexif()
                if exif_obj:
                    exif_data = dict(exif_obj)
                    
                    # 🔧 FIX 2: Explicitly fetch the GPS sub-dictionary
                    # Tag 34853 is the standard pointer to GPS Info
                    try:
                        gps_data = exif_obj.get_ifd(34853)
                        if gps_data:
                            exif_data[34853] = gps_data
                    except Exception:
                        pass
        
            # Method 2: Try _getexif() for older PIL versions
            elif hasattr(pil_image, '_getexif') and callable(pil_image._getexif):
                exif_data = pil_image._getexif()
        
            if not exif_data:
                return result

            # Extract timestamp (Tag 36867 = DateTimeOriginal)
            date_str = exif_data.get(36867) or exif_data.get(306)  # 306 = DateTime (fallback)
            if date_str:
                try:
                    result["timestamp"] = datetime.strptime(str(date_str), "%Y:%m:%d %H:%M:%S")
                except (ValueError, TypeError):
                    pass

            # Extract GPS (Tag 34853)
            gps_info = exif_data.get(34853)
            if gps_info:
                result["latitude"], result["longitude"] = self._parse_gps(gps_info)
        
            return result
        
        except Exception as e:
            logger.error(f"Metadata extraction from PIL failed: {e}")
            return result

    def get_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from file path (with caching)"""
        
        # Simple cache key based on file path
        cache_key = file_path
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        result = self._extract_metadata(file_path)
        self._cache[cache_key] = result
        return result
    
    def _extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Internal extraction logic - supports JPEG, PNG, HEIC"""
        result = {"timestamp": None, "latitude": None, "longitude": None}
        
        try:
            img = Image.open(file_path)
            
            # 🔧 FIX: Handle both standard images and HEIC
            exif_data = None
            
            # Method 1: Try standard _getexif() for JPEG/PNG
            if hasattr(img, '_getexif') and callable(img._getexif):
                exif_data = img._getexif()
            
            # Method 2: Try getexif() for newer PIL versions
            elif hasattr(img, 'getexif') and callable(img.getexif):
                exif_dict = img.getexif()
                if exif_dict:
                    exif_data = dict(exif_dict)
            
            # Method 3: Try info dict for HEIC (pillow-heif)
            elif hasattr(img, 'info') and 'exif' in img.info:
                # HEIC files store EXIF in info dict
                from PIL import ExifTags
                exif_dict = img.getexif()
                if exif_dict:
                    exif_data = dict(exif_dict)
            
            if not exif_data:
                return result

            # Extract timestamp (Tag 36867 = DateTimeOriginal)
            date_str = exif_data.get(36867) or exif_data.get(306)  # 306 = DateTime (fallback)
            if date_str:
                try:
                    result["timestamp"] = datetime.strptime(str(date_str), "%Y:%m:%d %H:%M:%S")
                except (ValueError, TypeError):
                    pass

            # Extract GPS (Tag 34853)
            gps_info = exif_data.get(34853)
            if gps_info:
                result["latitude"], result["longitude"] = self._parse_gps(gps_info)
            
            return result
            
        except Exception as e:
            logger.error(f"Metadata fail for {file_path}: {e}")
            return result

    def _parse_gps(self, gps: Dict) -> tuple:
    
        def rational_to_float(r):
            try:
                return float(r)
            except Exception:
                # (num, den)
                return r[0] / r[1]

        def dms_to_deg(dms):
            if not dms or len(dms) != 3:
                return None
            d = rational_to_float(dms[0])
            m = rational_to_float(dms[1])
            s = rational_to_float(dms[2])
            return d + m / 60.0 + s / 3600.0

        try:
            lat_dms = gps.get(2)
            lon_dms = gps.get(4)
            lat_ref = gps.get(1, "N")
            lon_ref = gps.get(3, "E")

            lat = dms_to_deg(lat_dms)
            lon = dms_to_deg(lon_dms)

            if lat is None or lon is None:
                return None, None

            if lat_ref == "S":
                lat = -lat
            if lon_ref == "W":
                lon = -lon

            # 🔒 Safety guard (Vietnam bounds)
            if not (8 <= lat <= 12 and 104 <= lon <= 109):
                logger.warning(f"GPS out of VN bounds: {lat}, {lon}")
                return None, None

            return lat, lon

        except Exception as e:
            logger.debug(f"GPS parsing failed: {e}")
            return None, None
