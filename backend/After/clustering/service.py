import threading
from typing import List

from sentence_transformers import SentenceTransformer

from schemas import PhotoInput, PhotoOutput, Album
from logger_config import logger
from .algorithms import (
    run_spatiotemporal,      # Tier 1
    run_jenks_time,          # Tier 2
    run_location_hdbscan,    # Tier 3
    run_umap_semantic        # Tier 4
)

# --- THREAD-SAFE SINGLETON ---
_clip_model = None
_model_lock = threading.Lock()  # ← ADD THIS


def get_model():
    """
    Thread-safe lazy loader for CLIP model.
    """
    global _clip_model
    
    # First check (fast path)
    if _clip_model is not None:
        return _clip_model
    
    # Acquire lock
    with _model_lock:
        # Second check (prevent duplicate loading)
        if _clip_model is not None:
            return _clip_model
        
        logger.info("Loading CLIP Model...")
        _clip_model = SentenceTransformer('clip-ViT-B-32')
        logger.info("CLIP Model Loaded ✓")
        
        return _clip_model


class ClusteringService:
    @staticmethod
    def dispatch(photos: List[PhotoInput]) -> List[Album]:
        """
        Decides the best clustering strategy based on available metadata.
        """
        if not photos: 
            return []
        
        clean_photos = [p for p in photos if not p.is_rejected]
        rejected_photos = [p for p in photos if p.is_rejected]

        # 1. Cluster the Good Photos
        albums = []
        if clean_photos:
            has_time = all(p.timestamp is not None for p in clean_photos)
            has_gps = all(p.latitude is not None and p.longitude is not None for p in clean_photos)
            
            logger.info(f"Router: Count={len(clean_photos)}, Time={has_time}, GPS={has_gps}")

            if has_gps and has_time:
                albums = run_spatiotemporal(clean_photos, dist_m=500, gap_min=240)
            elif has_time:
                albums = run_jenks_time(clean_photos)
            elif has_gps:
                albums = run_location_hdbscan(clean_photos)
            else:
                # Blind Mode
                model = get_model()
                albums = run_umap_semantic(clean_photos, model)

        # 2. Append the Bad Photos (if any)
        if rejected_photos:
            junk_album = ClusteringService._create_rejected_album(rejected_photos)
            albums.extend(junk_album)
        
        return albums
    
    @staticmethod
    def _create_rejected_album(photos: List[PhotoInput]) -> List[Album]:
        if not photos: return []
        
        out_photos = [
            PhotoOutput(
                id=p.id, 
                filename=p.filename, 
                timestamp=p.timestamp,
            ) for p in photos
        ]
        
        return [Album(
            title="Review Needed (Low Quality)", 
            method="filters_rejected", 
            photos=out_photos
        )]