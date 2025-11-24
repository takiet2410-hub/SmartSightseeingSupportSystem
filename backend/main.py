import shutil
import tempfile
import os
from typing import List, Optional
from pathlib import Path

import uvicorn
from fastapi import FastAPI, UploadFile, File, Query

from schemas import ProcessingDirective, PhotoObject, CurationRequest, CurationResponse
from metadata_service import (
    extract_single_image_metadata,
    interpolation,
    spatial_attachment
)

from junk_filter_service import JunkFilterService

from clustering_service import (
    DBSCAN,
    STHDBSCAN,
    STDBSCAN
)

app = FastAPI()
junk_filter = JunkFilterService()
curator = CurationService()

# =====================================
# STRATEGY FACTORY
# =====================================
def get_clustering_strategy(
    algorithm_name: str,
    eps_km: Optional[float] = None,
    time_gap_minutes: int = 120,
    min_cluster_size: Optional[int] = None,
    min_samples: Optional[int] = None
):
    """Factory function to initialize the requested algorithm with optional parameters"""
    if algorithm_name == "st-hdbscan":
        return STHDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
            time_gap_minutes=time_gap_minutes
        )
    elif algorithm_name == "st-dbscan":
        return STDBSCAN(
            eps_km=eps_km,
            time_gap_minutes=time_gap_minutes
        )
    else:
        # Default: dbscan
        return DBSCAN(
            eps_km=eps_km,
            min_samples=min_samples if min_samples is not None else 3
        )

# =====================================
# API ENDPOINT
# =====================================
@app.post("/create-album", response_model=List[PhotoObject])
async def create_album_endpoint(
    files: List[UploadFile] = File(...),
    algorithm: str = Query("st-hdbscan", enum=["dbscan", "st-hdbscan", "st-dbscan"]),
    eps_km: Optional[float] = Query(None, description="Epsilon in km (DBSCAN, ST-DBSCAN). Range: 0.02-2.0 km"),
    time_gap_minutes: int = Query(120, description="Time gap in minutes (ST-DBSCAN, ST-HDBSCAN). Range: 1-1440"),
    min_cluster_size: Optional[int] = Query(None, description="Min cluster size (ST-HDBSCAN). Range: 3-100"),
    min_samples: Optional[int] = Query(None, description="Min samples for clustering")
):
    all_photos = []
    temp_files = []  # Track temporary files for cleanup

    try:
        # 1.Ingest
        if not files or len(files) == 0:
            raise ValueError("No files uploaded")
        
        for file in files:
            suffix = os.path.splitext(file.filename)[1]
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                    shutil.copyfileobj(file.file, temp_file)
                    temp_path = temp_file.name
                    temp_files.append(temp_path)  # Track for cleanup
            
                photo = extract_single_image_metadata(temp_path, file.filename) 
                all_photos.append(photo)
            except Exception as e:
                print(f"⚠️ Failed to process {file.filename}: {e}")
                continue  # Skip this file, process others

        # 2. Junk Filter
        all_photos = junk_filter.filter_batch(all_photos)

        # 3. Separate junk photos
        good_photos = [p for p in all_photos if p.clustering_directive != ProcessingDirective.JUNK_REJECTED]
        rejected_photos = [p for p in all_photos if p.clustering_directive == ProcessingDirective.JUNK_REJECTED]
        
        print(f"--- Processing Pipeline: {len(good_photos)} valid, {len(rejected_photos)} rejected ---")
        
        if good_photos:
            # 4. Interpolation
            good_photos = interpolation(good_photos)

            # 5. Clustering
            print(f"--- Running Clustering using {algorithm.upper()} ---")
            if eps_km:
                print(f"    Parameter: eps_km={eps_km}")
            if time_gap_minutes != 120:
                print(f"    Parameter: time_gap_minutes={time_gap_minutes}")
            if min_cluster_size:
                print(f"    Parameter: min_cluster_size={min_cluster_size}")
            if min_samples:
                print(f"    Parameter: min_samples={min_samples}")
        
            strategy = get_clustering_strategy(
                algorithm,
                eps_km=eps_km,
                time_gap_minutes=time_gap_minutes,
                min_cluster_size=min_cluster_size,
                min_samples=min_samples
            )
            good_photos = strategy.cluster(good_photos)

            # 6. Spatial Attachment
            good_photos = spatial_attachment(good_photos)
        else:
            print("No valid photos after filtering. Returning only rejected photos.")

        return good_photos + rejected_photos
    
    finally:
        # Cleanup temporary files
        for temp_path in temp_files:
            try:
                os.remove(temp_path)
            except Exception as e:
                print(f"Warning: Failed to delete temporary file {temp_path}: {e}")

@app.post("/curate", response_model=CurationResponse)
async def curate_photos(request: CurationRequest):
    """
    Nhận vào 1 list đường dẫn ảnh (ví dụ: 1 cụm ảnh).
    Trả về ảnh tốt nhất (Best Shot).
    """
    best_path, best_score, all_scores = curator.select_best_shot(request.image_paths)
    
    return {
        "best_image": best_path if best_path else "",
        "best_score": best_score,
        "all_candidates": all_scores
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)