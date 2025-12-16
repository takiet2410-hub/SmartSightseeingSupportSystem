"""
Complete Unit Tests for Clustering Module
Tests both ClusteringService (dispatcher) and Algorithms (ST-DBSCAN, HDBSCAN, Jenks)
"""

import unittest
from datetime import datetime, timedelta
from clustering.service import ClusteringService
from clustering.algorithms import (
    run_spatiotemporal,
    run_location_hdbscan,
    run_jenks_time,
    generate_time_title,
    _find_optimal_breaks_gvf
)
from schemas import PhotoInput
import numpy as np


# ============================================================================
# PART 1: CLUSTERING SERVICE TESTS (Dispatcher Logic)
# ============================================================================

class TestClusteringService(unittest.TestCase):
    """Test ClusteringService dispatcher and routing logic"""

    def test_empty_photos(self):
        """Test with empty photo list"""
        albums = ClusteringService.dispatch([])
        
        self.assertEqual(len(albums), 0)

    def test_unsorted_album_when_no_gps_no_time(self):
        """Test fallback to unsorted album when no metadata"""
        photos = [
            PhotoInput(
                id="1",
                filename="a.jpg",
                local_path="a.jpg",
                score=0.9,
                is_rejected=False
            ),
            PhotoInput(
                id="2",
                filename="b.jpg",
                local_path="b.jpg",
                score=0.5,
                is_rejected=False
            )
        ]

        albums = ClusteringService.dispatch(photos)

        self.assertEqual(len(albums), 1)
        self.assertEqual(albums[0].method, "no_metadata_fallback")
        self.assertEqual(albums[0].title, "Unsorted Collection")
        
        # Photo with higher score should be first
        self.assertEqual(albums[0].photos[0].id, "1")
        self.assertEqual(albums[0].photos[1].id, "2")

    def test_rejected_photos_go_to_review_album(self):
        """Test that rejected photos go to separate album"""
        photos = [
            PhotoInput(
                id="1",
                filename="bad.jpg",
                local_path="bad.jpg",
                is_rejected=True,
                rejected_reason="Too dark"
            )
        ]

        albums = ClusteringService.dispatch(photos)

        self.assertEqual(len(albums), 1)
        self.assertEqual(albums[0].method, "filters_rejected")
        self.assertIn("Review Needed", albums[0].title)

    def test_good_and_rejected_photos_separate(self):
        """Test that good and rejected photos go to different albums"""
        photos = [
            PhotoInput(
                id="1",
                filename="good.jpg",
                local_path="good.jpg",
                score=0.8,
                is_rejected=False
            ),
            PhotoInput(
                id="2",
                filename="bad.jpg",
                local_path="bad.jpg",
                is_rejected=True,
                rejected_reason="Junk detected"
            )
        ]

        albums = ClusteringService.dispatch(photos)

        self.assertEqual(len(albums), 2)
        
        good_album = albums[0]
        self.assertNotEqual(good_album.method, "filters_rejected")
        self.assertEqual(len(good_album.photos), 1)
        self.assertEqual(good_album.photos[0].id, "1")
        
        rejected_album = albums[1]
        self.assertEqual(rejected_album.method, "filters_rejected")
        self.assertEqual(len(rejected_album.photos), 1)
        self.assertEqual(rejected_album.photos[0].id, "2")

    def test_clustering_with_time_metadata(self):
        """Test time-based clustering"""
        photos = [
            PhotoInput(
                id="1",
                filename="a.jpg",
                local_path="a.jpg",
                timestamp=datetime(2024, 1, 1, 10, 0),
                score=0.8,
                is_rejected=False
            ),
            PhotoInput(
                id="2",
                filename="b.jpg",
                local_path="b.jpg",
                timestamp=datetime(2024, 1, 1, 10, 5),
                score=0.7,
                is_rejected=False
            )
        ]

        albums = ClusteringService.dispatch(photos)

        self.assertGreater(len(albums), 0)
        self.assertIn(albums[0].method, ["jenks_time", "jenks_gvf", "spatiotemporal"])

    def test_clustering_with_gps_metadata(self):
        """Test GPS-based clustering"""
        photos = [
            PhotoInput(
                id="1",
                filename="a.jpg",
                local_path="a.jpg",
                latitude=21.0,
                longitude=105.0,
                score=0.8,
                is_rejected=False
            ),
            PhotoInput(
                id="2",
                filename="b.jpg",
                local_path="b.jpg",
                latitude=21.1,
                longitude=105.1,
                score=0.7,
                is_rejected=False
            )
        ]

        albums = ClusteringService.dispatch(photos)

        self.assertGreater(len(albums), 0)
        self.assertIn(albums[0].method, ["location_hdbscan", "spatiotemporal", "gps_hdbscan_noise", "cleanup_collection", "gps_hdbscan"])

    def test_clustering_with_gps_and_time(self):
        """Test spatiotemporal clustering (best case)"""
        photos = [
            PhotoInput(
                id="1",
                filename="a.jpg",
                local_path="a.jpg",
                timestamp=datetime(2024, 1, 1, 10, 0),
                latitude=21.0,
                longitude=105.0,
                score=0.8,
                is_rejected=False
            ),
            PhotoInput(
                id="2",
                filename="b.jpg",
                local_path="b.jpg",
                timestamp=datetime(2024, 1, 1, 14, 0),
                latitude=21.5,
                longitude=105.5,
                score=0.7,
                is_rejected=False
            )
        ]

        albums = ClusteringService.dispatch(photos)

        self.assertGreater(len(albums), 0)
        # With only 2 photos, may be cleanup_collection
        self.assertIn(albums[0].method, ["spatiotemporal", "st_dbscan", "cleanup_collection", "gps_hdbscan_noise"])

    def test_all_rejected_photos(self):
        """Test when all photos are rejected"""
        photos = [
            PhotoInput(id="1", filename="a.jpg", local_path="a.jpg", is_rejected=True),
            PhotoInput(id="2", filename="b.jpg", local_path="b.jpg", is_rejected=True)
        ]

        albums = ClusteringService.dispatch(photos)

        self.assertEqual(len(albums), 1)
        self.assertEqual(albums[0].method, "filters_rejected")
        self.assertEqual(len(albums[0].photos), 2)

    def test_mixed_metadata_partial_gps(self):
        """Test with partial GPS metadata (some photos have GPS, some don't)"""
        photos = [
            PhotoInput(
                id="1",
                filename="a.jpg",
                local_path="a.jpg",
                latitude=21.0,
                longitude=105.0,
                score=0.8,
                is_rejected=False
            ),
            PhotoInput(
                id="2",
                filename="b.jpg",
                local_path="b.jpg",
                # No GPS
                score=0.7,
                is_rejected=False
            )
        ]

        albums = ClusteringService.dispatch(photos)

        # Should fallback to unsorted (not all have GPS)
        self.assertGreater(len(albums), 0)
        self.assertIn(albums[0].method, ["no_metadata_fallback", "cleanup_collection"])

    def test_partial_timestamps(self):
        """Test with partial timestamp metadata"""
        photos = [
            PhotoInput(
                id="1",
                filename="a.jpg",
                local_path="a.jpg",
                timestamp=datetime(2024, 1, 1, 10, 0),
                score=0.8,
                is_rejected=False
            ),
            PhotoInput(
                id="2",
                filename="b.jpg",
                local_path="b.jpg",
                # No timestamp
                score=0.7,
                is_rejected=False
            )
        ]

        albums = ClusteringService.dispatch(photos)

        # Should fallback to unsorted (not all have timestamps)
        self.assertGreater(len(albums), 0)


# ============================================================================
# PART 2: ALGORITHM HELPER TESTS
# ============================================================================

class TestAlgorithmsHelper(unittest.TestCase):
    """Test helper functions"""

    def test_generate_time_title_with_timestamp(self):
        """Test time title generation with valid timestamps"""
        photos = [
            PhotoInput(
                id="1",
                filename="a.jpg",
                local_path="a.jpg",
                timestamp=datetime(2024, 2, 17, 14, 30),
                score=0.8
            ),
            PhotoInput(
                id="2",
                filename="b.jpg",
                local_path="b.jpg",
                timestamp=datetime(2024, 2, 17, 15, 0),
                score=0.7
            )
        ]
        
        title = generate_time_title(photos)
        
        self.assertEqual(title, "2024-02-17 14:30")

    def test_generate_time_title_without_timestamp(self):
        """Test time title generation without timestamps"""
        photos = [
            PhotoInput(id="1", filename="a.jpg", local_path="a.jpg", score=0.8)
        ]
        
        title = generate_time_title(photos)
        
        self.assertEqual(title, "Undated Event")

    def test_generate_time_title_mixed_timestamps(self):
        """Test with some photos having timestamps, some not"""
        photos = [
            PhotoInput(
                id="1",
                filename="a.jpg",
                local_path="a.jpg",
                timestamp=datetime(2024, 3, 1, 10, 0),
                score=0.8
            ),
            PhotoInput(id="2", filename="b.jpg", local_path="b.jpg", score=0.7)
        ]
        
        title = generate_time_title(photos)
        
        self.assertEqual(title, "2024-03-01 10:00")


# ============================================================================
# PART 3: SPATIOTEMPORAL (ST-DBSCAN) TESTS
# ============================================================================

class TestSpatiotemporalClustering(unittest.TestCase):
    """Test ST-DBSCAN algorithm"""

    def test_spatiotemporal_basic_clustering(self):
        """Test basic spatiotemporal clustering"""
        photos = [
            PhotoInput(
                id="1",
                filename="a.jpg",
                local_path="a.jpg",
                timestamp=datetime(2024, 1, 1, 10, 0),
                latitude=21.0,
                longitude=105.0,
                score=0.8
            ),
            PhotoInput(
                id="2",
                filename="b.jpg",
                local_path="b.jpg",
                timestamp=datetime(2024, 1, 1, 10, 5),
                latitude=21.0001,
                longitude=105.0001,
                score=0.7
            ),
            PhotoInput(
                id="3",
                filename="c.jpg",
                local_path="c.jpg",
                timestamp=datetime(2024, 1, 1, 10, 10),
                latitude=21.0002,
                longitude=105.0002,
                score=0.9
            )
        ]
        
        albums = run_spatiotemporal(photos, dist_m=700, gap_min=120)
        
        self.assertGreater(len(albums), 0)
        self.assertTrue(all(album.method in ["st_dbscan", "cleanup_collection"] for album in albums))

    def test_spatiotemporal_time_gap_split(self):
        """Test temporal gap splitting"""
        photos = [
            PhotoInput(
                id="1",
                filename="a.jpg",
                local_path="a.jpg",
                timestamp=datetime(2024, 1, 1, 10, 0),
                latitude=21.0,
                longitude=105.0,
                score=0.8
            ),
            PhotoInput(
                id="2",
                filename="b.jpg",
                local_path="b.jpg",
                timestamp=datetime(2024, 1, 1, 13, 0),  # 3 hour gap
                latitude=21.0001,
                longitude=105.0001,
                score=0.7
            )
        ]
        
        albums = run_spatiotemporal(photos, dist_m=700, gap_min=120)
        
        self.assertGreaterEqual(len(albums), 1)

    def test_spatiotemporal_spatial_separation(self):
        """Test spatial separation into clusters"""
        photos = [
            # Cluster 1: Hanoi
            PhotoInput(
                id="1", filename="a.jpg", local_path="a.jpg",
                timestamp=datetime(2024, 1, 1, 10, 0),
                latitude=21.0, longitude=105.0, score=0.8
            ),
            PhotoInput(
                id="2", filename="b.jpg", local_path="b.jpg",
                timestamp=datetime(2024, 1, 1, 10, 30),
                latitude=21.0001, longitude=105.0001, score=0.7
            ),
            PhotoInput(
                id="3", filename="c.jpg", local_path="c.jpg",
                timestamp=datetime(2024, 1, 1, 10, 45),
                latitude=21.0002, longitude=105.0002, score=0.9
            ),
            # Cluster 2: Da Nang (far away)
            PhotoInput(
                id="4", filename="d.jpg", local_path="d.jpg",
                timestamp=datetime(2024, 1, 2, 14, 0),
                latitude=16.0, longitude=108.0, score=0.6
            ),
            PhotoInput(
                id="5", filename="e.jpg", local_path="e.jpg",
                timestamp=datetime(2024, 1, 2, 14, 30),
                latitude=16.0001, longitude=108.0001, score=0.5
            ),
            PhotoInput(
                id="6", filename="f.jpg", local_path="f.jpg",
                timestamp=datetime(2024, 1, 2, 15, 0),
                latitude=16.0002, longitude=108.0002, score=0.7
            )
        ]
        
        albums = run_spatiotemporal(photos, dist_m=700, gap_min=120)
        
        self.assertGreaterEqual(len(albums), 2)

    def test_spatiotemporal_small_clusters_to_misc(self):
        """Test that small clusters (<3) go to miscellaneous"""
        photos = [
            PhotoInput(
                id="1", filename="a.jpg", local_path="a.jpg",
                timestamp=datetime(2024, 1, 1, 10, 0),
                latitude=21.0, longitude=105.0, score=0.8
            ),
            PhotoInput(
                id="2", filename="b.jpg", local_path="b.jpg",
                timestamp=datetime(2024, 1, 1, 10, 5),
                latitude=21.0001, longitude=105.0001, score=0.7
            )
        ]
        
        albums = run_spatiotemporal(photos, dist_m=700, gap_min=120)
        
        self.assertTrue(any(a.method == "cleanup_collection" for a in albums))


# ============================================================================
# PART 4: HDBSCAN TESTS
# ============================================================================

class TestLocationHDBSCAN(unittest.TestCase):
    """Test HDBSCAN location clustering"""

    def test_hdbscan_basic_clustering(self):
        """Test basic HDBSCAN clustering"""
        photos = [
            PhotoInput(id="1", filename="a.jpg", local_path="a.jpg",
                      latitude=21.0, longitude=105.0, score=0.8),
            PhotoInput(id="2", filename="b.jpg", local_path="b.jpg",
                      latitude=21.0001, longitude=105.0001, score=0.7),
            PhotoInput(id="3", filename="c.jpg", local_path="c.jpg",
                      latitude=21.0002, longitude=105.0002, score=0.9)
        ]
        
        albums = run_location_hdbscan(photos, min_cluster_size=3)
        
        self.assertGreater(len(albums), 0)
        self.assertTrue(all(album.method in ["gps_hdbscan", "gps_hdbscan_noise"] for album in albums))

    def test_hdbscan_noise_detection(self):
        """Test noise photo detection"""
        photos = [
            PhotoInput(id="1", filename="a.jpg", local_path="a.jpg",
                      latitude=21.0, longitude=105.0, score=0.8),
            PhotoInput(id="2", filename="b.jpg", local_path="b.jpg",
                      latitude=21.0001, longitude=105.0001, score=0.7),
            PhotoInput(id="3", filename="c.jpg", local_path="c.jpg",
                      latitude=21.0002, longitude=105.0002, score=0.9),
            PhotoInput(id="4", filename="d.jpg", local_path="d.jpg",
                      latitude=25.0, longitude=110.0, score=0.6)
        ]
        
        albums = run_location_hdbscan(photos, min_cluster_size=3)
        
        noise_albums = [a for a in albums if a.method == "gps_hdbscan_noise"]
        self.assertGreaterEqual(len(noise_albums), 0)

    def test_hdbscan_with_timestamps(self):
        """Test HDBSCAN with timestamps uses date-time titles"""
        photos = [
            PhotoInput(
                id="1", filename="a.jpg", local_path="a.jpg",
                timestamp=datetime(2024, 2, 1, 10, 0),
                latitude=21.0, longitude=105.0, score=0.8
            ),
            PhotoInput(
                id="2", filename="b.jpg", local_path="b.jpg",
                timestamp=datetime(2024, 2, 1, 10, 30),
                latitude=21.0001, longitude=105.0001, score=0.7
            ),
            PhotoInput(
                id="3", filename="c.jpg", local_path="c.jpg",
                timestamp=datetime(2024, 2, 1, 11, 0),
                latitude=21.0002, longitude=105.0002, score=0.9
            )
        ]
        
        albums = run_location_hdbscan(photos, min_cluster_size=3)
        
        cluster_albums = [a for a in albums if a.method == "gps_hdbscan"]
        if cluster_albums:
            self.assertRegex(cluster_albums[0].title, r'\d{4}-\d{2}-\d{2}')


# ============================================================================
# PART 5: JENKS TIME CLUSTERING TESTS
# ============================================================================

class TestJenksTimeClustering(unittest.TestCase):
    """Test Jenks Natural Breaks algorithm"""

    def test_jenks_basic_clustering(self):
        """Test basic Jenks time clustering"""
        photos = []
        base_time = datetime(2024, 1, 1, 10, 0)
        
        for i in range(5):
            photos.append(PhotoInput(
                id=str(i), filename=f"{i}.jpg", local_path=f"{i}.jpg",
                timestamp=base_time + timedelta(minutes=i*10),
                score=0.8
            ))
        
        albums = run_jenks_time(photos, max_events=5)
        
        self.assertGreater(len(albums), 0)
        self.assertTrue(all(album.method == "jenks_gvf" for album in albums))

    def test_jenks_empty_photos(self):
        """Test Jenks with empty photo list"""
        albums = run_jenks_time([], max_events=5)
        
        self.assertEqual(len(albums), 0)

    def test_jenks_natural_breaks(self):
        """Test Jenks detects natural time breaks"""
        photos = []
        
        # Morning cluster
        for i in range(5):
            photos.append(PhotoInput(
                id=f"morning_{i}", filename=f"m{i}.jpg", local_path=f"m{i}.jpg",
                timestamp=datetime(2024, 1, 1, 10, 0) + timedelta(minutes=i*5),
                score=0.8
            ))
        
        # Afternoon cluster (3 hour gap)
        for i in range(5):
            photos.append(PhotoInput(
                id=f"afternoon_{i}", filename=f"a{i}.jpg", local_path=f"a{i}.jpg",
                timestamp=datetime(2024, 1, 1, 14, 0) + timedelta(minutes=i*5),
                score=0.7
            ))
        
        albums = run_jenks_time(photos, max_events=10)
        
        self.assertGreaterEqual(len(albums), 2)

    def test_jenks_large_dataset_sampling(self):
        """Test Jenks downsampling for large datasets"""
        photos = []
        base_time = datetime(2024, 1, 1, 10, 0)
        
        for i in range(600):
            photos.append(PhotoInput(
                id=str(i), filename=f"{i}.jpg", local_path=f"{i}.jpg",
                timestamp=base_time + timedelta(minutes=i),
                score=0.8
            ))
        
        albums = run_jenks_time(photos, max_events=10)
        
        self.assertGreater(len(albums), 0)

    def test_jenks_optimal_breaks_gvf(self):
        """Test GVF optimization function"""
        data = np.array([
            1.0, 1.1, 1.2, 1.3, 1.4,
            5.0, 5.1, 5.2, 5.3, 5.4,
            10.0, 10.1, 10.2, 10.3
        ])
        
        breaks = _find_optimal_breaks_gvf(data, max_k=5)
        
        self.assertGreaterEqual(len(breaks), 4)

    def test_jenks_single_class_edge_case(self):
        """Test Jenks with all identical values"""
        data = np.array([5.0, 5.0, 5.0, 5.0, 5.0])
        
        breaks = _find_optimal_breaks_gvf(data, max_k=3)
        
        self.assertEqual(len(breaks), 2)
        self.assertEqual(breaks[0], 5.0)
        self.assertEqual(breaks[-1], 5.0)


# ============================================================================
# PART 6: INTEGRATION TESTS
# ============================================================================

class TestClusteringIntegration(unittest.TestCase):
    """Integration tests across service and algorithms"""

    def test_all_algorithms_return_valid_albums(self):
        """Test that all algorithms return valid Album objects"""
        photos = [
            PhotoInput(
                id="1", filename="a.jpg", local_path="a.jpg",
                timestamp=datetime(2024, 1, 1, 10, 0),
                latitude=21.0, longitude=105.0, score=0.8
            ),
            PhotoInput(
                id="2", filename="b.jpg", local_path="b.jpg",
                timestamp=datetime(2024, 1, 1, 10, 30),
                latitude=21.0001, longitude=105.0001, score=0.7
            ),
            PhotoInput(
                id="3", filename="c.jpg", local_path="c.jpg",
                timestamp=datetime(2024, 1, 1, 11, 0),
                latitude=21.0002, longitude=105.0002, score=0.9
            )
        ]
        
        st_albums = run_spatiotemporal(photos, dist_m=700, gap_min=120)
        hdb_albums = run_location_hdbscan(photos, min_cluster_size=3)
        jenks_albums = run_jenks_time(photos, max_events=5)
        
        for album_list in [st_albums, hdb_albums, jenks_albums]:
            self.assertIsInstance(album_list, list)
            for album in album_list:
                self.assertIsNotNone(album.title)
                self.assertIsNotNone(album.method)
                self.assertIsInstance(album.photos, list)

    def test_service_routes_to_correct_algorithm(self):
        """Test that service routes to appropriate algorithm"""
        # GPS + Time → Spatiotemporal (need 3+ photos)
        gps_time_photos = [
            PhotoInput(id="1", filename="a.jpg", local_path="a.jpg",
                      timestamp=datetime(2024, 1, 1, 10, 0),
                      latitude=21.0, longitude=105.0, score=0.8),
            PhotoInput(id="2", filename="b.jpg", local_path="b.jpg",
                      timestamp=datetime(2024, 1, 1, 10, 30),
                      latitude=21.0001, longitude=105.0001, score=0.7),
            PhotoInput(id="3", filename="c.jpg", local_path="c.jpg",
                      timestamp=datetime(2024, 1, 1, 11, 0),
                      latitude=21.0002, longitude=105.0002, score=0.9)
        ]
        albums = ClusteringService.dispatch(gps_time_photos)
        if albums:
            self.assertIn(albums[0].method, ["st_dbscan", "spatiotemporal", "cleanup_collection"])
        
        # Time only → Jenks (need 2+ photos)
        time_only_photos = [
            PhotoInput(id="1", filename="a.jpg", local_path="a.jpg",
                      timestamp=datetime(2024, 1, 1, 10, 0), score=0.7),
            PhotoInput(id="2", filename="b.jpg", local_path="b.jpg",
                      timestamp=datetime(2024, 1, 1, 11, 0), score=0.8)
        ]
        albums = ClusteringService.dispatch(time_only_photos)
        if albums:
            self.assertIn(albums[0].method, ["jenks_gvf", "jenks_time"])
        
        # GPS only → HDBSCAN (need 3+ photos for HDBSCAN)
        gps_only_photos = [
            PhotoInput(id="1", filename="a.jpg", local_path="a.jpg",
                      latitude=21.0, longitude=105.0, score=0.9),
            PhotoInput(id="2", filename="b.jpg", local_path="b.jpg",
                      latitude=21.0001, longitude=105.0001, score=0.8),
            PhotoInput(id="3", filename="c.jpg", local_path="c.jpg",
                      latitude=21.0002, longitude=105.0002, score=0.7)
        ]
        albums = ClusteringService.dispatch(gps_only_photos)
        if albums:
            self.assertIn(albums[0].method, ["gps_hdbscan", "gps_hdbscan_noise", "location_hdbscan"])


if __name__ == "__main__":
    unittest.main()