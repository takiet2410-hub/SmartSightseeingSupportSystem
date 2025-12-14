from typing import List

from schemas import PhotoInput, PhotoOutput, Album
from logger_config import logger
from .algorithms import (
    run_spatiotemporal,      # Tier 1
    run_jenks_time,          # Tier 2
    run_location_hdbscan,    # Tier 3
)

# NOTE: CLIP model removed - no longer needed

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
                # Best case: GPS + Time
                albums = run_spatiotemporal(clean_photos, dist_m=700, gap_min=240)
            elif has_time:
                # Good case: Time only
                albums = run_jenks_time(clean_photos)
            elif has_gps:
                # OK case: GPS only
                albums = run_location_hdbscan(clean_photos)
            else:
                # Worst case: No GPS, No Time - Create single unsorted album
                logger.warning("No GPS or Time metadata - creating unsorted collection")
                albums = ClusteringService._create_unsorted_album(clean_photos)

        # 2. Append the Bad Photos (if any)
        if rejected_photos:
            junk_album = ClusteringService._create_rejected_album(rejected_photos)
            albums.extend(junk_album)
        
        return albums
    
    @staticmethod
    def _create_unsorted_album(photos: List[PhotoInput]) -> List[Album]:
        """
        Create a single album for photos without GPS or Time metadata.
        Sort by quality score.
        """
        if not photos:
            return []
        
        # Sort by quality score (best first)
        photos.sort(key=lambda x: x.score, reverse=True)
        
        out_photos = [
            PhotoOutput(
                id=p.id, 
                filename=p.filename, 
                timestamp=p.timestamp,
                score=p.score
            ) for p in photos
        ]
        
        return [Album(
            title="Unsorted Collection", 
            method="no_metadata_fallback", 
            photos=out_photos
        )]
    
    @staticmethod
    def _create_rejected_album(photos: List[PhotoInput]) -> List[Album]:
        if not photos: 
            return []
        
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