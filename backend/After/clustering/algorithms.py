from typing import List
from datetime import timedelta, datetime

import numpy as np
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import jenkspy
import hdbscan
from sklearn.cluster import DBSCAN

from schemas import PhotoInput, PhotoOutput, Album
from logger_config import logger
import math


EARTH_RADIUS_KM = 6371.0088

geolocator = Nominatim(user_agent="smart_tourism_app_v1")

def geographic_center(lats, lons):
    """
    Compute proper geographic centroid
    """
    x = y = z = 0.0

    for lat, lon in zip(lats, lons):
        lat = math.radians(lat)
        lon = math.radians(lon)
        x += math.cos(lat) * math.cos(lon)
        y += math.cos(lat) * math.sin(lon)
        z += math.sin(lat)

    total = len(lats)
    x /= total
    y /= total
    z /= total

    lon = math.atan2(y, x)
    hyp = math.sqrt(x * x + y * y)
    lat = math.atan2(z, hyp)

    return math.degrees(lat), math.degrees(lon)

def get_location_name(lat: float, lon: float) -> str:
    try:
        if lat is None or lon is None:
            return "Unknown Location"

        location = geolocator.reverse(
            (lat, lon),
            language="vi",
            exactly_one=True,
            zoom=18,
            timeout=10
        )

        if not location:
            return "Unknown Location"

        address = location.raw.get("address", {})

        district = (
            address.get("city_district")
            or address.get("suburb")
            or address.get("borough")
            or address.get("city")
        )

        state = address.get("state") or address.get("province")

        if district and state:
            return f"{district}, {state}"
        return state or district or "Unknown Location"

    except GeocoderTimedOut:
        logger.warning("Geocoder timeout")
        return "Unknown Location"

    except Exception as e:
        logger.warning(f"Geocoding failed: {e}")
        return "Unknown Location"



# --- 1. GPS + TIME: ST-DBSCAN ---
def run_spatiotemporal(photos: List[PhotoInput], dist_m: int, gap_min: int) -> List[Album]:
    logger.info(f"Running ST-DBSCAN (Dist={dist_m}m, Gap={gap_min}min) on {len(photos)} photos")

    epsilon_rad = (dist_m / 1000.0) / EARTH_RADIUS_KM
    coords = np.radians([[p.latitude, p.longitude] for p in photos])
    
    db = DBSCAN(
        eps=epsilon_rad, 
        min_samples=1, 
        metric='haversine', 
        n_jobs=-1,
        algorithm='ball_tree'
    ).fit(coords)
    
    spatial_groups = {}
    for p, label in zip(photos, db.labels_):
        spatial_groups.setdefault(label, []).append(p)

    raw_albums = []
    time_gap = timedelta(minutes=gap_min)
    
    for loc_id, group in spatial_groups.items():
        group.sort(key=lambda x: x.timestamp)
        
        current_batch = [group[0]]
        
        for i in range(1, len(group)):
            prev_photo = group[i-1]
            curr_photo = group[i]
            
            if (curr_photo.timestamp - prev_photo.timestamp) > time_gap:
                raw_albums.append(current_batch)
                current_batch = []
            
            current_batch.append(curr_photo)
            
        if current_batch:
            raw_albums.append(current_batch)
            
    final_albums = []
    misc_photos = []

    for batch in raw_albums:
        if len(batch) < 3:
            misc_photos.extend(batch) 
        else:
            batch.sort(key=lambda x: x.score, reverse=True)

            out_photos = [PhotoOutput(
                id=p.id,
                filename=p.filename,
                timestamp=p.timestamp,
                score=p.score
            ) for p in batch]

            date_str = batch[0].timestamp.strftime('%Y-%m-%d')
            lats = [p.latitude for p in batch if p.latitude]
            lons = [p.longitude for p in batch if p.longitude]

            location_title = "Event"
            if lats and lons:
                center_lat, center_lon = geographic_center(lats, lons)
                place_name = get_location_name(center_lat, center_lon)
                if place_name != "Unknown Location":
                    location_title = place_name

            final_albums.append(Album(
                title=f"{location_title} - {date_str}", 
                method="st_dbscan", 
                photos=out_photos
            ))

    if misc_photos:
        misc_photos.sort(key=lambda x: x.score, reverse=True)
        out_misc = [PhotoOutput(
            id=p.id,
            filename=p.filename,
            timestamp=p.timestamp,
            score=p.score
        ) for p in misc_photos]

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

    final_albums.sort(
        key=lambda a: max([p.timestamp for p in a.photos if p.timestamp], default=datetime.min),
        reverse=True
    )
    
    return final_albums

# --- 2. GPS ONLY: HDBSCAN ---
def run_location_hdbscan(photos: List[PhotoInput], min_cluster_size: int = 3) -> List[Album]:
    logger.info(f"Running HDBSCAN (Min Cluster Size={min_cluster_size}) on {len(photos)} photos")

    max_dist_meters = 300
    epsilon_rad = (max_dist_meters / 1000.0) / EARTH_RADIUS_KM
    
    coords = np.radians([[p.latitude, p.longitude] for p in photos])
    
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size, 
        min_samples=1, 
        metric='haversine',
        cluster_selection_epsilon=epsilon_rad,
        core_dist_n_jobs=-1,
        algorithm='best',
        approx_min_span_tree=True
    )
    labels = clusterer.fit_predict(coords)

    groups = {}
    noise_photos = []

    for p, label in zip(photos, labels):
        if label == -1:
            noise_photos.append(p)
        else:
            groups.setdefault(label, []).append(p)
            
    albums = []

    for label, group in groups.items():
        group.sort(key=lambda x: x.score, reverse=True)
        
        out_photos = [PhotoOutput(
            id=p.id,
            filename=p.filename,
            timestamp=p.timestamp,
            score=p.score
        ) for p in group]
        
        date_str = group[0].timestamp.strftime('%Y-%m-%d') if group[0].timestamp else "Undated"
        lats = [p.latitude for p in group if p.latitude is not None]
        lons = [p.longitude for p in group if p.longitude is not None]

        location_title = f"Location Cluster #{label}"

        if lats and lons:
            center_lat, center_lon = geographic_center(lats, lons)
            place_name = get_location_name(center_lat, center_lon)
            if place_name != "Unknown Location":
                location_title = place_name
            
        albums.append(Album(
            title=f"{location_title} - {date_str}", 
            method="gps_hdbscan", 
            photos=out_photos
        ))

    if noise_photos:
        noise_photos.sort(key=lambda x: x.score, reverse=True)
        out_noise = [PhotoOutput(
            id=p.id,
            filename=p.filename,
            timestamp=p.timestamp,
            score=p.score
        ) for p in noise_photos]
        
        albums.append(Album(
            title="Miscellaneous", 
            method="gps_hdbscan_noise", 
            photos=out_noise
        ))

    albums.sort(
        key=lambda a: max([p.timestamp for p in a.photos if p.timestamp], default=datetime.min),
        reverse=True
    )

    return albums

# --- 3. TIME ONLY: JENKS NATURAL BREAKS ---
def run_jenks_time(photos: List[PhotoInput], max_events: int = 10) -> List[Album]:
    logger.info(f"Running Jenks Time on {len(photos)} photos")
    if not photos: return []
    
    photos.sort(key=lambda x: x.timestamp)
    
    timestamps = np.array([p.timestamp.timestamp() for p in photos])
    n_photos = len(photos)

    if n_photos > 500:
        step = n_photos // 500
        sample_timestamps = timestamps[::step]
        logger.info(f"Jenks: Downsampling {n_photos} -> {len(sample_timestamps)} points")
    else:
        sample_timestamps = timestamps

    limit = min(max_events, len(sample_timestamps) - 1)
    if limit < 2: limit = 2
        
    best_breaks = _find_optimal_breaks_gvf(sample_timestamps, max_k=limit)
    
    logger.info(f"Jenks: Optimal split is {len(best_breaks)-1} events.")

    albums = []
    
    internal_breaks = best_breaks[1:-1]
    split_indices = np.searchsorted(timestamps, internal_breaks, side='right')
    split_indices = np.concatenate(([0], split_indices, [n_photos]))

    for i in range(len(split_indices) - 1):
        start_idx = split_indices[i]
        end_idx = split_indices[i+1]
        
        batch = photos[start_idx:end_idx]
        
        if batch:
            batch.sort(key=lambda x: x.score, reverse=True)
            
            out_photos = [PhotoOutput(
                id=p.id,
                filename=p.filename,
                timestamp=p.timestamp,
                score=p.score
            ) for p in batch]
            
            date_str = batch[0].timestamp.strftime('%Y-%m-%d')
            
            albums.append(Album(
                title=f"Event - {date_str}", 
                method="jenks_gvf", 
                photos=out_photos
            ))

    albums.sort(key=lambda a: a.photos[0].timestamp if a.photos else 0, reverse=True)
    return albums

def _find_optimal_breaks_gvf(data: np.array, max_k: int) -> List[float]:
    sdam = np.var(data) * len(data)
    if sdam == 0: return [data[0], data[-1]]

    best_breaks = []
    previous_gvf = 0.0
    
    for k in range(2, max_k + 1):
        try:
            current_breaks = jenkspy.jenks_breaks(data, n_classes=k)
            
            cut_points = current_breaks[1:-1]
            indices = np.searchsorted(data, cut_points, side='right')
            indices = np.concatenate(([0], indices, [len(data)]))
            
            sdcm = 0.0
            for i in range(len(indices) - 1):
                start, end = indices[i], indices[i+1]
                if end > start:
                    group = data[start:end]
                    sdcm += np.var(group) * len(group)
            
            gvf = 1.0 - (sdcm / sdam)
            
            improvement = gvf - previous_gvf
            
            if gvf > 0.85 and improvement < 0.05:
                return best_breaks if best_breaks else current_breaks
            
            best_breaks = current_breaks
            previous_gvf = gvf
            
        except Exception as e:
            logger.warning(f"Jenks Optimization Warning at k={k}: {e}")
            continue
            
    return best_breaks if best_breaks else [data[0], data[-1]]