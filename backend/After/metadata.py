from typing import Dict, Any
from datetime import datetime

from PIL import Image
from pillow_heif import register_heif_opener

from logger_config import logger

# Register HEIC support globally
register_heif_opener()

class MetadataExtractor:
    def get_metadata(self, file_path: str) -> Dict[str, Any]:
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