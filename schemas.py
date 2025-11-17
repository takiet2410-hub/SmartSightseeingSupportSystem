from pydantic import BaseModel
from typing import List, Optional, Any

# === Input Schema ===

class HardConstraints(BaseModel):
    tags: Optional[List[str]] = None  
    # budget_range: Optional[str] = None
    # duration: Optional[int] = None 

class RecommendationRequest(BaseModel):
    hard_constraints: HardConstraints
    vibe_prompt: str 

# === Output Schema ===

class RecommendedDestination(BaseModel):
    rank: int
    name: str
    justification_summary: str
    estimated_budget: Optional[str] = None
    suggested_activities: Optional[List[str]] = None

class RecommendationResponse(BaseModel):
    status: str
    recommendations: List[RecommendedDestination]
    debug_info: Optional[dict] = None