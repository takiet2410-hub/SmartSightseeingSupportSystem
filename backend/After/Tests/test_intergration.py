import unittest
from filters.lighting import LightingFilter
from filters.junk_detector import is_junk_batch
from PIL import Image
import numpy as np
import tempfile
import os


class TestFilterIntegration(unittest.TestCase):
    """Test how lighting and junk filters work together"""

    def setUp(self):
        self.lighting_filter = LightingFilter()

    def test_full_photo_pipeline(self):
        """Test realistic photo processing pipeline"""
        test_photos = []
        
        # Photo 1: Good lighting
        good_photo = np.full((512, 512, 3), 130, dtype=np.uint8)
        good_img = Image.fromarray(good_photo, 'RGB')
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            good_path = f.name
            good_img.save(good_path)
            test_photos.append(good_path)
        
        # Photo 2: Bad lighting (too dark)
        dark_photo = np.full((512, 512, 3), 20, dtype=np.uint8)
        dark_img = Image.fromarray(dark_photo, 'RGB')
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            dark_path = f.name
            dark_img.save(dark_path)
            test_photos.append(dark_path)
        
        # Photo 3: Screenshot (no camera EXIF)
        screenshot = np.full((512, 512, 3), 130, dtype=np.uint8)
        screenshot_img = Image.fromarray(screenshot, 'RGB')
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            screenshot_path = f.name
            screenshot_img.save(screenshot_path)
            test_photos.append(screenshot_path)
        
        try:
            # Stage 1: Lighting check
            lighting_results = []
            for path in test_photos:
                img = Image.open(path)
                is_good, reason = self.lighting_filter.analyze_from_image(img)
                lighting_results.append(is_good)
                img.close()
            
            self.assertTrue(lighting_results[0])
            self.assertFalse(lighting_results[1])
            self.assertTrue(lighting_results[2])
            
            # Stage 2: Junk detection
            good_photos = [test_photos[i] for i, is_good in enumerate(lighting_results) if is_good]
            junk_results = is_junk_batch(good_photos)
            
            self.assertTrue(junk_results[1])
            
        finally:
            for path in test_photos:
                if os.path.exists(path):
                    os.unlink(path)