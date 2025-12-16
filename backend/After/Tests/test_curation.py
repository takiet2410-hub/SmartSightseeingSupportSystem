import unittest
from curation_service import CurationService
from PIL import Image
import numpy as np


class TestCuration(unittest.TestCase):

    def setUp(self):
        self.curator = CurationService()

    def test_calculate_score_returns_float(self):
        """Test that score calculation returns valid float"""
        img_array = np.random.randint(0, 255, (512, 512, 3), dtype=np.uint8)
        img = Image.fromarray(img_array)

        score = self.curator.calculate_score(img)

        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_sharp_image_scores_higher(self):
        """Test that sharp images score higher than blurry ones"""
        sharp_img = np.zeros((512, 512, 3), dtype=np.uint8)
        sharp_img[100:400, 100:400] = 255
        sharp_img = Image.fromarray(sharp_img)

        blurry_img = np.full((512, 512, 3), 128, dtype=np.uint8)
        blurry_img = Image.fromarray(blurry_img)

        sharp_score = self.curator.calculate_score(sharp_img)
        blurry_score = self.curator.calculate_score(blurry_img)

        self.assertGreater(sharp_score, blurry_score)


if __name__ == "__main__":
    unittest.main()