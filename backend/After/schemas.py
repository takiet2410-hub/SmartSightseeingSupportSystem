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

class PhotoOutput(BaseModel):
    id: str
    filename: str
    timestamp: Optional[datetime]

class Album(BaseModel):
    title: str
    method: str
    photos: List[PhotoOutput]