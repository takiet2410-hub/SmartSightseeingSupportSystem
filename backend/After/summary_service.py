import os
from dotenv import load_dotenv
from geopy.distance import geodesic
from typing import List, Dict, Any, Tuple
from datetime import datetime
import math

# Load biến môi trường từ file .env
load_dotenv()

class SummaryService:
    def __init__(self):
        self.mapbox_key = os.getenv("MAPBOX_TOKEN")
        if not self.mapbox_key:
            print("⚠️ CẢNH BÁO: Chưa cấu hình MAPBOX_TOKEN trong file .env")

    def generate_summary(self, album_data: Dict[str, Any], manual_locations: List[dict]):
        """
        Input: Cấu trúc JSON final chứa list albums -> photos (có lat/lon).
        Output: Thông tin tóm tắt chuyến đi + URL bản đồ Goong.
        """
        
        # 1. Xử lý đầu vào linh hoạt (nhận cả dict hoặc list)
        if isinstance(album_data, dict):
            albums = album_data.get("albums", [])
        elif isinstance(album_data, list):
            albums = album_data
        else:
            return self._empty_result()

        if not albums:
            return self._empty_result()

        # 2. Map dữ liệu sửa tay (Key = album_title)
        manual_map = {m['album_title']: m for m in manual_locations}

        valid_points = []   # List các tọa độ đại diện (lat, lon)
        timeline_names = [] # Tên các điểm đến
        total_photos = 0
        all_timestamps = [] # Dùng để tìm ngày bắt đầu/kết thúc
        
        # 3. DUYỆT QUA TỪNG ALBUM
        for album in albums:
            title = album.get("title", "Unknown Event")
            method = album.get("method", "")
            photos = album.get("photos", [])

            # Bỏ qua album rác
            if method == "filters_rejected" or "Review Needed" in title:
                continue

            count = len(photos)
            total_photos += count
            if count == 0:
                continue

            # --- TÍNH TOÁN TỌA ĐỘ TRUNG TÂM (CENTROID) ---
            lat_sum = 0.0
            lon_sum = 0.0
            valid_photo_count = 0
            
            for p in photos:
                # Lấy timestamp để tính thời gian chuyến đi
                ts = p.get("timestamp")
                if ts:
                    # Chuyển đổi timestamp sang string chuẩn ISO nếu cần
                    if isinstance(ts, datetime):
                        ts_str = ts.isoformat()
                    else:
                        ts_str = str(ts)
                    all_timestamps.append(ts_str)

                # Lấy GPS
                p_lat = p.get("lat")
                p_lon = p.get("lon")
                
                # Kiểm tra tọa độ hợp lệ
                if p_lat is not None and p_lon is not None:
                    try:
                        f_lat = float(p_lat)
                        f_lon = float(p_lon)
                        if f_lat != 0.0 and f_lon != 0.0:
                            lat_sum += f_lat
                            lon_sum += f_lon
                            valid_photo_count += 1
                    except ValueError:
                        continue
            
            # Tính trung bình cộng để ra điểm đại diện cho Album
            final_lat = None
            final_lon = None

            if valid_photo_count > 0:
                final_lat = lat_sum / valid_photo_count
                final_lon = lon_sum / valid_photo_count

            # --- KIỂM TRA DỮ LIỆU NHẬP TAY (MANUAL OVERRIDE) ---
            if title in manual_map:
                user_input = manual_map[title]
                if user_input.get('lat') and user_input.get('lon'):
                    final_lat = float(user_input.get('lat'))
                    final_lon = float(user_input.get('lon'))
                if user_input.get('name'):
                    title = user_input.get('name')

            # --- LƯU ĐIỂM HỢP LỆ ---
            if final_lat is not None and final_lon is not None:
                valid_points.append((final_lat, final_lon))
                timeline_names.append(title)

        # 4. Tính toán thống kê
        total_distance = 0.0
        if len(valid_points) > 1:
            for i in range(len(valid_points) - 1):
                try:
                    dist = geodesic(valid_points[i], valid_points[i+1]).km
                    total_distance += dist
                except: pass

        # Sắp xếp thời gian để lấy Start/End Date chuẩn xác
        start_date = ""
        end_date = ""
        if all_timestamps:
            all_timestamps.sort()
            start_date = all_timestamps[0].split("T")[0]
            end_date = all_timestamps[-1].split("T")[0]

        # 5. Tạo Link Bản đồ Goong
        map_url = self._build_goong_static_map_url(valid_points)

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

    def _build_goong_static_map_url(self, points: List[Tuple[float, float]]):
        """
        Vẽ marker + path bằng Mapbox Static Images API
        và tự tính zoom đủ để thấy toàn bộ hành trình (auto-fit).
        """
        if not points or not self.mapbox_key:
            return ""


        # --- Tính bounding box ---
        lats = [p[0] for p in points]
        lons = [p[1] for p in points]
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)


        # --- Tính center ---
        center_lat = (min_lat + max_lat) / 2
        center_lon = (min_lon + max_lon) / 2


        # --- Auto-fit zoom cho Mapbox ---
        width_px = 600
        height_px = 400


        # biên độ góc theo độ
        lon_diff = max_lon - min_lon
        lat_diff = max_lat - min_lat


        # tránh chia 0
        lon_diff = max(lon_diff, 0.00001)
        lat_diff = max(lat_diff, 0.00001)


        # Tính zoom theo công thức Mapbox
        # zoom = log2(360 * width_px / lon_span_deg)

        zoom_x = math.log2(360 * (width_px / 256) / lon_diff)
        zoom_y = math.log2(170.1022 * (height_px / 256) / lat_diff) # hằng số cho lat


        zoom = min(zoom_x, zoom_y)
        zoom = max(min(zoom, 16), 3) # giới hạn zoom hợp lệ


        # --- Path (lng,lat) ---
        path_coords = [f"{lon},{lat}" for lat, lon in points]
        polyline = "|".join(path_coords)


        # --- Markers ---
        start = points[0]
        end = points[-1]


        overlay = (
            f"pin-s+00ff00({start[1]},{start[0]})," # start
            f"pin-s+ff0000({end[1]},{end[0]})," # end
            f"path-3+0000ff-0.8({polyline})"
        )


        url = (
            "https://api.mapbox.com/styles/v1/mapbox/streets-v12/static/"
            f"{overlay}/"
            f"{center_lon},{center_lat},{zoom},0,0/"
            f"{width_px}x{height_px}?access_token={self.mapbox_key}"
        )


        return url

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