import os
from geopy.distance import geodesic
from typing import List, Tuple
import logging
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

class SummaryService:
    def __init__(self):
        self.mapbox_token = os.getenv("MAPBOX_ACCESS_TOKEN")
        
        # Configuration
        self.USE_INTERACTIVE_MAP = os.getenv("USE_INTERACTIVE_MAP", "true").lower() == "true"
        self.MAPBOX_MONTHLY_LIMIT = int(os.getenv("MAPBOX_MONTHLY_LIMIT", "45000"))
        self.mapbox_usage_file = os.path.join(
            os.getenv("DATA_DIR", "/tmp"),
            "mapbox_usage.txt"
        )

    def generate_summary(self, album_data: dict, manual_locations: List[dict] = None):
        """
        Process Trip Summary based on actual JSON structure:
        Albums -> Photos (with GPS).
        Algorithm: Calculate centroid of photos to find album center.
        """
        
        if manual_locations is None:
            manual_locations = []
        
        # 1. Get albums list
        albums = album_data.get("albums", [])
        if not albums:
            return self._empty_result()

        # 2. Map manual location data (Key = album_id)
        manual_map = {}

        for m in manual_locations:
            album_id = None

            if isinstance(m, dict):
                album_id = m.get("album_id")
            else:
                album_id = getattr(m, "album_id", None)

            if not album_id:
                continue

            manual_map[album_id] = m


        valid_points = []   # Points to plot on map
        timeline_names = [] # Location names
        album_dates = []    # Dates for sorting
        location_data = []  # Album data for frontend (cover, sample photos)
        total_photos = 0
        
        # Date tracking
        start_date = ""
        end_date = ""

        # 3. ITERATE THROUGH EACH ALBUM
        for album in albums:
            album_id = album.get("album_id") or album.get("id")
            album_title = album.get("title", "Unknown")
            display_title = album_title
            method = album.get("method", "")

            # Note: Removed filter for "Review Needed" albums - let users include any album they select

            photos = album.get("photos", [])
            total_photos += len(photos)
            if not photos:
                logger.warning(f"Album {album_title} has no photos, skipped")
                continue

            # ---------- DATE ----------
            album_date = None
            ts = photos[0].get("timestamp")
            if ts:
                try:
                    album_date = datetime.fromisoformat(ts.replace("Z", "+00:00")) if isinstance(ts, str) else ts
                except Exception:
                    album_date = None

            final_lat = None
            final_lon = None

            # ---------- 1️⃣ MANUAL LOCATION (MATCH BẰNG album_id) ----------
            manual = manual_map.get(album_id)
            if manual:
                try:
                    if isinstance(manual, dict):
                        lat = manual.get("lat")
                        lon = manual.get("lon")
                        name = manual.get("name")
                    else:
                        lat = manual.lat
                        lon = manual.lon
                        name = manual.name

                    lat = float(lat)
                    lon = float(lon)

                    if self._is_valid_coordinate(lat, lon):
                        final_lat = lat
                        final_lon = lon
                        display_title = name or album_title
                except (TypeError, ValueError):
                    pass

            # ---------- 2️⃣ FALLBACK GPS ----------
            if final_lat is None:
                lat_sum = 0.0
                lon_sum = 0.0
                count = 0

                for p in photos:
                    try:
                        lat = p.get("lat") or p.get("latitude")
                        lon = p.get("lon") or p.get("longitude")
                        lat = float(lat)
                        lon = float(lon)

                        if self._is_valid_coordinate(lat, lon):
                            lat_sum += lat
                            lon_sum += lon
                            count += 1
                    except (TypeError, ValueError):
                        continue

                if count > 0:
                    final_lat = lat_sum / count
                    final_lon = lon_sum / count

            # ---------- SAVE ----------
            if final_lat is not None and final_lon is not None:
                valid_points.append((final_lat, final_lon))
                timeline_names.append(display_title)
                album_dates.append(album_date)
                
                logger.info(f"✅ Added album '{display_title}' with GPS: ({final_lat}, {final_lon})")
                
                # Collect location data for frontend
                cover_url = None
                if photos and len(photos) > 0:
                    cover_url = photos[0].get("image_url")
                
                location_data.append({
                    "title": display_title,
                    "cover_url": cover_url,
                    "photo_count": len(photos)
                })
            else:
                logger.warning(f"⚠️ Album '{album_title}' skipped - no valid GPS coordinates")

        # Log final array sizes
        logger.info(f"📊 Final arrays: points={len(valid_points)}, timeline={len(timeline_names)}, locations={len(location_data)}")

        # ✅ FIX: SORT BY DATE (OLDEST TO NEWEST)
        if album_dates and any(d is not None for d in album_dates):
            # Create tuples of (date, point, name, loc_data) and sort by date
            combined = list(zip(album_dates, valid_points, timeline_names, location_data))
            # Filter out None dates and sort
            combined_with_dates = [(d, p, n, l) for d, p, n, l in combined if d is not None]
            combined_without_dates = [(d, p, n, l) for d, p, n, l in combined if d is None]
            
            # Sort by date (oldest first)
            combined_with_dates.sort(key=lambda x: x[0])
            
            # Combine back (dated items first in chronological order, then undated)
            combined = combined_with_dates + combined_without_dates
            
            # Unpack back to separate lists
            album_dates, valid_points, timeline_names, location_data = zip(*combined) if combined else ([], [], [], [])
            valid_points = list(valid_points)
            timeline_names = list(timeline_names)
            album_dates = list(album_dates)
            location_data = list(location_data)
            
            logger.info(f"✅ Sorted {len(combined)} locations by date (oldest to newest)")

        # Get start and end dates from sorted data
        if album_dates and len(album_dates) > 0:
            first_date = album_dates[0]
            last_date = album_dates[-1]
            
            if first_date:
                start_date = first_date.strftime('%Y-%m-%d')
            if last_date:
                end_date = last_date.strftime('%Y-%m-%d')

        # 4. Calculate total distance
        total_distance = 0.0
        if len(valid_points) > 1:
            for i in range(len(valid_points) - 1):
                try:
                    dist = geodesic(valid_points[i], valid_points[i+1]).km
                    total_distance += dist
                except Exception as e:
                    logger.warning(f"Error calculating distance: {e}")
                    continue

        # 5. Prepare response data
        # 🛠️ FIXED: Replaced "HÃ nh trÃ¬nh" with "Hành trình" and "Ä‘iá»ƒm Ä‘áº¿n" with "điểm đến"
        response = {
            "trip_title": f"Hành trình {len(valid_points)} điểm đến",
            "total_distance_km": round(total_distance, 2),
            "total_locations": len(valid_points),
            "total_photos": total_photos,
            "start_date": start_date,
            "end_date": end_date,
            "timeline": timeline_names,
            "points": [[lat, lon] for lat, lon in valid_points],
            "locations": location_data  # Album data for markers/popups
        }

        # 6. Add map data based on configuration
        if self.USE_INTERACTIVE_MAP:
            # For Mapbox GL JS (frontend renders the interactive map)
            response["map_data"] = {
                "type": "interactive",
                "provider": "mapbox",
                "mapbox_token": self.mapbox_token
            }
            response["map_image_url"] = None
            # Track usage
            self._increment_mapbox_usage()
        else:
            # For Static Images (backend generates static image URL)
            if self._check_mapbox_usage_limit():
                map_url = self._build_mapbox_static_url(valid_points)
                self._increment_mapbox_usage()
            else:
                logger.warning("Mapbox monthly limit reached")
                map_url = ""
            
            response["map_data"] = {
                "type": "static",
                "url": map_url
            }
            response["map_image_url"] = map_url

        return response

    def _is_valid_coordinate(self, lat: float, lon: float) -> bool:
        """Check if coordinates are valid"""
        try:
            return (isinstance(lat, (int, float)) and 
                    isinstance(lon, (int, float)) and
                    -90 <= lat <= 90 and 
                    -180 <= lon <= 180 and
                    lat != 0.0 and lon != 0.0)
        except:
            return False

    def _build_mapbox_static_url(self, points: List[Tuple[float, float]]) -> str:
        """
        Create Mapbox Static Images API URL
        Docs: https://docs.mapbox.com/api/maps/static-images/
        """
        try:
            if not self.mapbox_token or not points:
                return ""

            # Sample points if too many (Mapbox has URL length limit)
            display_points = points
            if len(points) > 15: # Reduced slightly to allow space for more marker definitions
                step = len(points) // 15 + 1
                display_points = points[::step]
                if points[-1] not in display_points:
                    display_points.append(points[-1])

            # Build path (line connecting points)
            path_coords = "|".join([f"{lon},{lat}" for lat, lon in display_points])
            path = f"path-5+007bff-0.6({path_coords})"

            # Build markers for ALL points
            overlays = [path]
            
            for i, point in enumerate(display_points):
                lat, lon = point
                label = str(i + 1)
                
                # Color logic: Start=Green, End=Red, Middle=Blue
                if i == 0:
                    color = "10b981" # Green
                elif i == len(display_points) - 1:
                    color = "ef4444" # Red
                else:
                    color = "3b82f6" # Blue
                
                # Add pin with number label
                # Format: pin-s-{label}+{color}({lon},{lat})
                overlays.append(f"pin-s-{label}+{color}({lon},{lat})")

            overlay = ",".join(overlays)

            # Calculate center
            lats = [p[0] for p in display_points]
            lons = [p[1] for p in display_points]
            center_lat = sum(lats) / len(lats)
            center_lon = sum(lons) / len(lons)

            # Calculate zoom level based on bounding box
            lat_range = max(lats) - min(lats)
            lon_range = max(lons) - min(lons)
            max_range = max(lat_range, lon_range)

            if max_range > 10: zoom = 4
            elif max_range > 5: zoom = 5
            elif max_range > 2: zoom = 6
            elif max_range > 1: zoom = 7
            elif max_range > 0.5: zoom = 8
            elif max_range > 0.2: zoom = 9
            elif max_range > 0.1: zoom = 10
            else: zoom = 11

            # Build final URL
            url = f"https://api.mapbox.com/styles/v1/mapbox/streets-v12/static/{overlay}/{center_lon},{center_lat},{zoom}/800x600@2x"
            url += f"?access_token={self.mapbox_token}"

            logger.info(f"Generated Mapbox static map URL with {len(display_points)} markers")
            return url

        except Exception as e:
            logger.error(f"Error building Mapbox static URL: {e}")
            return ""

    def _check_mapbox_usage_limit(self) -> bool:
        """Check if Mapbox usage limit exceeded"""
        try:
            current_month = datetime.now().strftime("%Y-%m")
            usage_data = self._read_mapbox_usage()
            
            month_key = usage_data.get("month", "")
            count = usage_data.get("count", 0)
            
            # Reset counter if new month
            if month_key != current_month:
                return True
            
            return count < self.MAPBOX_MONTHLY_LIMIT
            
        except Exception as e:
            logger.error(f"Error checking Mapbox usage: {e}")
            return True  # Allow if error

    def _increment_mapbox_usage(self):
        """Increment Mapbox usage counter"""
        try:
            current_month = datetime.now().strftime("%Y-%m")
            usage_data = self._read_mapbox_usage()
            
            month_key = usage_data.get("month", "")
            count = usage_data.get("count", 0)
            
            # Reset if new month
            if month_key != current_month:
                count = 0
                month_key = current_month
            
            count += 1
            self._write_mapbox_usage({"month": month_key, "count": count})
            
            logger.info(f"Mapbox usage: {count}/{self.MAPBOX_MONTHLY_LIMIT} this month")
            
        except Exception as e:
            logger.error(f"Error incrementing Mapbox usage: {e}")

    def _read_mapbox_usage(self) -> dict:
        """Read usage data from file"""
        try:
            if os.path.exists(self.mapbox_usage_file):
                with open(self.mapbox_usage_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error reading usage file: {e}")
        
        return {"month": "", "count": 0}

    def _write_mapbox_usage(self, data: dict):
        """Write usage data to file"""
        try:
            with open(self.mapbox_usage_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Error writing usage file: {e}")

    def _empty_result(self):
        """Return empty result structure"""
        # 🛠️ FIXED: Replaced "ChÆ°a cÃ³ dá»¯ liá»‡u" with "Chưa có dữ liệu"
        return {
            "trip_title": "Chưa có dữ liệu",
            "total_distance_km": 0,
            "total_locations": 0,
            "total_photos": 0,
            "start_date": "",
            "end_date": "",
            "timeline": [],
            "points": [],
            "locations": [],  # Empty locations array
            "map_data": {
                "type": "none",
                "url": ""
            }
        }