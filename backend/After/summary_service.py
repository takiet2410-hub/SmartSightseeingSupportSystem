from geopy.distance import geodesic
from typing import List, Dict, Any, Tuple
from datetime import datetime
from config import GOONG_API_KEY 

class SummaryService:
    def __init__(self):
        self.api_key = GOONG_API_KEY

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
        """Tạo URL bản đồ tĩnh Goong.io"""
        if not points: return ""
        
        base_url = "https://rsapi.goong.io/staticmap/v1?"
        
        # Giới hạn số điểm vẽ để URL không quá dài
        display_points = points
        if len(points) > 15:
            step = len(points) // 15 + 1
            display_points = points[::step]
            if points[-1] not in display_points:
                display_points.append(points[-1])

        # Tạo đường nối (Path) - Màu xanh dương
        path_str = "path=color:007bff|weight:5"
        for lat, lon in display_points:
            path_str += f"|{lat},{lon}"
            
        # Tạo Markers - Điểm đầu Xanh, Điểm cuối Đỏ, Giữa Xanh dương
        markers_list = []
        for i, (lat, lon) in enumerate(display_points):
            color = "blue"
            label = str(i + 1) if i < 9 else "Z"
            
            if i == 0: color = "green" # Điểm bắt đầu
            elif i == len(display_points) - 1: color = "red" # Điểm kết thúc
            
            markers_list.append(f"markers=color:{color}|label:{label}|{lat},{lon}")
            
        return f"{base_url}size=600x400&maptype=roadmap&{path_str}&{'&'.join(markers_list)}&api_key={self.api_key}"

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