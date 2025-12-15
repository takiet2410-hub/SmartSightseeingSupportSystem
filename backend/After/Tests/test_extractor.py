import unittest
from unittest.mock import Mock, MagicMock
from PIL import Image
from metadata import MetadataExtractor


class TestImageExtraction(unittest.TestCase):

    def setUp(self):
        self.extractor = MetadataExtractor()

    def test_extract_metadata_no_exif(self):
        """Test extracting metadata from image with no EXIF"""
        mock_img = MagicMock(spec=Image.Image)
        mock_img._getexif = MagicMock(return_value=None)

        meta = self.extractor.get_metadata_from_image(mock_img)

        self.assertIsNone(meta.get("timestamp"))
        self.assertIsNone(meta.get("latitude"))
        self.assertIsNone(meta.get("longitude"))

    def test_metadata_extractor_returns_dict(self):
        """Test that metadata extractor returns a dictionary"""
        mock_img = MagicMock(spec=Image.Image)
        mock_img._getexif = MagicMock(return_value={})

        meta = self.extractor.get_metadata_from_image(mock_img)

        self.assertIsInstance(meta, dict)