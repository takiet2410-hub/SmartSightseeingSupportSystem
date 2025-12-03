from typing import List, Optional
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

class Album(BaseModel):
    title: str
    method: str
    photos: List[PhotoOutput]