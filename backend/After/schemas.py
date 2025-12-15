from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

# --- INPUT MODEL (Dữ liệu đầu vào từ client) ---
class PhotoInput(BaseModel):
    id: str
    filename: str
    local_path: str 
    timestamp: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_rejected: bool = False
    rejected_reason: str = ""
    score: float = 0.0

# --- OUTPUT MODEL (Dữ liệu trả về cho client) ---
class PhotoOutput(BaseModel):
    id: str
    filename: str
    timestamp: Optional[datetime]
    score: float = 0.0
    image_url: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

class Album(BaseModel):
    # [QUAN TRỌNG] Sửa id và user_id thành Optional = None
    # Để thuật toán Clustering có thể tạo album tạm mà không bị lỗi
    id: Optional[str] = None
    user_id: Optional[str] = None
    
    title: str
    method: str
    download_zip_url: Optional[str] = None
    cover_photo_url: Optional[str] = None
    photos: List[PhotoOutput]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    needs_manual_location: bool = False

# --- MODEL CHO TRIP SUMMARY ---
class ManualLocationInput(BaseModel):
    album_id: str
    name: str
    lat: float
    lon: float

class TripSummaryRequest(BaseModel):
    # Dùng Dict để linh hoạt nhận dữ liệu, tránh lỗi validation chặt chẽ
    album_data: Dict[str, Any] 
    manual_locations: List[ManualLocationInput] = []

class TripSummaryResponse(BaseModel):
    trip_title: str
    total_distance_km: float
    total_locations: int
    total_photos: int
    start_date: str
    end_date: str
    map_image_url: str
    timeline: List[str]

class AlbumUpdateRequest(BaseModel):
    title: str
class OSMGeocodeRequest(BaseModel):
    address: str