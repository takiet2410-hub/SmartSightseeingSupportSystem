from geopy.distance import geodesic
from typing import List, Dict, Any
from config import GOOGLE_MAPS_API_KEY

class SummaryService:
    def __init__(self):
        self.api_key = GOOGLE_MAPS_API_KEY

    def generate_summary(self, album_data: dict, manual_locations: List[dict]):
        """
        Generate summary from photo GPS coordinates (not album-level GPS)
        """
        
        albums = album_data.get("albums", [])
        if not albums:
            return self._empty_result()

        # Map for manual overrides
        manual_map = {m['album_title']: m for m in manual_locations}

        valid_points = []
        timeline_names = []
        total_photos = 0
        
        start_date = ""
        end_date = ""

        # Process each album
        for album in albums:
            title = album.get("title", "Unknown Event")
            method = album.get("method", "")

            # Skip rejected albums
            if method == "filters_rejected" or "Review Needed" in title:
                continue

            photos = album.get("photos", [])
            total_photos += len(photos)

            # 🆕 CORRECT: Get GPS from photos, not album
            lat = None
            lon = None
            
            # Calculate representative GPS (average of all photos in album)
            valid_photo_coords = []
            for photo in photos:
                photo_lat = photo.get('lat')
                photo_lon = photo.get('lon')
                if photo_lat is not None and photo_lon is not None:
                    if float(photo_lat) != 0.0 and float(photo_lon) != 0.0:
                        valid_photo_coords.append((float(photo_lat), float(photo_lon)))
            
            # Use average GPS as album's representative location
            if valid_photo_coords:
                lat = sum(coord[0] for coord in valid_photo_coords) / len(valid_photo_coords)
                lon = sum(coord[1] for coord in valid_photo_coords) / len(valid_photo_coords)
            
            # Check for manual override
            if title in manual_map:
                user_input = manual_map[title]
                lat = user_input.get('lat')
                lon = user_input.get('lon')
                if user_input.get('name'):
                    title = user_input.get('name')

            # Add valid point
            if lat is not None and lon is not None:
                valid_points.append((float(lat), float(lon)))
                timeline_names.append(title)

            # Get dates from photos
            if photos and not start_date:
                ts = photos[0].get("timestamp")
                if ts:
                    start_date = str(ts).split("T")[0] if "T" in str(ts) else str(ts)[:10]
            if photos:
                ts = photos[-1].get("timestamp")
                if ts:
                    end_date = str(ts).split("T")[0] if "T" in str(ts) else str(ts)[:10]

        # Calculate distance
        total_distance = 0.0
        if len(valid_points) > 1:
            for i in range(len(valid_points) - 1):
                dist = geodesic(valid_points[i], valid_points[i+1]).km
                total_distance += dist

        # Generate map URL
        map_url = self._build_google_static_map_url(valid_points)

        return {
            "trip_title": f"Hành trình {len(valid_points)} điểm đến",
            "total_distance_km": round(total_distance, 2),
            "total_locations": len(valid_points),
            "total_photos": total_photos,
            "start_date": start_date,
            "end_date": end_date,
            "map_image_url": map_url,
            "timeline": timeline_names
        }

    def _build_google_static_map_url(self, points):
        if not points: 
            return ""
            
        base_url = "https://maps.googleapis.com/maps/api/staticmap?"
        
        # Limit to 15 points to keep URL manageable
        display_points = points if len(points) <= 15 else points[::len(points)//15 + 1]
        if points[-1] not in display_points: 
            display_points.append(points[-1])

        # Draw path
        path_str = "path=color:0x007bff|weight:5"
        for lat, lon in display_points:
            path_str += f"|{lat},{lon}"
            
        # Draw markers
        markers_list = []
        for i, (lat, lon) in enumerate(display_points):
            label = str(i + 1) if i < 9 else "Z"
            color = "red" if i == 0 or i == len(display_points)-1 else "blue"
            markers_list.append(f"markers=color:{color}|label:{label}|{lat},{lon}")
            
        return f"{base_url}size=600x400&scale=2&maptype=roadmap&{path_str}&{'&'.join(markers_list)}&key={self.api_key}"

    def _empty_result(self):
        return {
            "trip_title": "Chưa có dữ liệu",
            "total_distance_km": 0,
            "total_locations": 0,
            "total_photos": 0,
            "start_date": "",
            "end_date": "",
            "map_image_url": "",
            "timeline": []
        }