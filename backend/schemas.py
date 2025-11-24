from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime

class ProcessingDirective(str, Enum):
    '''    
    Define the specific algorithm pipeline for each photo based on metadata completeness.
    '''

    # 1. Perfect Data (Time + GPS) -> Feed to ST-DBSCAN
    CLUSTER_CORE = "CLUSTER_CORE"

    # 2. Has Time, Missing GPS -> Run Interpolation
    REQUIRE_INTERPOLATION = "REQUIRE_INTERPOLATION"

    # 3. Has GPS, Missing Time -> Run Spatial Attachment
    SPATIAL_ONLY = "SPATIAL_ONLY"

    # 4. Junk (No Time + No GPS) -> Manual Drag-and-Drop
    MANUAL_REVIEW = "MANUAL_REVIEW"

    # 5. Rejected by junk filter
    JUNK_REJECTED = "JUNK_REJECTED"

class PhotoObject(BaseModel):
    """
    Defines the standard structure for a proccessed photo.
    """

    image_id: str
    original_filename: str
    temp_file_path: str

    # Use Optional[] for fields that may not always be present
    timestamp_utc: Optional[datetime] = None
    gps_coordinates: Optional[Dict[str, float]] = None # {'lat': ..., 'lon':...}

    # The flag that controls how this photo should be processed downstream
    clustering_directive: ProcessingDirective = Field(default=ProcessingDirective.MANUAL_REVIEW)
    assigned_cluster_id: Optional[str] = None

    # Filter results
    lighting_status: Optional[bool] = None  # True=Good, False=Bad
    lighting_reason: Optional[str] = None
    ml_junk_score: Optional[float] = None  # 0-1 score, higher = more likely junk
    is_junk: Optional[bool] = None  # Final verdict

class CurationRequest(BaseModel):
    image_paths: List[str] # Danh sách đường dẫn ảnh trong 1 cụm

class ScoredImage(BaseModel):
    path: str
    score: float

class CurationResponse(BaseModel):
    best_image: str
    best_score: float
    all_candidates: List[ScoredImage] # Trả về danh sách đã xếp hạng để debug