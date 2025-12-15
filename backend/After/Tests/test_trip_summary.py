import unittest
from summary_service import SummaryService


class TestTripSummary(unittest.TestCase):

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
        
        # FIXED: Should have 2 locations (2 albums)
        self.assertEqual(result["total_locations"], 2)
        self.assertEqual(result["total_photos"], 2)
        self.assertEqual(len(result["points"]), 2)
        # Distance should be calculated between 2 points
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