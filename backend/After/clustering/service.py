from typing import List

from sentence_transformers import SentenceTransformer

from schemas import PhotoInput, Album
from logger_config import logger
from .algorithms import (
    run_spatiotemporal,      # Tier 1
    run_jenks_time,          # Tier 2
    run_location_hdbscan,    # Tier 3
    run_umap_semantic        # Tier 4
)

# --- SINGLETON PATTERN ---
# We use a global variable to store the model
_clip_model = None

def get_model():
    """
    Lazy-loads the heavy AI model.
    """

    global _clip_model
    if not _clip_model:
        logger.info("Loading CLIP Model...")
        _clip_model = SentenceTransformer('clip-ViT-B-32')
        logger.info("CLIP Model Loaded.")
    return _clip_model

class ClusteringService:
    @staticmethod
    def dispatch(photos: List[PhotoInput]) -> List[Album]:
        """
        Decides the best clustering strategy based on available metadata.
        """
        if not photos: 
            return []
        
        # 1. Analyze the batch
        # We assume if the majority have metadata, we use it.
        # (Using 'all' is stricter, 'any' is looser. 'all' is safer for albums).
        has_time = all(p.timestamp is not None for p in photos)
        has_gps = all(p.latitude is not None and p.longitude is not None for p in photos)
        
        logger.info(f"Router: Count={len(photos)}, Time={has_time}, GPS={has_gps}")

        # --- TIER 1: GPS + TIME ---
        if has_gps and has_time:
            # Constraints: 500 meters, 4 hours (240 mins)
            return run_spatiotemporal(photos, dist_m=500, gap_min=240)
        
        # --- TIER 2: TIME ONLY ---
        elif has_time:
            # Uses Jenks to adapt to user pacing
            return run_jenks_time(photos)
            
        # --- TIER 3: GPS ONLY ---
        elif has_gps:
            # Uses HDBSCAN to find density hotspots
            return run_location_hdbscan(photos)
            
        # --- TIER 4: BLIND (CONTENT) ---
        else:
            logger.info("Metadata missing. Engaging AI Visual Clustering.")
            # Only NOW do we pay the RAM cost to load the model
            model = get_model()
            return run_umap_semantic(photos, model)
