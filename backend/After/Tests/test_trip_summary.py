
"""
Fixed & Deterministic Unit Tests for SummaryService
Scope: Trip summary generation, GPS handling, manual locations, distance & map logic
"""

import unittest
from summary_service import SummaryService


class TestTripSummary(unittest.TestCase):

    def setUp(self):
        self.service = SummaryService()
        # Make tests deterministic
        self.service.mapbox_token = "test-token"
        self.service.USE_INTERACTIVE_MAP = False

    # ---------- BASIC CASES ----------

    def test_empty_album_data(self):
        result = self.service.generate_summary({"albums": []})

        self.assertEqual(result["total_locations"], 0)
        self.assertEqual(result["total_photos"], 0)
        self.assertEqual(result["points"], [])

    def test_album_with_gps_photos(self):
        album_data = {
            "albums": [
                {
                    "id": "a1",
                    "title": "GPS Album",
                    "method": "spatiotemporal",
                    "photos": [
                        {"id": "1", "filename": "a.jpg", "lat": 21.0, "lon": 105.0,
                         "timestamp": "2024-01-01T10:00:00Z"}
                    ]
                }
            ]
        }

        result = self.service.generate_summary(album_data)

        self.assertEqual(result["total_locations"], 1)
        self.assertEqual(result["total_photos"], 1)
        self.assertEqual(len(result["points"]), 1)

    # ---------- MANUAL LOCATION ----------

    def test_manual_location_override(self):
        album_data = {
            "albums": [
                {
                    "id": "a1",
                    "title": "Has GPS",
                    "method": "spatiotemporal",
                    "photos": [{"id": "1", "filename": "a.jpg", "lat": 21.0, "lon": 105.0}]
                }
            ]
        }

        manual_locations = [
            {"album_id": "a1", "name": "Manual Place", "lat": 16.0, "lon": 108.0}
        ]

        result = self.service.generate_summary(album_data, manual_locations)

        self.assertEqual(result["timeline"][0], "Manual Place")
        self.assertEqual(result["points"][0], [16.0, 108.0])

    def test_invalid_manual_location_skipped(self):
        album_data = {
            "albums": [
                {
                    "id": "a1",
                    "title": "Album",
                    "method": "spatiotemporal",
                    "photos": [{"id": "1", "filename": "a.jpg"}]
                }
            ]
        }

        manual_locations = [
            {"album_id": "a1", "name": "Bad", "lat": "x", "lon": 105.0}
        ]

        result = self.service.generate_summary(album_data, manual_locations)
        self.assertEqual(result["total_locations"], 0)

    # ---------- GPS EDGE CASES ----------

    def test_invalid_gps_coordinates(self):
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
        self.assertEqual(len(result["points"]), 1)

    def test_album_with_multiple_photos_centroid(self):
        album_data = {
            "albums": [
                {
                    "id": "a1",
                    "title": "Multi",
                    "method": "spatiotemporal",
                    "photos": [
                        {"lat": 21.0, "lon": 105.0},
                        {"lat": 21.2, "lon": 105.2},
                        {"lat": 21.1, "lon": 105.1}
                    ]
                }
            ]
        }

        result = self.service.generate_summary(album_data)
        lat, lon = result["points"][0]

        self.assertAlmostEqual(lat, 21.1, places=1)
        self.assertAlmostEqual(lon, 105.1, places=1)

    # ---------- DATE & SORTING ----------

    def test_chronological_sorting(self):
        album_data = {
            "albums": [
                {
                    "id": "a3",
                    "title": "Third",
                    "method": "spatiotemporal",
                    "photos": [{"lat": 22.0, "lon": 106.0,
                                 "timestamp": "2024-01-03T10:00:00Z"}]
                },
                {
                    "id": "a1",
                    "title": "First",
                    "method": "spatiotemporal",
                    "photos": [{"lat": 21.0, "lon": 105.0,
                                 "timestamp": "2024-01-01T10:00:00Z"}]
                }
            ]
        }

        result = self.service.generate_summary(album_data)

        self.assertEqual(result["timeline"], ["First", "Third"])
        self.assertEqual(result["start_date"], "2024-01-01")
        self.assertEqual(result["end_date"], "2024-01-03")

    # ---------- MAP LOGIC ----------

    def test_static_map_mode(self):
        album_data = {
            "albums": [
                {
                    "id": "a1",
                    "title": "Map",
                    "method": "spatiotemporal",
                    "photos": [{"lat": 21.0, "lon": 105.0}]
                }
            ]
        }

        result = self.service.generate_summary(album_data)

        self.assertEqual(result["map_data"]["type"], "static")
        self.assertIn("url", result["map_data"])

    def test_build_mapbox_static_url_no_token(self):
        original = self.service.mapbox_token
        try:
            self.service.mapbox_token = None
            url = self.service._build_mapbox_static_url([(21.0, 105.0)])
            self.assertEqual(url, "")
        finally:
            self.service.mapbox_token = original

    def test_build_mapbox_static_url_many_points(self):
        points = [(21.0 + i * 0.1, 105.0 + i * 0.1) for i in range(20)]
        url = self.service._build_mapbox_static_url(points)

        self.assertNotEqual(url, "")
        self.assertIn("mapbox.com", url)

    # ---------- INTERNAL HELPERS ----------

    def test_is_valid_coordinate(self):
        self.assertTrue(self.service._is_valid_coordinate(21.0, 105.0))
        self.assertFalse(self.service._is_valid_coordinate(0.0, 0.0))
        self.assertFalse(self.service._is_valid_coordinate(91.0, 0.0))
        self.assertFalse(self.service._is_valid_coordinate(0.0, 181.0))

    def test_empty_result_structure(self):
        result = self.service._empty_result()

        self.assertEqual(result["total_locations"], 0)
        self.assertEqual(result["total_photos"], 0)
        self.assertEqual(result["map_data"]["type"], "none")


if __name__ == "__main__":
    unittest.main()
