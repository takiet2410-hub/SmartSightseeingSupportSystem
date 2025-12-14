import unittest
from summary_service import SummaryService



class TestAfterTripSummary(unittest.TestCase):

    def setUp(self):
        self.service = SummaryService()

    def test_empty_album_data(self):
        result = self.service.generate_summary({"albums": []})
        self.assertEqual(result["total_locations"], 0)
        self.assertEqual(result["total_photos"], 0)

    def test_album_with_gps_photos(self):
        album_data = {
            "albums": [
                {
                    "id": "album_001",
                    "title": "Album GPS",
                    "photos": [
                        {"lat": 21.0, "lon": 105.0, "timestamp": "2024-01-01T10:00:00"},
                        {"lat": 21.1, "lon": 105.1, "timestamp": "2024-01-01T10:05:00"}
                    ]
                }
            ]
        }

        result = self.service.generate_summary(album_data)
        self.assertEqual(result["total_locations"], 1)
        self.assertEqual(result["total_photos"], 2)

    def test_album_no_gps_with_manual_location(self):
        album_data = {
            "albums": [
                {
                    "id": "album_002",
                    "title": "Album No GPS",
                    "photos": [
                        {"timestamp": "2024-01-02T09:00:00"}
                    ]
                }
            ]
        }

        manual_locations = [
            {
                "album_id": "album_002",  # FIX: match by album_id
                "name": "Hà Nội",
                "lat": 21.0285,
                "lon": 105.8542
            }
        ]

        result = self.service.generate_summary(album_data, manual_locations)
        self.assertEqual(result["total_locations"], 1)
        self.assertEqual(result["timeline"][0], "Hà Nội")

    def test_album_no_gps_no_manual_location(self):
        album_data = {
            "albums": [
                {
                    "id": "album_003",
                    "title": "Album Skip",
                    "photos": [
                        {"timestamp": "2024-01-03T09:00:00"}
                    ]
                }
            ]
        }

        result = self.service.generate_summary(album_data)
        self.assertEqual(result["total_locations"], 0)


if __name__ == '__main__':
    unittest.main()
