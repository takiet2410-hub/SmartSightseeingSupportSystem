from typing import List, Optional, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field

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

class PhotoOutput(BaseModel):
    id: str
    filename: str
    timestamp: Optional[datetime]
    score: float = 0.0
    image_url: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

class Album(BaseModel):
    title: str
    method: str
    id: str = Field(..., description="Unique Album ID")
    user_id: str = Field(..., description="Owner User ID")
    download_zip_url: Optional[str] = None
    photos: List[PhotoOutput]

class ManualLocationInput(BaseModel):
    album_title: str  # Album title to identify which album
    name: str         # Custom location name
    lat: float
    lon: float

class TripSummaryRequest(BaseModel):
    album_data: Dict[str, Any]  # Album data from /create-album endpoint
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