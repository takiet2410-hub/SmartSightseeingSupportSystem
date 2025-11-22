from pydantic import BaseModel, Field
from typing import List, Optional, Any


# 1. INPUT SCHEMA (Frontend gửi lên)
class HardConstraints(BaseModel):
    # Đặt default=None để Frontend có thể bỏ qua nếu user không chọn
    budget_range: Optional[str] = Field(default=None, description="Ngân sách (vd: 1-2 triệu, Thấp, Cao)")
    available_time: Optional[str] = Field(default=None, description="Thời gian rảnh (vd: 1-2 giờ, Trong ngày)")
    companion_tag: Optional[str] = Field(default=None, description="Bạn đồng hành (vd: Gia đình, Cặp đôi)")
    season_tag: Optional[str] = Field(default=None, description="Mùa (vd: Mùa hè, Mùa khô)")
    location_province: Optional[str] = Field(default=None, description="Lọc theo tỉnh thành cụ thể (nếu có)")

class RecommendationRequest(BaseModel):
    hard_constraints: HardConstraints
    vibe_prompt: str = Field(..., description="Mô tả sở thích/mong muốn của user (Bắt buộc)")
    
class WeatherInfo(BaseModel):
    temp: float = Field(..., description="Nhiệt độ (độ C)")
    description: str = Field(..., description="Mô tả (vd: Mưa nhẹ, Nắng)")
    icon: str = Field(..., description="Mã icon của OpenWeather")


# 2. OUTPUT SCHEMA (Trả về Frontend)
class RecommendedDestination(BaseModel):
    # --- Thông tin định danh ---
    rank: int = Field(..., description="Thứ hạng gợi ý (1, 2, 3...)")
    name: str = Field(..., description="Tên địa điểm")
    
    # Thông tin từ Database (Data Enrichment) 
    # Quan trọng: Đặt default="" hoặc 0.0 để tránh lỗi null/missing field ở Frontend
    location_province: str = Field(default="Đang cập nhật", description="Tỉnh/Thành phố")
    specific_address: str = Field(default="", description="Địa chỉ chi tiết")
    overall_rating: float = Field(default=0.0, description="Điểm đánh giá trung bình")
    image_urls: List[str] = Field(default=[], description="Danh sách đường dẫn ảnh")
    description: str = Field(default = "...", description = "Thông tin chi tiết về địa điểm")
    
    #Thông tin từ LLM (Reasoning)
    justification_summary: str = Field(default="Gợi ý dựa trên sự phù hợp của bạn.", description="Lời giải thích tại sao địa điểm này phù hợp")
    suggested_activities: List[str] = Field(default=[], description="Danh sách các hoạt động gợi ý")
    
    #Thông tin thời tiết
    weather: Optional[WeatherInfo] = Field(default=None, description="Thông tin thời tiết hiện tại")

class RecommendationResponse(BaseModel):
    status: str = Field(..., description="Trạng thái request (success/error)")
    recommendations: List[RecommendedDestination]
    debug_info: Optional[dict] = Field(default=None, description="Thông tin debug (số lượng tìm thấy, score...)")