from typing import Dict, Any, Optional
from datetime import datetime
import hashlib

from PIL import Image
from pillow_heif import register_heif_opener

from logger_config import logger

register_heif_opener()

class MetadataExtractor:
    def __init__(self):
        # 🚀 V2: Cache parsed EXIF data
        self._cache = {}
    
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
        """Internal extraction logic"""
        result = {"timestamp": None, "latitude": None, "longitude": None}
        try:
            img = Image.open(file_path)
            exif = img._getexif()
            if not exif: return result

            # Time (Tag 36867 = DateTimeOriginal)
            date_str = exif.get(36867) 
            if date_str:
                try:
                    result["timestamp"] = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                except ValueError: pass

            # GPS (Tag 34853)
            gps_info = exif.get(34853)
            if gps_info:
                result["latitude"], result["longitude"] = self._parse_gps(gps_info)
            
            return result
        except Exception as e:
            logger.error(f"Metadata fail for {file_path}: {e}")
            return result

    def _parse_gps(self, gps: Dict) -> Any:
        def to_deg(value):
            d, m, s = value
            return float(d) + (float(m)/60.0) + (float(s)/3600.0)

        try:
            lat = to_deg(gps[2])
            lon = to_deg(gps[4])
            if gps[1] == 'S': lat = -lat
            if gps[3] == 'W': lon = -lon
            return lat, lon
        except:
            return None, None