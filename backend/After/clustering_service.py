from abc import ABC, abstractmethod
from typing import List
import uuid

import pandas as pd
import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.cluster import DBSCAN as SklearnDBSCAN
import hdbscan

from schemas import ProcessingDirective, PhotoObject

# =================
# 1. THE INTERFACE
# =================

# Constants
EARTH_RADIUS_KM = 6371.0088  # Earth's radius in kilometers
DEFAULT_EPS_M = 50  # Default epsilon in meters
MIN_EPS_KM = 0.02  # Minimum epsilon: 20 meters
MAX_EPS_KM = 2.0  # Maximum epsilon: 2 kilometers

class ClusteringService(ABC):
    @abstractmethod
    def cluster(self, photos: List[PhotoObject]) -> List[PhotoObject]:
        pass

    def _get_core_coords(self, photos: List[PhotoObject]):
        """
        Helper to extract coordinates from valid photos
        """

        core_photos = [p for p in photos if p.clustering_directive == ProcessingDirective.CLUSTER_CORE]
        if not core_photos:
            return [], []
        
        coords = np.radians([[p.gps_coordinates['lat'], p.gps_coordinates['lon']] for p in core_photos])
        return core_photos, coords
    
    def _calculate_dynamic_eps(self, coords: np.ndarray, min_samples: int) -> float:
        """
        K-Distance method to estimate optimal Epsilon for DBSCAN
        """

        if len(coords) < min_samples:
            return (DEFAULT_EPS_M / 1000) / EARTH_RADIUS_KM  # Default to 50m in radians if too few points
        
        # 1. Calculate distance to the k-th nearest neighbor for every point
        # Metric is Haversine (Radians)
        nbrs = NearestNeighbors(n_neighbors=min_samples, metric='haversine').fit(coords)
        distances, _ = nbrs.kneighbors(coords)

        # 2. Get the distance column for the k-th nearest neighbor (index k-1)
        # distance is shape (n_samples, min_samples)
        k_distances = distances[:, min_samples - 1]

        # 3. Sort low to high
        k_distances = np.sort(k_distances)

        # 4. Find the "elbow" point in the curve
        optimal_rad = np.percentile(k_distances, 90)  # Using 90th percentile as a heuristic

        # 5. Safety Clamps (Prevent extreme values)
        # Convert to Km for readability check
        optimal_km = optimal_rad * EARTH_RADIUS_KM

        # Clamp: Minimum 20 meters, Maximum 2 kilometers
        clamped_km = max(MIN_EPS_KM, min(MAX_EPS_KM, optimal_km))

        print(f"   [Auto-Tune] Calculated eps={optimal_km:.4f}km. Clamped to={clamped_km:.4f}km")

        return clamped_km / EARTH_RADIUS_KM
    
# ===================
# 2. DBSCAN
# ===================

class DBSCAN(ClusteringService):
    def __init__(self, eps_km=None, min_samples=3):
        self.eps_km = eps_km
        self.min_samples = min_samples
        self.kms_per_radian = EARTH_RADIUS_KM

    def cluster(self, photos: List[PhotoObject]) -> List[PhotoObject]:
        core_photos, coords = self._get_core_coords(photos)
        if not core_photos: return photos

        if self.eps_km is None:
            # Dynamically calculate eps using K-Distance method
            eps_radians = self._calculate_dynamic_eps(coords, self.min_samples)
        else:
            eps_radians = self.eps_km / self.kms_per_radian

        db = SklearnDBSCAN(
            eps=eps_radians,
            min_samples=self.min_samples,
            metric='haversine'
        ).fit(coords)

        batch_uuid = str(uuid.uuid4())[:8]
        for photo, label in zip(core_photos, db.labels_):
            if label != -1:
                photo.assigned_cluster_id = f"DBSCAN_{batch_uuid}_{label}"

        return photos
    
# ===========
# 3. ST-HDBSCAN
# ===========

class STHDBSCAN(ClusteringService):
    def __init__(self, min_cluster_size=None, min_samples=None, time_gap_minutes=120):
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.time_gap_seconds = time_gap_minutes * 60
        self.kms_per_radian = EARTH_RADIUS_KM

    def cluster(self, photos: List[PhotoObject]) -> List[PhotoObject]:
        core_photos, coords = self._get_core_coords(photos)
        if not core_photos: return photos

        if self.min_cluster_size is None:
            n = len(core_photos)
            dynamic_size = max(3, int(n * 0.015))
            self.min_cluster_size = min(dynamic_size, 30)
            print(f"   [Auto-Tune] Dataset N={n}. Set min_cluster_size={self.min_cluster_size}")

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            min_samples=self.min_samples,
            metric='haversine'
        ).fit(coords)

        data = []
        for i, photo in enumerate(core_photos):
            data.append({
                'index': i,
                'object': photo,
                'spatial_label': clusterer.labels_[i], # Use HDBSCAN labels
                'time': photo.timestamp_utc
            })

        df = pd.DataFrame(data)
        batch_uuid = str(uuid.uuid4())[:8]

        for label in df['spatial_label'].unique():
            if label == -1:
                continue  # Skip noise

            spatial_group = df[df['spatial_label'] == label].sort_values(by='time')
            
            # The Time Split Logic
            time_split_ids = (spatial_group['time'].diff().dt.total_seconds() > self.time_gap_seconds).cumsum()

            for t_id, row_idxs in spatial_group.groupby(time_split_ids).groups.items():
                sub_group_indices = spatial_group.loc[row_idxs, 'index']
                
                # Name it ST-HDBSCAN to distinguish
                final_cluster_name = f"ST-HDBSCAN_{batch_uuid}_{label}_{t_id}"

                for original_idx in sub_group_indices:
                    core_photos[original_idx].assigned_cluster_id = final_cluster_name

        return photos
    
# =============
# 4. ST-DBSCAN
# =============

class STDBSCAN(ClusteringService):
    def __init__(self, eps_km=None, min_samples=3, time_gap_minutes=120):
        self.eps_km = eps_km
        self.min_samples = min_samples
        self.time_gap_seconds = time_gap_minutes * 60
        self.kms_per_radian = EARTH_RADIUS_KM  # Earth's radius in kilometers

    def cluster(self, photos: List[PhotoObject]) -> List[PhotoObject]:
        """
        Implements the "Filter & Refine" logic:
        1. Run Spatial DBSCAN to get initial clusters
        2. Split Spatial clusters by Time gaps
        """

        core_photos, coords = self._get_core_coords(photos)
        if not core_photos: return photos

        if self.eps_km is None:
            eps_radians = self._calculate_dynamic_eps(coords, self.min_samples)
        else:
            eps_radians = self.eps_km / self.kms_per_radian

        # Step 1: Spatial DBSCAN
        db = SklearnDBSCAN(
            eps=eps_radians,
            min_samples=self.min_samples,
            metric='haversine'
        ).fit(coords)

        # Prepare data for Step 2
        # Map photos to a DataFrame for easier time-diff calculations
        data = []
        for i, photo in enumerate(core_photos):
            data.append({
                'index': i,
                'object': photo,
                'spatial_label': db.labels_[i],
                'time': photo.timestamp_utc
            })

        df = pd.DataFrame(data)
        batch_uuid = str(uuid.uuid4())[:8]

        # Step 2: Refine clusters by Time gaps
        for label in df['spatial_label'].unique():
            if label == -1:
                continue  # Skip noise

            # Get all photos in this phyhsical location, sort by time
            spatial_group = df[df['spatial_label'] == label].sort_values(by='time')
            
            # Find gaps larger than threshold
            # .diff() calculates difference between current row and previous row
            time_split_ids = (spatial_group['time'].diff().dt.total_seconds() > self.time_gap_seconds).cumsum()

            # Assign new cluster IDs based on time splits
            for t_id, row_idxs in spatial_group.groupby(time_split_ids).groups.items():
                # row_idxs are the indices in the original spatial_group
                sub_group_indices = spatial_group.loc[row_idxs, 'index']

                final_cluster_name = f"ST_{batch_uuid}_{label}_{t_id}"

                for original_idx in sub_group_indices:
                    core_photos[original_idx].assigned_cluster_id = final_cluster_name

        return photos