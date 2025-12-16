"""
Complete Unit Tests for Summary Service
Tests trip summary generation, GPS processing, manual locations, and map generation
"""

import unittest
from summary_service import SummaryService
from datetime import datetime


class TestTripSummary(unittest.TestCase):
    """Basic trip summary tests"""

    def setUp(self):
        self.service = SummaryService()

    def test_empty_album_data(self):
        """Test summary with no albums"""
        result = self.service.generate_summary({"albums": []})
        
        self.assertEqual(result["total_locations"], 0)
        self.assertEqual(result["total_photos"], 0)
        self.assertEqual(len(result["points"]), 0)

    def test_album_with_gps_photos(self):
        """Test summary with GPS-enabled photos"""
        album_data = {
            "albums": [
                {
                    "id": "album_001",
                    "title": "Album GPS 1",
                    "method": "spatiotemporal",
                    "photos": [
                        {
                            "id": "1",
                            "filename": "a.jpg",
                            "lat": 21.0,
                            "lon": 105.0,
                            "timestamp": "2024-01-01T10:00:00Z"
                        }
                    ]
                },
                {
                    "id": "album_002",
                    "title": "Album GPS 2",
                    "method": "spatiotemporal",
                    "photos": [
                        {
                            "id": "2",
                            "filename": "b.jpg",
                            "lat": 21.1,
                            "lon": 105.1,
                            "timestamp": "2024-01-01T10:05:00Z"
                        }
                    ]
                }
            ]
        }

        result = self.service.generate_summary(album_data)
        
        self.assertEqual(result["total_locations"], 2)
        self.assertEqual(result["total_photos"], 2)
        self.assertEqual(len(result["points"]), 2)
        self.assertGreater(result["total_distance_km"], 0)

    def test_album_no_gps_with_manual_location(self):
        """Test summary with manual location override"""
        album_data = {
            "albums": [
                {
                    "id": "album_002",
                    "title": "Album No GPS",
                    "method": "time_only",
                    "photos": [
                        {
                            "id": "1",
                            "filename": "x.jpg",
                            "timestamp": "2024-01-02T09:00:00Z"
                        }
                    ]
                }
            ]
        }

        manual_locations = [
            {
                "album_id": "album_002",
                "name": "Hà Nội",
                "lat": 21.0285,
                "lon": 105.8542
            }
        ]

        result = self.service.generate_summary(album_data, manual_locations)
        
        self.assertEqual(result["total_locations"], 1)
        self.assertEqual(result["timeline"][0], "Hà Nội")
        self.assertEqual(len(result["points"]), 1)

    def test_album_no_gps_no_manual_location(self):
        """Test album without GPS and no manual location is skipped"""
        album_data = {
            "albums": [
                {
                    "id": "album_003",
                    "title": "Album Skip",
                    "method": "time_only",
                    "photos": [
                        {
                            "id": "1",
                            "filename": "y.jpg",
                            "timestamp": "2024-01-03T09:00:00Z"
                        }
                    ]
                }
            ]
        }

        result = self.service.generate_summary(album_data)
        
        self.assertEqual(result["total_locations"], 0)

    def test_rejected_albums_are_skipped(self):
        """Test that rejected albums don't appear in summary"""
        album_data = {
            "albums": [
                {
                    "id": "album_004",
                    "title": "Review Needed (Low Quality)",
                    "method": "filters_rejected",
                    "photos": [
                        {
                            "id": "1",
                            "filename": "bad.jpg",
                            "lat": 21.0,
                            "lon": 105.0
                        }
                    ]
                }
            ]
        }

        result = self.service.generate_summary(album_data)
        
        self.assertEqual(result["total_locations"], 0)
        self.assertEqual(result["total_photos"], 0)


class TestTripSummaryExtended(unittest.TestCase):
    """Extended tests for improved coverage"""

    def setUp(self):
        self.service = SummaryService()

    def test_multiple_albums_distance_calculation(self):
        """Test distance calculation between multiple locations"""
        album_data = {
            "albums": [
                {
                    "id": "a1",
                    "title": "Location 1",
                    "method": "spatiotemporal",
                    "photos": [
                        {"id": "1", "filename": "a.jpg", "lat": 21.0, "lon": 105.0, 
                         "timestamp": "2024-01-01T10:00:00Z"}
                    ]
                },
                {
                    "id": "a2",
                    "title": "Location 2",
                    "method": "spatiotemporal",
                    "photos": [
                        {"id": "2", "filename": "b.jpg", "lat": 21.5, "lon": 105.5,
                         "timestamp": "2024-01-01T12:00:00Z"}
                    ]
                },
                {
                    "id": "a3",
                    "title": "Location 3",
                    "method": "spatiotemporal",
                    "photos": [
                        {"id": "3", "filename": "c.jpg", "lat": 22.0, "lon": 106.0,
                         "timestamp": "2024-01-01T14:00:00Z"}
                    ]
                }
            ]
        }
        
        result = self.service.generate_summary(album_data)
        
        self.assertEqual(result["total_locations"], 3)
        self.assertGreater(result["total_distance_km"], 0)
        self.assertEqual(len(result["timeline"]), 3)

    def test_manual_location_override_priority(self):
        """Test that manual location has priority over GPS"""
        album_data = {
            "albums": [
                {
                    "id": "album_001",
                    "title": "Has GPS",
                    "method": "spatiotemporal",
                    "photos": [
                        {"id": "1", "filename": "a.jpg", "lat": 21.0, "lon": 105.0,
                         "timestamp": "2024-01-01T10:00:00Z"}
                    ]
                }
            ]
        }
        
        manual_locations = [
            {
                "album_id": "album_001",
                "name": "Manual Override",
                "lat": 16.0,
                "lon": 108.0
            }
        ]
        
        result = self.service.generate_summary(album_data, manual_locations)
        
        self.assertEqual(result["timeline"][0], "Manual Override")
        self.assertEqual(result["points"][0], [16.0, 108.0])

    def test_invalid_gps_coordinates(self):
        """Test handling of invalid GPS coordinates (0,0)"""
        album_data = {
            "albums": [
                {
                    "id": "a1",
                    "title": "Invalid GPS",
                    "method": "spatiotemporal",
                    "photos": [
                        {"id": "1", "filename": "a.jpg", "lat": 0.0, "lon": 0.0},
                        {"id": "2", "filename": "b.jpg", "lat": 21.0, "lon": 105.0}
                    ]
                }
            ]
        }
        
        result = self.service.generate_summary(album_data)
        
        self.assertEqual(result["total_locations"], 1)

    def test_album_with_multiple_photos_centroid(self):
        """Test centroid calculation for album with multiple photos"""
        album_data = {
            "albums": [
                {
                    "id": "a1",
                    "title": "Multiple Photos",
                    "method": "spatiotemporal",
                    "photos": [
                        {"id": "1", "filename": "a.jpg", "lat": 21.0, "lon": 105.0},
                        {"id": "2", "filename": "b.jpg", "lat": 21.2, "lon": 105.2},
                        {"id": "3", "filename": "c.jpg", "lat": 21.1, "lon": 105.1}
                    ]
                }
            ]
        }
        
        result = self.service.generate_summary(album_data)
        
        self.assertEqual(result["total_locations"], 1)
        lat, lon = result["points"][0]
        self.assertAlmostEqual(lat, 21.1, places=1)
        self.assertAlmostEqual(lon, 105.1, places=1)

    def test_date_range_extraction(self):
        """Test start_date and end_date extraction"""
        album_data = {
            "albums": [
                {
                    "id": "a1",
                    "title": "First Day",
                    "method": "spatiotemporal",
                    "photos": [
                        {"id": "1", "filename": "a.jpg", "lat": 21.0, "lon": 105.0,
                         "timestamp": "2024-01-01T10:00:00Z"}
                    ]
                },
                {
                    "id": "a2",
                    "title": "Last Day",
                    "method": "spatiotemporal",
                    "photos": [
                        {"id": "2", "filename": "b.jpg", "lat": 21.5, "lon": 105.5,
                         "timestamp": "2024-01-05T15:00:00Z"}
                    ]
                }
            ]
        }
        
        result = self.service.generate_summary(album_data)
        
        self.assertEqual(result["start_date"], "2024-01-01")
        self.assertEqual(result["end_date"], "2024-01-05")

    def test_mixed_albums_with_and_without_gps(self):
        """Test processing mix of GPS and non-GPS albums"""
        album_data = {
            "albums": [
                {
                    "id": "a1",
                    "title": "Has GPS",
                    "method": "spatiotemporal",
                    "photos": [
                        {"id": "1", "filename": "a.jpg", "lat": 21.0, "lon": 105.0}
                    ]
                },
                {
                    "id": "a2",
                    "title": "No GPS",
                    "method": "time_only",
                    "photos": [
                        {"id": "2", "filename": "b.jpg", "timestamp": "2024-01-01T10:00:00Z"}
                    ]
                }
            ]
        }
        
        result = self.service.generate_summary(album_data)
        
        self.assertEqual(result["total_locations"], 1)
        self.assertEqual(result["total_photos"], 2)

    def test_chronological_sorting(self):
        """Test that locations are sorted chronologically"""
        album_data = {
            "albums": [
                {
                    "id": "a3",
                    "title": "Third",
                    "method": "spatiotemporal",
                    "photos": [
                        {"id": "3", "filename": "c.jpg", "lat": 22.0, "lon": 106.0,
                         "timestamp": "2024-01-03T10:00:00Z"}
                    ]
                },
                {
                    "id": "a1",
                    "title": "First",
                    "method": "spatiotemporal",
                    "photos": [
                        {"id": "1", "filename": "a.jpg", "lat": 21.0, "lon": 105.0,
                         "timestamp": "2024-01-01T10:00:00Z"}
                    ]
                },
                {
                    "id": "a2",
                    "title": "Second",
                    "method": "spatiotemporal",
                    "photos": [
                        {"id": "2", "filename": "b.jpg", "lat": 21.5, "lon": 105.5,
                         "timestamp": "2024-01-02T10:00:00Z"}
                    ]
                }
            ]
        }
        
        result = self.service.generate_summary(album_data)
        
        self.assertEqual(result["timeline"], ["First", "Second", "Third"])

    def test_album_with_empty_photos(self):
        """Test handling album with empty photos array"""
        album_data = {
            "albums": [
                {
                    "id": "a1",
                    "title": "Empty Album",
                    "method": "spatiotemporal",
                    "photos": []
                }
            ]
        }
        
        result = self.service.generate_summary(album_data)
        
        self.assertEqual(result["total_locations"], 0)

    def test_coordinate_validation(self):
        """Test _is_valid_coordinate method"""
        # Valid coordinates
        self.assertTrue(self.service._is_valid_coordinate(21.0, 105.0))
        self.assertTrue(self.service._is_valid_coordinate(-16.0, 108.0))
        
        # Invalid coordinates
        self.assertFalse(self.service._is_valid_coordinate(0.0, 0.0))
        self.assertFalse(self.service._is_valid_coordinate(91.0, 105.0))  # > 90
        self.assertFalse(self.service._is_valid_coordinate(21.0, 181.0))  # > 180
        self.assertFalse(self.service._is_valid_coordinate(-91.0, 105.0))  # < -90
        self.assertFalse(self.service._is_valid_coordinate(21.0, -181.0))  # < -180

    def test_mapbox_static_mode(self):
        """Test Mapbox static map generation"""
        album_data = {
            "albums": [
                {
                    "id": "a1",
                    "title": "Location",
                    "method": "spatiotemporal",
                    "photos": [
                        {"id": "1", "filename": "a.jpg", "lat": 21.0, "lon": 105.0}
                    ]
                }
            ]
        }
        
        # Force static mode
        self.service.USE_INTERACTIVE_MAP = False
        
        result = self.service.generate_summary(album_data)
        
        self.assertIn("map_data", result)
        self.assertEqual(result["map_data"]["type"], "static")

    def test_mapbox_interactive_mode(self):
        """Test Mapbox interactive map mode"""
        album_data = {
            "albums": [
                {
                    "id": "a1",
                    "title": "Location",
                    "method": "spatiotemporal",
                    "photos": [
                        {"id": "1", "filename": "a.jpg", "lat": 21.0, "lon": 105.0}
                    ]
                }
            ]
        }
        
        # Force interactive mode
        self.service.USE_INTERACTIVE_MAP = True
        
        result = self.service.generate_summary(album_data)
        
        self.assertIn("map_data", result)
        self.assertEqual(result["map_data"]["type"], "interactive")
        self.assertEqual(result["map_data"]["provider"], "mapbox")

    def test_build_mapbox_static_url_no_token(self):
        """Test Mapbox URL generation without token"""
        # Save original token
        original_token = self.service.mapbox_token
        
        # Remove token
        self.service.mapbox_token = None
        
        url = self.service._build_mapbox_static_url([(21.0, 105.0)])
        
        self.assertEqual(url, "")
        
        # Restore token
        self.service.mapbox_token = original_token

    def test_build_mapbox_static_url_empty_points(self):
        """Test Mapbox URL generation with empty points"""
        url = self.service._build_mapbox_static_url([])
        
        self.assertEqual(url, "")

    def test_build_mapbox_static_url_many_points(self):
        """Test Mapbox URL sampling for many points (>15)"""
        # Create 20 points
        points = [(21.0 + i*0.1, 105.0 + i*0.1) for i in range(20)]
        
        url = self.service._build_mapbox_static_url(points)
        
        # Should still generate URL (with sampling)
        if self.service.mapbox_token:
            self.assertIn("mapbox.com", url)

    def test_manual_location_with_invalid_coordinates(self):
        """Test manual location with invalid lat/lon"""
        album_data = {
            "albums": [
                {
                    "id": "a1",
                    "title": "Album",
                    "method": "spatiotemporal",
                    "photos": [
                        {"id": "1", "filename": "a.jpg"}
                    ]
                }
            ]
        }
        
        manual_locations = [
            {
                "album_id": "a1",
                "name": "Bad Location",
                "lat": "invalid",  # Invalid type
                "lon": 105.0
            }
        ]
        
        result = self.service.generate_summary(album_data, manual_locations)
        
        # Should skip invalid manual location
        self.assertEqual(result["total_locations"], 0)

    def test_album_with_latitude_longitude_keys(self):
        """Test photos using 'latitude' and 'longitude' keys instead of 'lat' and 'lon'"""
        album_data = {
            "albums": [
                {
                    "id": "a1",
                    "title": "Different Keys",
                    "method": "spatiotemporal",
                    "photos": [
                        {"id": "1", "filename": "a.jpg", "latitude": 21.0, "longitude": 105.0}
                    ]
                }
            ]
        }
        
        result = self.service.generate_summary(album_data)
        
        self.assertEqual(result["total_locations"], 1)

    def test_empty_result_structure(self):
        """Test _empty_result returns correct structure"""
        result = self.service._empty_result()
        
        self.assertEqual(result["total_locations"], 0)
        self.assertEqual(result["total_photos"], 0)
        self.assertEqual(result["total_distance_km"], 0)
        self.assertEqual(result["start_date"], "")
        self.assertEqual(result["end_date"], "")
        self.assertEqual(result["timeline"], [])
        self.assertEqual(result["points"], [])
        self.assertIn("map_data", result)


if __name__ == "__main__":
    unittest.main()