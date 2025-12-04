from pydantic import BaseModel, Field
from typing import List, Optional, Any

# --- 1. COMMON SCHEMAS ---
class WeatherInfo(BaseModel):
    temp: float = Field(..., description="Nhiệt độ (độ C)")
    description: str = Field(..., description="Mô tả (vd: Mưa nhẹ, Nắng)")
    icon: str = Field(..., description="Mã icon của OpenWeather")

class HardConstraints(BaseModel):
    # Dùng cho cả filter danh sách và AI
    budget_range: Optional[str] = Field(default=None, description="Ngân sách")
    available_time: Optional[str] = Field(default=None, description="Thời gian rảnh")
    companion_tag: Optional[str] = Field(default=None, description="Bạn đồng hành")
    season_tag: Optional[str] = Field(default=None, description="Mùa")
    location_province: Optional[str] = Field(default=None, description="Lọc theo tỉnh thành")

# --- 2. PAGINATION & LIST VIEW SCHEMAS ---
class DestinationSummary(BaseModel):
    # Khớp với logic: Backend sẽ gán landmark_id vào field này
    id: str = Field(..., description="Mã định danh duy nhất (landmark_id) của địa điểm")
    name: str
    location_province: str
    image_urls: List[str] = Field(default=[])
    overall_rating: float = Field(default=0.0)

class PaginatedResponse(BaseModel):
    data: List[DestinationSummary]
    total: int
    page: int
    limit: int
    total_pages: int

# --- 3. DETAIL VIEW SCHEMA (FULL INFO) ---
class DestinationDetailResponse(BaseModel):
    # Khớp với logic: Backend sẽ gán landmark_id vào field này
    id: str = Field(..., description="Mã định danh duy nhất (landmark_id)")
    name: str
    location_province: str = Field(default="")
    specific_address: str = Field(default="")
    overall_rating: float = Field(default=0.0)
    available_time: Optional[List[str]] = Field(default=[], description="Thời gian phù hợp (Array)")
    season_tag: Optional[List[str]] = Field(default=[], description="Mùa phù hợp (Array)")
    companion_tag: Optional[List[str]] = Field(default=[], description="Bạn đồng hành phù hợp (Array)")
    combined_tags: Optional[List[str]] = Field(default=[], description="Các tag khác (Array)")
    budget_range: str = Field(default="")
    description: str = Field(default="", description="Mô tả chi tiết từ DB")
    image_urls: List[str] = Field(default=[])
    
    # Thông tin thời tiết (Enrichment)
    weather: Optional[WeatherInfo] = Field(default=None)

# --- 4. AI RECOMMENDATION SCHEMAS ---
class RecommendationRequest(BaseModel):
    vibe_prompt: str = Field(..., description="Mô tả sở thích")

class RecommendedDestination(DestinationDetailResponse):
    # Kế thừa từ DetailResponse -> Tự động có field 'id' (là landmark_id)
    justification_summary: str = Field(default="Gợi ý phù hợp", description="Lý do AI chọn")
    suggested_activities: List[str] = Field(default=[], description="Hoạt động gợi ý")

class RecommendationResponse(BaseModel):
    status: str
    recommendations: List[RecommendedDestination]
    debug_info: Optional[dict] = None
    
# --- 5. SEMANTIC SEARCH SCHEMAS ---
class SearchRequest(BaseModel):
    query: str = Field(..., description="Nội dung tìm kiếm (VD: du lịch biển giá rẻ)")
    hard_constraints: Optional[HardConstraints] = Field(default=None, description="Bộ lọc cứng kèm theo")

class SearchResponse(BaseModel):
    # Trả về danh sách DestinationSummary (giống API danh sách) cho nhẹ
    # Hoặc dùng DestinationDetailResponse nếu muốn full info
    data: List[DestinationSummary] 
    total_found: int