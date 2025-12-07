from geopy.distance import geodesic
from typing import List, Dict, Any, Tuple
from config import GOONG_API_KEY # Đảm bảo bạn đã thay key Goong trong config.py

class SummaryService:
    def __init__(self):
        self.api_key = GOONG_API_KEY

    def generate_summary(self, album_data: dict, manual_locations: List[dict]):
        """
        Xử lý Trip Summary dựa trên cấu trúc JSON thực tế:
        Albums -> Photos (có GPS).
        Thuật toán: Tính trung bình cộng tọa độ của photos để tìm tâm của Album.
        """
        
        # 1. Lấy danh sách albums
        albums = album_data.get("albums", [])
        if not albums:
            return self._empty_result()

        # 2. Map dữ liệu sửa tay (Key = album_title)
        manual_map = {m['album_title']: m for m in manual_locations}

        valid_points = []   # Các điểm chốt để vẽ bản đồ
        timeline_names = [] # Tên các điểm đến
        total_photos = 0
        
        # Biến ngày tháng
        start_date = ""
        end_date = ""

        # 3. DUYỆT QUA TỪNG ALBUM
        for album in albums:
            title = album.get("title", "Unknown Event")
            method = album.get("method", "")

            # Bỏ qua album rác
            if method == "filters_rejected" or "Review Needed" in title:
                continue

            photos = album.get("photos", [])
            count = len(photos)
            total_photos += count

            if count == 0:
                continue

            # --- A. TÍNH TOÁN TỌA ĐỘ TRUNG TÂM (CENTROID) ---
            lat_sum = 0.0
            lon_sum = 0.0
            valid_photo_count = 0
            
            # Lấy ngày tháng từ ảnh đầu/cuối của chuyến đi
            if photos:
                current_ts = photos[0].get("timestamp")
                if current_ts and not start_date:
                     start_date = str(current_ts).split("T")[0]
                
                last_ts = photos[-1].get("timestamp")
                if last_ts:
                    end_date = str(last_ts).split("T")[0]

            # Duyệt từng ảnh để cộng dồn tọa độ
            for p in photos:
                p_lat = p.get("lat")
                p_lon = p.get("lon")
                
                # Kiểm tra tọa độ hợp lệ
                if p_lat is not None and p_lon is not None:
                    if float(p_lat) != 0.0 and float(p_lon) != 0.0:
                        lat_sum += float(p_lat)
                        lon_sum += float(p_lon)
                        valid_photo_count += 1
            
            final_lat = None
            final_lon = None

            # Nếu có ảnh có GPS -> Tính trung bình
            if valid_photo_count > 0:
                final_lat = lat_sum / valid_photo_count
                final_lon = lon_sum / valid_photo_count

            # --- B. KIỂM TRA DỮ LIỆU NHẬP TAY (OVERRIDE) ---
            # Nếu user đã sửa địa điểm này, ưu tiên dùng của user
            if title in manual_map:
                user_input = manual_map[title]
                final_lat = user_input.get('lat')
                final_lon = user_input.get('lon')
                if user_input.get('name'):
                    title = user_input.get('name')

            # --- C. LƯU ĐIỂM ĐẠI DIỆN HỢP LỆ ---
            if final_lat is not None and final_lon is not None:
                valid_points.append((final_lat, final_lon))
                timeline_names.append(title)

        # 4. Tính tổng quãng đường
        total_distance = 0.0
        if len(valid_points) > 1:
            for i in range(len(valid_points) - 1):
                dist = geodesic(valid_points[i], valid_points[i+1]).km
                total_distance += dist

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
        Tạo URL bản đồ tĩnh Goong.io
        """
        if not points: return ""
        
        base_url = "https://rsapi.goong.io/staticmap/v1?"
        
        # Nếu quá nhiều điểm, lấy mẫu để URL không bị quá dài
        display_points = points
        if len(points) > 15:
            step = len(points) // 15 + 1
            display_points = points[::step]
            if points[-1] not in display_points:
                display_points.append(points[-1])

        # Tạo đường nối (Path) - Màu xanh dương
        # Goong format: path=color:Hex|weight:Number|lat,lon|lat,lon...
        path_str = "path=color:007bff|weight:5"
        for lat, lon in display_points:
            path_str += f"|{lat},{lon}"
            
        # Tạo Markers - Điểm đầu Xanh, Điểm cuối Đỏ, Giữa Xanh dương
        markers_list = []
        for i, (lat, lon) in enumerate(display_points):
            label = str(i + 1) if i < 9 else "Z"
            color = "blue"
            if i == 0: color = "green"
            elif i == len(display_points) - 1: color = "red"
            
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