import unittest
from filters.lighting import LightingFilter
from PIL import Image
import numpy as np
import tempfile
import os


class TestLightingFilter(unittest.TestCase):

    def setUp(self):
        self.filter = LightingFilter()

    def test_good_lighting_quality(self):
        """Test image with optimal lighting passes"""
        img_array = np.full((512, 512, 3), 130, dtype=np.uint8)
        img = Image.fromarray(img_array, 'RGB')

        is_good, reason = self.filter.analyze_from_image(img)

        self.assertTrue(is_good)
        self.assertEqual(reason, "Good Lighting")

    def test_underexposed_image(self):
        """Test very dark image fails"""
        img_array = np.full((512, 512, 3), 25, dtype=np.uint8)
        img = Image.fromarray(img_array, 'RGB')

        is_good, reason = self.filter.analyze_from_image(img)

        self.assertFalse(is_good)
        self.assertIn("Underexposed", reason)
        self.assertIn("Too Dark", reason)

    def test_overexposed_image(self):
        """Test overexposed image fails"""
        img_array = np.full((512, 512, 3), 240, dtype=np.uint8)
        img = Image.fromarray(img_array, 'RGB')

        is_good, reason = self.filter.analyze_from_image(img)

        self.assertFalse(is_good)
        self.assertIn("Overexposed", reason)
        self.assertIn("Too Bright", reason)

    def test_glare_detection(self):
        """Test image with excessive glare fails"""
        img_array = np.full((512, 512, 3), 120, dtype=np.uint8)
        glare_pixels = int(512 * 512 * 0.4)
        img_array.flat[:glare_pixels*3] = 252
        img = Image.fromarray(img_array, 'RGB')

        is_good, reason = self.filter.analyze_from_image(img)

        self.assertFalse(is_good)
        self.assertIn("Glare", reason)

    def test_analyze_from_disk(self):
        """Test loading and analyzing from disk file"""
        img_array = np.full((512, 512, 3), 130, dtype=np.uint8)
        img = Image.fromarray(img_array, 'RGB')
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            temp_path = f.name
            img.save(temp_path)
        
        try:
            is_good, reason = self.filter.analyze(temp_path)
            self.assertTrue(is_good)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_corrupt_image_from_disk(self):
        """Test that corrupt image file is rejected"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            temp_path = f.name
            f.write(b'not an image')
        
        try:
            is_good, reason = self.filter.analyze(temp_path)
            self.assertFalse(is_good)
            self.assertIn("Corrupt", reason)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_pil_image_mode_conversion(self):
        """Test that non-RGB images are converted properly"""
        img_array = np.full((512, 512), 130, dtype=np.uint8)
        img = Image.fromarray(img_array, 'L')

        is_good, reason = self.filter.analyze_from_image(img)

        self.assertTrue(is_good)

    def test_brightness_thresholds(self):
        """Test exact threshold values"""
        img_min = np.full((512, 512, 3), 41, dtype=np.uint8)
        is_good_min, _ = self.filter.analyze_from_image(Image.fromarray(img_min, 'RGB'))
        self.assertTrue(is_good_min)
        
        img_max = np.full((512, 512, 3), 219, dtype=np.uint8)
        is_good_max, _ = self.filter.analyze_from_image(Image.fromarray(img_max, 'RGB'))
        self.assertTrue(is_good_max)

    def test_realistic_outdoor_photo(self):
        """Test realistic outdoor photo with varied brightness"""
        img_array = np.zeros((512, 512, 3), dtype=np.uint8)
        img_array[0:256, :] = 180
        img_array[256:512, :] = 100
        img = Image.fromarray(img_array, 'RGB')

        is_good, reason = self.filter.analyze_from_image(img)

        self.assertTrue(is_good)