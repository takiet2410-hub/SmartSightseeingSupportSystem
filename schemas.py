from pydantic import BaseModel
from typing import List, Optional, Any

# === Input Schema (Giữ nguyên) ===
class HardConstraints(BaseModel):
    budget_range: Optional[str] = None        
    available_time: Optional[str] = None      
    companion_tag: Optional[str] = None       
    season_tag: Optional[str] = None          

class RecommendationRequest(BaseModel):
    hard_constraints: HardConstraints
    vibe_prompt: str 

# === Output Schema (Cập nhật) ===

class RecommendedDestination(BaseModel):
    rank: int
    name: str
    location_province: str 
    specific_address: str
    overall_rating: float
    
    justification_summary: str
    suggested_activities: Optional[List[str]] = None
    image_urls: Optional[List[str]] = None

class RecommendationResponse(BaseModel):
    status: str
    recommendations: List[RecommendedDestination]
    debug_info: Optional[dict] = None