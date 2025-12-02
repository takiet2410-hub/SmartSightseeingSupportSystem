from typing import List
from datetime import timedelta, datetime

import numpy as np
import jenkspy
import hdbscan
from sklearn.cluster import DBSCAN
from PIL import Image
from sentence_transformers import util
import umap
import torch

from schemas import PhotoInput, PhotoOutput, Album
from logger_config import logger

EARTH_RADIUS_KM = 6371.0088

# --- 1. GPS + TIME: ST-DBSCAN ---
def run_spatiotemporal(photos: List[PhotoInput], dist_m: int, gap_min: int) -> List[Album]:
    """
    1. Groups photos by location (DBSCAN)
    2. Splits groups by time gaps
    3. Cleanup: Merges tiny events (< 3 photos) into a 'Misc' album
    """
    
    logger.info(f"Running ST-DBSCAN (Dist={dist_m}m, Gap={gap_min}min) on {len(photos)} photos")

    # --- PHASE 1: SPATIAL CLUSTERING (DBSCAN) ---

    epsilon_rad = (dist_m / 1000.0) / EARTH_RADIUS_KM
    coords = np.radians([[p.latitude, p.longitude] for p in photos])
    
    # 1. Run DBSCAN
    # metric='haversine' expects radians
    # n_jobs=-1 uses all CPU cores
    # min_samples=1 ensures isolated photos are their own cluster (not noise)
    db = DBSCAN(eps=epsilon_rad, min_samples=1, metric='haversine', n_jobs=-1).fit(coords)
    
    spatial_groups = {}
    for p, label in zip(photos, db.labels_):
        spatial_groups.setdefault(label, []).append(p)

    # --- PHASE 2: TEMPORAL SPLITTING ---
    
    raw_albums = []
    time_gap = timedelta(minutes=gap_min)
    
    for loc_id, group in spatial_groups.items():
        # Crucial: Sort by timestamp to find linear gaps
        group.sort(key=lambda x: x.timestamp)
        
        current_batch = [group[0]]
        
        for i in range(1, len(group)):
            prev_photo = group[i-1]
            curr_photo = group[i]
            
            # Check if the time difference exceeds the threshold
            if (curr_photo.timestamp - prev_photo.timestamp) > time_gap:
                raw_albums.append(current_batch)
                # Reset batch
                current_batch = []
            
            current_batch.append(curr_photo)
            
        # --- Handle the final batch in this location ---
        if current_batch:
            raw_albums.append(current_batch)
            
    # --- PHASE 3: CLEANUP & CONVERSION ---

    final_albums = []
    misc_photos = []

    for batch in raw_albums:
        # If an event is too small (e.g., 1 or 2 photos), demote it to "Misc"
        # Adjust '3' to whatever your threshold for a "Real Event" is
        if len(batch) < 3:
            misc_photos.extend(batch) 
        else:
            batch.sort(key=lambda x: x.score, reverse=True)

            # Create a proper Album - ✅ FIX: Include score=p.score
            out_photos = [PhotoOutput(
                id=p.id,
                filename=p.filename,
                timestamp=p.timestamp,
                score=p.score  # ✅ This was already correct!
            ) for p in batch]

            date_str = batch[0].timestamp.strftime('%Y-%m-%d')
            final_albums.append(Album(
                title=f"Event - {date_str}", 
                method="st_dbscan", 
                photos=out_photos
            ))

    # Handle Miscellaneous photos
    if misc_photos:
        # Sort misc photos by time so the album flows naturally
        misc_photos.sort(key=lambda x: x.score, reverse=True)
        out_misc = [PhotoOutput(
            id=p.id,
            filename=p.filename,
            timestamp=p.timestamp,
            score=p.score  # ✅ This was already correct!
        ) for p in misc_photos]

        # Check date range
        start = misc_photos[0].timestamp
        end = misc_photos[-1].timestamp
        if start.year == end.year:
            title = f"Miscellaneous - {start.year}"
        else:
            title = f"Miscellaneous (Archive)"
        
        final_albums.append(Album(
            title=title,
            method="cleanup_collection", 
            photos=out_misc
        ))

    # --- PHASE 4: FINAL SORT ---
    final_albums.sort(
        key=lambda a: max([p.timestamp for p in a.photos if p.timestamp], default=datetime.min),
        reverse=True
    )
    
    return final_albums

# --- 2. GPS ONLY: HDBSCAN ---
def run_location_hdbscan(photos: List[PhotoInput], min_cluster_size: int = 3) -> List[Album]:
    """
    Uses Hierarchical Clustering to find hotspots of varying densities.

    :param min_cluster_size: Minimum number of photos to form a cluster.
                             Anything smaller becomes 'Miscellaneous'.
    """

    logger.info(f"Running HDBSCAN (Min Cluster Size={min_cluster_size}) on {len(photos)} photos")

    # 1. Run HDBSCAN
    coords = np.radians([[p.latitude, p.longitude] for p in photos])
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size, 
        min_samples=1, 
        metric='haversine'
    )
    labels = clusterer.fit_predict(coords)

    # 2. Group photos by cluster labels
    groups = {}
    noise_photos = []

    for p, label in zip(photos, labels):
        if label == -1:
            noise_photos.append(p)
        else:
            groups.setdefault(label, []).append(p)
            
    albums = []

    # 3. Create Albums - ✅ FIX: Include score
    for label, group in groups.items():
        # Sort by time/filename
        group.sort(key=lambda x: x.score, reverse=True)
        
        out_photos = [PhotoOutput(
            id=p.id,
            filename=p.filename,
            timestamp=p.timestamp,
            score=p.score  # ✅ This was already correct!
        ) for p in group]
        
        # Simple Title
        date_str = group[0].timestamp.strftime('%Y-%m-%d') if group[0].timestamp else "Undated"
        albums.append(Album(
            title=f"Location Cluster #{label} - {date_str}", 
            method="gps_hdbscan", 
            photos=out_photos
        ))

    # 4. Handle Noise - ✅ FIX: Include score
    if noise_photos:
        noise_photos.sort(key=lambda x: x.score, reverse=True)
        out_noise = [PhotoOutput(
            id=p.id,
            filename=p.filename,
            timestamp=p.timestamp,
            score=p.score  # ✅ This was already correct!
        ) for p in noise_photos]
        
        albums.append(Album(
            title="Miscellaneous", 
            method="gps_hdbscan_noise", 
            photos=out_noise
        ))

    # 5. Final Sort 
    albums.sort(
        key=lambda a: max([p.timestamp for p in a.photos if p.timestamp], default=datetime.min),
        reverse=True
    )

    return albums

# --- 3. TIME ONLY: JENKS NATURAL BREAKS ---
def run_jenks_time(photos: List[PhotoInput], max_events: int = 10) -> List[Album]:
    """
    Groups photos by time using Jenks Natural Breaks with GVF auto-optimization.
    Includes downsampling and vectorized slicing for high performance.
    """

    logger.info(f"Running Jenks Time on {len(photos)} photos")
    if not photos: return []
    
    # 1. Prepare Data
    # Sort in-place once (Crucial for the slicing logic later)
    photos.sort(key=lambda x: x.timestamp)
    
    # Convert to float array for numpy math
    timestamps = np.array([p.timestamp.timestamp() for p in photos])
    n_photos = len(photos)

    # 2. Optimization: Downsample
    # Jenks is O(N^2). We cap input at ~500 points to keep it instant.
    if n_photos > 500:
        step = n_photos // 500
        # We perform Jenks on the sample, but apply breaks to the full set
        sample_timestamps = timestamps[::step]
        logger.info(f"Jenks: Downsampling {n_photos} -> {len(sample_timestamps)} points")
    else:
        sample_timestamps = timestamps

    # 3. Find Optimal Breaks (GVF)
    # Ensure reasonable limits (At least 2 groups, at most max_events)
    limit = min(max_events, len(sample_timestamps) - 1)
    if limit < 2: limit = 2
        
    best_breaks = _find_optimal_breaks_gvf(sample_timestamps, max_k=limit)
    
    logger.info(f"Jenks: Optimal split is {len(best_breaks)-1} events.")

    # 4. Slicing (The "Bucket" Phase)
    albums = []
    
    # best_breaks includes [min, break1, break2, ..., max]
    # We only care about the internal split points to find indices
    internal_breaks = best_breaks[1:-1]
    
    # Use searchsorted to map the sample-derived break VALUES back to the FULL timestamp array INDICES
    # side='right' ensures x <= break falls in the left bucket
    split_indices = np.searchsorted(timestamps, internal_breaks, side='right')
    
    # Add start (0) and end (N) indices to loop easily
    # Result looks like: [0, 50, 120, ..., 1000]
    split_indices = np.concatenate(([0], split_indices, [n_photos]))

    # Iterate through indices to slice - ✅ FIX: Include score
    for i in range(len(split_indices) - 1):
        start_idx = split_indices[i]
        end_idx = split_indices[i+1]
        
        # Slice the original PhotoInput list
        batch = photos[start_idx:end_idx]
        
        if batch:
            # Sort by score
            batch.sort(key=lambda x: x.score, reverse=True)
            
            # Output Mapping - ✅ FIX: Add score here!
            out_photos = [PhotoOutput(
                id=p.id,
                filename=p.filename,
                timestamp=p.timestamp,
                score=p.score  # ✅ THIS WAS MISSING!
            ) for p in batch]
            
            # Title strategy: Use the first photo's date
            date_str = batch[0].timestamp.strftime('%Y-%m-%d')
            
            albums.append(Album(
                title=f"Event - {date_str}", 
                method="jenks_gvf", 
                photos=out_photos
            ))

    # Final Sort by Time (Newest First)
    albums.sort(key=lambda a: a.photos[0].timestamp if a.photos else 0, reverse=True)
    return albums

def _find_optimal_breaks_gvf(data: np.array, max_k: int) -> List[float]:
    """
    Calculates Goodness of Variance Fit (GVF) to find the 'Elbow'.
    Uses np.searchsorted for fast, overlap-free variance calculation.
    """
    # Total Variance (SDAM)
    # Variance * Size = Sum of Squared Errors
    sdam = np.var(data) * len(data)
    if sdam == 0: return [data[0], data[-1]]

    best_breaks = []
    previous_gvf = 0.0
    
    for k in range(2, max_k + 1):
        try:
            current_breaks = jenkspy.jenks_breaks(data, n_classes=k)
            
            # OPTIMIZATION: Use searchsorted instead of boolean masking
            # Map values to indices to split the array
            cut_points = current_breaks[1:-1]
            indices = np.searchsorted(data, cut_points, side='right')
            indices = np.concatenate(([0], indices, [len(data)]))
            
            # Calculate Variance inside classes (SDCM)
            sdcm = 0.0
            for i in range(len(indices) - 1):
                start, end = indices[i], indices[i+1]
                if end > start:
                    group = data[start:end]
                    # Faster calculation: Variance * N = Sum((x - mean)^2)
                    sdcm += np.var(group) * len(group)
            
            # GVF Calculation (0.0 to 1.0)
            gvf = 1.0 - (sdcm / sdam)
            
            # STOPPING RULE
            improvement = gvf - previous_gvf
            
            # If fit is excellent (>85%) and diminishing returns (<5%), stop.
            if gvf > 0.85 and improvement < 0.05:
                # Return simpler model (best_breaks) if it exists, else current
                return best_breaks if best_breaks else current_breaks
            
            best_breaks = current_breaks
            previous_gvf = gvf
            
        except Exception as e:
            logger.warning(f"Jenks Optimization Warning at k={k}: {e}")
            continue
            
    # If no elbow found, return the most granular breaks found
    return best_breaks if best_breaks else [data[0], data[-1]]

# --- 4. NO GPS + NO TIME: CLIP + UMAP + HDBSCAN ---
def run_umap_semantic(photos: List[PhotoInput], model) -> List[Album]:
    """
    Semantic Clustering.
    Pipeline: Batch Encoding (CLIP) -> UMAP (Reduction) -> HDBSCAN (Clustering) -> Titling.
    """
    logger.info(f"Running Semantic UMAP on {len(photos)} photos")
    
    # --- 0. SAFETY FALLBACK (Small Batches) ---
    if len(photos) < 3:
        # Sort and return single album - ✅ FIX: Include score
        photos.sort(key=lambda x: x.score, reverse=True)
        return [Album(
            title="Unsorted Collection", 
            method="fallback_small_batch", 
            photos=[PhotoOutput(
                id=p.id, 
                filename=p.filename, 
                timestamp=p.timestamp, 
                score=p.score  # ✅ THIS WAS MISSING!
            ) for p in photos]
        )]

    # --- 1. BATCH ENCODING (Memory Safe) ---
    embeddings = []
    valid_photos = [] 
    batch_size = 32
    
    for i in range(0, len(photos), batch_size):
        batch_paths = photos[i : i + batch_size]
        batch_imgs = []
        
        for p in batch_paths:
            try:
                # Open & convert to RGB
                img = Image.open(p.local_path).convert('RGB')
                img.thumbnail((512, 512))
                batch_imgs.append(img)
                valid_photos.append(p)
            except Exception: continue

        if batch_imgs:
            # no_grad() disables gradient tracking
            with torch.no_grad():
                batch_emb = model.encode(batch_imgs, batch_size=len(batch_imgs))
            embeddings.append(batch_emb)
            del batch_imgs # Free RAM immediately
            
    if not embeddings: return []
    embeddings = np.vstack(embeddings)

    # --- 2. DIMENSIONALITY REDUCTION (UMAP) ---
    # Reduce 512 dimensions -> 5 dimensions for better clustering density
    n_neighbors = min(15, len(embeddings) - 1)
    if n_neighbors < 2: n_neighbors = 2
    
    reducer = umap.UMAP(
        n_neighbors=n_neighbors, 
        n_components=5, 
        min_dist=0.0, 
        metric='cosine', 
        random_state=42, # Deterministic
        n_jobs=1,
        verbose=False
    )
    reduced_data = reducer.fit_transform(embeddings)
    
    # --- 3. CLUSTERING (HDBSCAN) ---
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=3, 
        min_samples=1, 
        metric='euclidean',
        cluster_selection_method='eom',
        cluster_selection_epsilon=0.5
    )
    labels = clusterer.fit_predict(reduced_data)
    
    # Grouping
    groups = {}
    noise = []
    for p, label in zip(valid_photos, labels):
        if label == -1: noise.append(p)
        else: groups.setdefault(label, []).append(p)
            
    # --- 4. ALBUM CREATION & SMART TITLING ---
    albums = []
    
    # Pre-encode candidate labels for Zero-Shot classification
    candidate_labels = [
        "Beach", "Mountain", "City", "Food", "People", 
        "Pets", "Art", "Night", "Nature", "Party", "Work", "Car", "Sunset",
        "Selfie", "Group of People", "Indoor", "Bedroom", 
        "Screenshot", "Document", "Receipt",
        "Flower", "Garden", "Cat", "Dog", 
        "Street", "Building", "Car", "Traffic",
        "Drawing", "Meme"
    ]
    with torch.no_grad():
        label_embeddings = model.encode(candidate_labels)
    
    for label_id, group_photos in groups.items():
        # Sort photos in group
        group_photos.sort(key=lambda x: x.score, reverse=True)
        
        base_title = "Visual Collection"
        try:
            # Title Logic: Re-encode the first photo to guess the content
            rep_img = Image.open(group_photos[0].local_path).convert('RGB')
            with torch.no_grad():
                rep_emb = model.encode(rep_img)
            
            # Compare against text labels
            scores = util.cos_sim(rep_emb, label_embeddings)[0]
            best_idx = scores.argmax().item()
            
            if scores[best_idx] > 0.25: # Confidence threshold
                base_title = f"{candidate_labels[best_idx]} Collection"
        except Exception: pass

        # ✅ FIX: Include score here!
        out_photos = [PhotoOutput(
            id=p.id, 
            filename=p.filename, 
            timestamp=p.timestamp,
            score=p.score  # ✅ THIS WAS MISSING!
        ) for p in group_photos]
        
        albums.append(Album(title=base_title, method="clip_smart_umap", photos=out_photos))

    # --- 5. HANDLE NOISE --- ✅ FIX: Include score
    if noise:
        noise.sort(key=lambda x: x.score, reverse=True)
        albums.append(Album(
            title="Miscellaneous", 
            method="clip_noise", 
            photos=[PhotoOutput(
                id=p.id, 
                filename=p.filename, 
                timestamp=p.timestamp, 
                score=p.score  # ✅ THIS WAS MISSING!
            ) for p in noise]
        ))
        
    # --- 6. FINAL SORT ---
    # Sort albums by date of the first photo
    albums.sort(
        key=lambda a: max([p.timestamp for p in a.photos if p.timestamp], default=datetime.min), 
        reverse=True
    )
    
    return albums