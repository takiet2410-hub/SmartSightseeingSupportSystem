from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel, Field, computed_field

from config import BASE_URL

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
    # Hide local path from frontend
    local_path: str = Field(exclude=True) 

    @computed_field
    def url(self) -> str:
        clean = self.local_path.replace("\\", "/")
        if "static" in clean:
            rel = clean.split("static")[-1].strip("/")
            return f"{BASE_URL}/static/{rel}"
        return ""

class Album(BaseModel):
    title: str
    method: str
    photos: List[PhotoOutput]