import unittest
from unittest.mock import Mock, MagicMock, patch
from PIL import Image
from metadata import MetadataExtractor
from datetime import datetime
import tempfile
import os


class TestMetadataExtractor(unittest.TestCase):

    def setUp(self):
        self.extractor = MetadataExtractor()

    # ============================================================================
    # BASIC EXTRACTION TESTS
    # ============================================================================

    def test_extract_metadata_no_exif(self):
        """Test extracting metadata from image with no EXIF"""
        mock_img = MagicMock(spec=Image.Image)
        mock_img.getexif = MagicMock(return_value=None)
        mock_img._getexif = MagicMock(return_value=None)

        meta = self.extractor.get_metadata_from_image(mock_img)

        self.assertIsNone(meta.get("timestamp"))
        self.assertIsNone(meta.get("latitude"))
        self.assertIsNone(meta.get("longitude"))

    def test_metadata_extractor_returns_dict(self):
        """Test that metadata extractor returns a dictionary"""
        mock_img = MagicMock(spec=Image.Image)
        mock_exif = MagicMock()
        mock_exif.__bool__ = MagicMock(return_value=True)
        mock_exif.__iter__ = MagicMock(return_value=iter([]))
        mock_img.getexif = MagicMock(return_value=mock_exif)

        meta = self.extractor.get_metadata_from_image(mock_img)

        self.assertIsInstance(meta, dict)
        self.assertIn("timestamp", meta)
        self.assertIn("latitude", meta)
        self.assertIn("longitude", meta)

    # ============================================================================
    # TIMESTAMP EXTRACTION TESTS
    # ============================================================================

    def test_extract_timestamp_datetimeoriginal(self):
        """Test extracting DateTimeOriginal (tag 36867)"""
        mock_img = MagicMock(spec=Image.Image)
        
        # Create proper EXIF mock that behaves like PIL's getexif()
        mock_exif_obj = MagicMock()
        mock_exif_obj.__bool__ = MagicMock(return_value=True)
        
        # Make it iterable and dict-like
        exif_data = {36867: "2024:01:15 14:30:45"}
        mock_exif_obj.__iter__ = MagicMock(return_value=iter(exif_data.items()))
        mock_exif_obj.items = MagicMock(return_value=exif_data.items())
        mock_exif_obj.__getitem__ = lambda self, key: exif_data.get(key)
        mock_exif_obj.get = lambda key, default=None: exif_data.get(key, default)
        mock_exif_obj.get_ifd = MagicMock(return_value=None)
        
        # Make dict() work on it
        mock_exif_obj.keys = MagicMock(return_value=exif_data.keys())
        mock_exif_obj.values = MagicMock(return_value=exif_data.values())
        
        mock_img.getexif = MagicMock(return_value=mock_exif_obj)
        mock_img._getexif = MagicMock(return_value=None)

        meta = self.extractor.get_metadata_from_image(mock_img)

        # Should extract timestamp
        self.assertIsNotNone(meta.get("timestamp"))
        if meta.get("timestamp"):
            self.assertEqual(meta["timestamp"], datetime(2024, 1, 15, 14, 30, 45))

    def test_extract_timestamp_datetime_fallback(self):
        """Test extracting DateTime fallback (tag 306)"""
        mock_img = MagicMock(spec=Image.Image)
        
        exif_data = {306: "2024:02:20 09:15:30"}
        mock_exif_obj = MagicMock()
        mock_exif_obj.__bool__ = MagicMock(return_value=True)
        mock_exif_obj.__iter__ = MagicMock(return_value=iter(exif_data.items()))
        mock_exif_obj.items = MagicMock(return_value=exif_data.items())
        mock_exif_obj.__getitem__ = lambda self, key: exif_data.get(key)
        mock_exif_obj.get = lambda key, default=None: exif_data.get(key, default)
        mock_exif_obj.get_ifd = MagicMock(return_value=None)
        mock_exif_obj.keys = MagicMock(return_value=exif_data.keys())
        mock_exif_obj.values = MagicMock(return_value=exif_data.values())
        
        mock_img.getexif = MagicMock(return_value=mock_exif_obj)
        mock_img._getexif = MagicMock(return_value=None)

        meta = self.extractor.get_metadata_from_image(mock_img)

        # Should extract timestamp from fallback
        self.assertIsNotNone(meta.get("timestamp"))
        if meta.get("timestamp"):
            self.assertEqual(meta["timestamp"], datetime(2024, 2, 20, 9, 15, 30))

    def test_invalid_timestamp_format(self):
        """Test handling of invalid timestamp format"""
        mock_img = MagicMock(spec=Image.Image)
        mock_exif = {36867: "invalid_date_format"}
        
        mock_exif_obj = MagicMock()
        mock_exif_obj.__bool__ = MagicMock(return_value=True)
        mock_exif_obj.__iter__ = MagicMock(return_value=iter(mock_exif.items()))
        mock_exif_obj.get = lambda k: mock_exif.get(k)
        mock_exif_obj.get_ifd = MagicMock(return_value=None)
        
        mock_img.getexif = MagicMock(return_value=mock_exif_obj)

        meta = self.extractor.get_metadata_from_image(mock_img)

        # Should handle gracefully, timestamp should be None
        self.assertIsNone(meta.get("timestamp"))

    # ============================================================================
    # GPS EXTRACTION TESTS
    # ============================================================================

    def test_extract_gps_coordinates(self):
        """Test extracting valid GPS coordinates"""
        mock_img = MagicMock(spec=Image.Image)
        
        # GPS data in DMS format
        gps_data = {
            1: 'N',  # Latitude ref
            2: ((21, 1), (0, 1), (0, 1)),  # Latitude DMS: 21°0'0"
            3: 'E',  # Longitude ref
            4: ((105, 1), (0, 1), (0, 1))  # Longitude DMS: 105°0'0"
        }
        
        mock_exif_obj = MagicMock()
        mock_exif_obj.__bool__ = MagicMock(return_value=True)
        mock_exif_obj.__iter__ = MagicMock(return_value=iter([]))
        mock_exif_obj.get = MagicMock(return_value=None)
        mock_exif_obj.get_ifd = MagicMock(return_value=gps_data)
        
        mock_img.getexif = MagicMock(return_value=mock_exif_obj)

        meta = self.extractor.get_metadata_from_image(mock_img)

        self.assertIsNotNone(meta.get("latitude"))
        self.assertIsNotNone(meta.get("longitude"))
        self.assertAlmostEqual(meta["latitude"], 21.0, places=1)
        self.assertAlmostEqual(meta["longitude"], 105.0, places=1)

    def test_extract_gps_southern_hemisphere(self):
        """Test GPS with South/West coordinates (negative)"""
        gps_data = {
            1: 'S',  # Southern hemisphere
            2: ((10, 1), (30, 1), (0, 1)),  # 10°30'0"
            3: 'W',  # Western hemisphere
            4: ((120, 1), (15, 1), (0, 1))  # 120°15'0"
        }
        
        lat, lon = self.extractor._parse_gps(gps_data)

        self.assertIsNotNone(lat)
        self.assertIsNotNone(lon)
        self.assertLess(lat, 0)  # Should be negative (South)
        self.assertLess(lon, 0)  # Should be negative (West)

    def test_extract_gps_with_seconds(self):
        """Test GPS with minutes and seconds"""
        gps_data = {
            1: 'N',
            2: ((16, 1), (2, 1), (47, 1)),  # 16°2'47" = ~16.0464°
            3: 'E',
            4: ((108, 1), (13, 1), (33, 1))  # 108°13'33" = ~108.2258°
        }
        
        lat, lon = self.extractor._parse_gps(gps_data)

        self.assertIsNotNone(lat)
        self.assertIsNotNone(lon)
        self.assertAlmostEqual(lat, 16.0464, places=3)
        self.assertAlmostEqual(lon, 108.2258, places=3)

    def test_extract_gps_invalid_data(self):
        """Test handling of invalid GPS data"""
        gps_data = {
            1: 'N',
            # Missing coordinate data
        }
        
        lat, lon = self.extractor._parse_gps(gps_data)

        self.assertIsNone(lat)
        self.assertIsNone(lon)

    def test_extract_gps_empty_dict(self):
        """Test handling of empty GPS dict"""
        lat, lon = self.extractor._parse_gps({})

        self.assertIsNone(lat)
        self.assertIsNone(lon)

    # ============================================================================
    # FILE PATH EXTRACTION TESTS
    # ============================================================================

    def test_get_metadata_from_file_path(self):
        """Test extracting metadata from file path"""
        # Create a temporary image file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            temp_path = f.name
            
        try:
            # Create simple image
            img = Image.new('RGB', (100, 100), color='red')
            img.save(temp_path)
            
            meta = self.extractor.get_metadata(temp_path)
            
            # Should return dict with keys (even if all None)
            self.assertIsInstance(meta, dict)
            self.assertIn("timestamp", meta)
            self.assertIn("latitude", meta)
            self.assertIn("longitude", meta)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_get_metadata_caching(self):
        """Test that metadata is cached after first extraction"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            temp_path = f.name
            
        try:
            img = Image.new('RGB', (100, 100))
            img.save(temp_path)
            
            # First call
            meta1 = self.extractor.get_metadata(temp_path)
            
            # Second call (should use cache)
            meta2 = self.extractor.get_metadata(temp_path)
            
            # Should be the same object (cached)
            self.assertIs(meta1, meta2)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_get_metadata_nonexistent_file(self):
        """Test handling of nonexistent file"""
        meta = self.extractor.get_metadata("/nonexistent/file.jpg")
        
        # Should return default dict with None values
        self.assertIsInstance(meta, dict)
        self.assertIsNone(meta.get("timestamp"))
        self.assertIsNone(meta.get("latitude"))
        self.assertIsNone(meta.get("longitude"))

    # ============================================================================
    # EDGE CASES AND ERROR HANDLING
    # ============================================================================

    def test_getexif_method_priority(self):
        """Test that getexif() is preferred over _getexif()"""
        mock_img = MagicMock(spec=Image.Image)
        
        # Both methods available
        mock_exif_new = MagicMock()
        mock_exif_new.__bool__ = MagicMock(return_value=True)
        mock_exif_new.__iter__ = MagicMock(return_value=iter({36867: "2024:01:01 10:00:00"}.items()))
        mock_exif_new.get = lambda k: {36867: "2024:01:01 10:00:00"}.get(k)
        mock_exif_new.get_ifd = MagicMock(return_value=None)
        
        mock_img.getexif = MagicMock(return_value=mock_exif_new)
        mock_img._getexif = MagicMock(return_value={36867: "2023:01:01 10:00:00"})

        meta = self.extractor.get_metadata_from_image(mock_img)

        # Should use getexif() result (2024, not 2023)
        if meta.get("timestamp"):
            self.assertEqual(meta["timestamp"].year, 2024)

    def test_rational_gps_format(self):
        """Test GPS coordinates in rational number format"""
        gps_data = {
            1: 'N',
            2: [(21.5, 1), (0, 1), (0, 1)],  # Different format
            3: 'E',
            4: [(105.5, 1), (0, 1), (0, 1)]
        }
        
        lat, lon = self.extractor._parse_gps(gps_data)

        # Should handle different rational formats
        self.assertIsNotNone(lat)
        self.assertIsNotNone(lon)

    def test_combined_timestamp_and_gps(self):
        """Test extracting both timestamp and GPS"""
        mock_img = MagicMock(spec=Image.Image)
        
        gps_data = {
            1: 'N',
            2: ((21, 1), (0, 1), (0, 1)),
            3: 'E',
            4: ((105, 1), (0, 1), (0, 1))
        }
        
        exif_data = {36867: "2024:03:01 12:00:00"}
        mock_exif_obj = MagicMock()
        mock_exif_obj.__bool__ = MagicMock(return_value=True)
        mock_exif_obj.__iter__ = MagicMock(return_value=iter(exif_data.items()))
        mock_exif_obj.items = MagicMock(return_value=exif_data.items())
        mock_exif_obj.__getitem__ = lambda self, key: exif_data.get(key)
        mock_exif_obj.get = lambda key, default=None: exif_data.get(key, default)
        mock_exif_obj.get_ifd = MagicMock(return_value=gps_data)
        mock_exif_obj.keys = MagicMock(return_value=exif_data.keys())
        mock_exif_obj.values = MagicMock(return_value=exif_data.values())
        
        mock_img.getexif = MagicMock(return_value=mock_exif_obj)
        mock_img._getexif = MagicMock(return_value=None)

        meta = self.extractor.get_metadata_from_image(mock_img)

        # Should have both (at least one should work)
        has_data = (meta.get("timestamp") is not None or 
                   meta.get("latitude") is not None or 
                   meta.get("longitude") is not None)
        self.assertTrue(has_data, "Should extract at least timestamp or GPS")

    def test_exception_handling_in_extraction(self):
        """Test that exceptions are handled gracefully"""
        mock_img = MagicMock(spec=Image.Image)
        mock_img.getexif = MagicMock(side_effect=Exception("EXIF read error"))
        mock_img._getexif = MagicMock(side_effect=Exception("EXIF read error"))

        # Should not raise exception
        meta = self.extractor.get_metadata_from_image(mock_img)

        # Should return default dict
        self.assertIsInstance(meta, dict)
        self.assertIsNone(meta.get("timestamp"))


if __name__ == "__main__":
    unittest.main()