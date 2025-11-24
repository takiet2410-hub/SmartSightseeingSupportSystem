import os
import re
import uuid
import math
from datetime import datetime, timezone
from collections import defaultdict
from typing import List, Optional, Dict, Any

import exifread
import numpy as np

from schemas import PhotoObject, ProcessingDirective

# =====================================
# SECTION A: HELPER FUNCTIONS (Parsing)
# =====================================

def parse_date_from_filename(filename: str) -> Optional[datetime]:
    """
    Extracts date using strict validation for:
    1. YYYY-MM-DD (e.g., 2025-11-19, 2025.11.19, 2025_11_19)
    2. DD-MM-YYYY (e.g., 19-11-2025, 19.11.2025, 19_11_2025)
    """

    # Regex pattern explanation:
    # - First branch: (19|20)\d{2}[-._](0[1-9]|1[0-2])[-._](0[1-9]|[12]\d|3[01])
    #   Matches YYYY-MM-DD, YYYY.MM.DD, or YYYY_MM_DD formats.
    # - Second branch: (0[1-9]|[12]\d|3[01])[-._](0[1-9]|1[0-2])[-._](19|20)\d{2}
    #   Matches DD-MM-YYYY, DD.MM.YYYY, or DD_MM_YYYY formats.
    pattern = r'(19|20)\d{2}[-._](0[1-9]|1[0-2])[-._](0[1-9]|[12]\d|3[01])|(0[1-9]|[12]\d|3[01])[-._](0[1-9]|1[0-2])[-._](19|20)\d{2}'

    match = re.search(pattern, filename)
    if match:
        try:
            # 1. Get the full string that matched (e.g. "2025-11-19" or "19.11.2025")
            date_str = match.group(0)

            # 2. Split by any of the allowed separators
            parts = re.split(r'[-._]', date_str)

            # 3. Determine Format (Year First vs Year Last)
            if len(parts[0]) == 4:
                # Format: YYYY-MM-DD
                y, m, d = map(int, parts)
            else:
                # Format: DD-MM-YYYY
                d, m, y = map(int, parts)

            # 4. Create Timestamp
            return datetime(y, m, d, 12, 0, 0, tzinfo=timezone.utc)
        
        except (ValueError, IndexError):
            pass

    return None

def parse_timestamp(tags: Dict[str, Any]) -> Optional[datetime]:
    """
    Extract & Standardize Timestamp
    Tries to find a date tag and convert it to a UTC datetime object.
    """

    # List of tags to check in order of priority
    date_tags = ['EXIF DateTimeOriginal', 'EXIF DateTimeDigitized', 'Image DateTime']

    for tag in date_tags:
        if tag in tags:
            try:
                # Common EXIF format: 'YYYY:MM:DD HH:MM:SS'
                dt = datetime.strptime(str(tags[tag]), "%Y:%m:%d %H:%M:%S")

                # Assuming the local time is in UTC for simplicity
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue # If parsing fails, try the next tag

    return None # No valid date found

def dms_to_decimal(dms_values, ref: str) -> float:
    """
    Convert DMS (Degrees, Minutes, Seconds) to Decimal Degrees.
    """

    degrees = float(dms_values[0].num) / float(dms_values[0].den)
    minutes = float(dms_values[1].num) / float(dms_values[1].den)
    seconds = float(dms_values[2].num) / float(dms_values[2].den)

    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)

    return -decimal if ref in ['S', 'W'] else decimal

def parse_gps(tags: Dict[str, Any]) -> Optional[Dict[str, float]]:
    """
    Extract & Standardize GPS
    Convert DMS GPS data to Decimal Degrees.
    Validates that coordinates are within valid ranges.
    """

    try:
        lat = dms_to_decimal(tags['GPS GPSLatitude'].values, str(tags['GPS GPSLatitudeRef']))
        lon = dms_to_decimal(tags['GPS GPSLongitude'].values, str(tags['GPS GPSLongitudeRef']))

        # Validate coordinate ranges
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            print(f"Warning: Invalid GPS coordinates detected - lat={lat}, lon={lon}")
            return None

        return {"lat": lat, "lon": lon}
    except Exception:
        return None
    
def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the Haversine distance between two GPS coordinates.
    Validates input coordinates before calculation.
    """

    # Validate coordinate ranges
    if not (-90 <= lat1 <= 90 and -180 <= lon1 <= 180):
        raise ValueError(f"Invalid coordinates for point 1: lat={lat1}, lon={lon1}")
    if not (-90 <= lat2 <= 90 and -180 <= lon2 <= 180):
        raise ValueError(f"Invalid coordinates for point 2: lat={lat2}, lon={lon2}")

    R = 6371  # Radius of the Earth in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2

    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

# ========================================
# SECTION B: EXTRACTION & LOGIC ASSIGNMENT
# ========================================

def extract_single_image_metadata(temp_file_path: str, original_filename: str) -> PhotoObject:
    """
    Reads one file and returns a PhotoObject with extracted metadata.
    """

    # 1. Initialize
    photo = PhotoObject(
        image_id = str(uuid.uuid4()),
        original_filename = original_filename,
        temp_file_path = temp_file_path
    )

    try:
        # 2. Read EXIF tags
        with open(temp_file_path, 'rb') as f:
            tags = exifread.process_file(f, details=False, extract_thumbnail=False)

        # 3. Extract Raw Data
        exif_time = parse_timestamp(tags)
        filename_time = parse_date_from_filename(original_filename)
        gps_data = parse_gps(tags)

        # 4. Determine Time source
        if exif_time:
            photo.timestamp_utc = exif_time
            time_source = "EXIF"
        elif filename_time:
            photo.timestamp_utc = filename_time
            time_source = "FILENAME"
        else:
            mod_time = os.path.getmtime(temp_file_path)
            photo.timestamp_utc = datetime.fromtimestamp(mod_time, tz=timezone.utc)
            time_source = "FALLBACK"

        photo.gps_coordinates = gps_data

        # 5. Assign Processing Directive based on metadata availability
        # Priority: Time + GPS > Time only > GPS only > Neither
        has_reliable_time = time_source in ["EXIF", "FILENAME"]
        has_gps = gps_data is not None

        if has_gps and has_reliable_time:
            # Perfect data: Ready for clustering
            photo.clustering_directive = ProcessingDirective.CLUSTER_CORE
        elif has_reliable_time and not has_gps:
            # Has precise time, missing GPS: Can interpolate
            photo.clustering_directive = ProcessingDirective.REQUIRE_INTERPOLATION
        elif has_gps and not has_reliable_time:
            # Has GPS but only fallback time: Spatial attachment only
            photo.clustering_directive = ProcessingDirective.SPATIAL_ONLY
        else:
            # No reliable time and no GPS: Manual review required
            photo.clustering_directive = ProcessingDirective.MANUAL_REVIEW

    except Exception as e:
        print(f"Error: {e}")
        photo.clustering_directive = ProcessingDirective.MANUAL_REVIEW
    
    return photo

# =======================
# SECTION D: LOGIC ENGINE
# =======================

def interpolation(photos: List[PhotoObject]) -> List[PhotoObject]:
    """
    Smart Interpolation: Fills GPS gaps based on Time AND Velocity.
    - Short Gaps (<15 mins): Always fill 
    - Stationary Gaps (Speed < 1km/h): Fill up to 4 hours (e.g., Restaurant/Museum).
    - Moving Gaps: Fill only if gap < 30 mins to prevent 'cutting corners' on maps.
    """

    # Sort by time
    candidates = [p for p in photos if p.clustering_directive in [ProcessingDirective.CLUSTER_CORE, ProcessingDirective.REQUIRE_INTERPOLATION]]
    candidates.sort(key=lambda x: x.timestamp_utc)

    for i, photo in enumerate(candidates):
        if photo.clustering_directive != ProcessingDirective.REQUIRE_INTERPOLATION:
            continue

        prev, next_photo = None, None

        # Search backwards for nearest valid GPS
        for j in range(i-1, -1, -1):
            if candidates[j].gps_coordinates:
                prev = candidates[j]; break
            
        # Search forwards for nearest valid GPS
        for j in range(i+1, len(candidates)):
            if candidates[j].gps_coordinates:
                next_photo = candidates[j]; break
            
        if prev and next_photo:
            # 1. Calculate Deltas
            time_gap_seconds = (next_photo.timestamp_utc - prev.timestamp_utc).total_seconds()
            dist_km = haversine_distance(
                prev.gps_coordinates['lat'], prev.gps_coordinates['lon'],
                next_photo.gps_coordinates['lat'], next_photo.gps_coordinates['lon']
            )
            
            # 2. Calculate Implicit Velocity (km/h)
            hours = time_gap_seconds / 3600.0
            velocity = dist_km / hours if hours > 0 else 0

            # 3. Dynamic Threshold Logic
            should_interpolate = False
            
            if time_gap_seconds < (15 * 60):
                # Rule 1: Short gaps (< 15 mins) are always safe
                should_interpolate = True
                
            elif velocity < 1.0 and time_gap_seconds < (4 * 60 * 60):
                # Rule 2: Stationary (< 1 km/h)? Safe up to 4 hours (Museum/Dinner)
                should_interpolate = True
                
            elif velocity < 100.0 and time_gap_seconds < (30 * 60):
                # Rule 3: Moving (Car/Walk)? Only safe if gap < 30 mins (Roads curve!)
                should_interpolate = True
                
            # Rule 4: If Velocity > 100 km/h (Plane), ignore.

            # 4. Execute Interpolation
            if should_interpolate:
                elapsed = (photo.timestamp_utc - prev.timestamp_utc).total_seconds()
                frac = elapsed / time_gap_seconds

                new_lat = prev.gps_coordinates['lat'] + ((next_photo.gps_coordinates['lat'] - prev.gps_coordinates['lat']) * frac)
                new_lon = prev.gps_coordinates['lon'] + ((next_photo.gps_coordinates['lon'] - prev.gps_coordinates['lon']) * frac)

                photo.gps_coordinates = {"lat": new_lat, "lon": new_lon}
                photo.clustering_directive = ProcessingDirective.CLUSTER_CORE
                
                print(f"   [Interpolation] Fixed {photo.original_filename} (Gap: {time_gap_seconds/60:.1f}m, Speed: {velocity:.1f}km/h)")
            else:
                print(f"   [Interpolation] SKIPPED {photo.original_filename} (Gap: {time_gap_seconds/60:.1f}m too large for Speed: {velocity:.1f}km/h)")

    return photos

def spatial_attachment(photos: List[PhotoObject], max_distance_km=0.5) -> List[PhotoObject]:
    """
    Attaches SPATIAL_ONLY (GPS, No Time) photos to the statistically best cluster.
    
    Logic:
    1. Calculate Centroid AND Density (Std Dev) for each cluster.
    2. Define 'Reach' = max(200m, 3 * StdDev).
       - 200m is the minimum 'gravity' of a place.
       - 3*StdDev covers 99% of a normal distribution (statistical reach).
    3. Attach ghost photos if they fall within this dynamic reach.
    """

    # 1. Group Valid Photos
    clusters = defaultdict(list)
    for p in photos:
        if p.assigned_cluster_id:
            clusters[p.assigned_cluster_id].append(p)

    # 2. Calculate Cluster Statistics (Centroid + Radius)
    cluster_stats = {} # {id: {'lat': float, 'lon': float, 'reach_km': float}}
    
    for cluster_id, group in clusters.items():
        lats = [p.gps_coordinates['lat'] for p in group]
        lons = [p.gps_coordinates['lon'] for p in group]
        
        # Centroid
        mean_lat = np.mean(lats)
        mean_lon = np.mean(lons)
        
        # Spread (Standard Deviation in degrees)
        # 1 degree lat ~= 111km. Simple approximation for heuristic.
        std_lat = np.std(lats) * 111
        std_lon = np.std(lons) * 111
        avg_spread_km = (std_lat + std_lon) / 2
        
        # Dynamic Reach: 3-Sigma (99% confidence) or min 200m
        # This means: "If you are within the statistical bounds of this event, join it."
        dynamic_reach = max(0.2, 3 * avg_spread_km)
        
        # Cap it at 5km to prevent "Black Hole" clusters sucking in everything
        dynamic_reach = min(dynamic_reach, 5.0)
        
        cluster_stats[cluster_id] = {
            'lat': mean_lat, 
            'lon': mean_lon, 
            'reach_km': dynamic_reach
        }
        # print(f"   [Cluster {cluster_id[-6:]}] Reach: {dynamic_reach:.3f}km (Spread: {avg_spread_km:.3f}km)")

    # 3. Attach Ghosts
    ghosts = [p for p in photos if p.clustering_directive == ProcessingDirective.SPATIAL_ONLY]
    
    count_attached = 0
    for ghost in ghosts:
        best_match = None
        min_normalized_dist = float('inf') # Score based on "Sigma Distance" (Z-score equivalent)

        for cluster_id, stats in cluster_stats.items():
            dist = haversine_distance(
                ghost.gps_coordinates['lat'], ghost.gps_coordinates['lon'], 
                stats['lat'], stats['lon']
            )
            
            # Check if within that cluster's specific dynamic reach
            if dist < stats['reach_km']:
                # We use a "Normalized Score": Distance / Reach
                # A point 100m from a 200m cluster (Score 0.5) is a better match
                # than a point 100m from a 10km cluster (Score 0.01)?
                # Actually, closer is usually better, but we want to favor TIGHT matches.
                # Let's stick to simple distance for tie-breaking, but filter by reach first.
                
                if dist < min_normalized_dist:
                    min_normalized_dist = dist
                    best_match = cluster_id

        if best_match:
            ghost.assigned_cluster_id = best_match
            count_attached += 1
            # print(f"   [Attachment] Fixed {ghost.original_filename} -> {best_match[-6:]}")
        else:
            ghost.clustering_directive = ProcessingDirective.MANUAL_REVIEW

    if count_attached > 0:
        print(f"--- Spatial Attachment: Recovered {count_attached} ghost photos ---")

    return photos