import unittest
from unittest.mock import Mock, patch
from filters.junk_detector import has_camera_model, is_junk, is_junk_batch, get_model
from PIL import Image
import numpy as np
import tempfile
import os


class TestJunkDetector(unittest.TestCase):

    def test_has_camera_model_without_exif(self):
        """Test image without camera model (screenshot/meme)"""
        img = Image.new('RGB', (100, 100), color='red')
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            temp_path = f.name
            img.save(temp_path)
        
        try:
            result = has_camera_model(temp_path)
            self.assertFalse(result)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_has_camera_model_invalid_values(self):
        """Test rejection of invalid camera model values"""
        mock_img = Mock(spec=Image.Image)
        mock_img.getexif.return_value = {
            271: "Unknown",
            272: "N/A"
        }
        
        with patch('filters.junk_detector.Image.open', return_value=mock_img):
            result = has_camera_model('fake_path.jpg')
            self.assertFalse(result)

    @patch('filters.junk_detector.get_model')
    def test_is_junk_batch_no_camera_model(self, mock_get_model):
        """Test Stage 1: Images without camera model are marked as junk"""
        test_images = []
        for i in range(3):
            img = Image.new('RGB', (100, 100))
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                temp_path = f.name
                img.save(temp_path)
                test_images.append(temp_path)
        
        try:
            results = is_junk_batch(test_images)
            
            self.assertEqual(len(results), 3)
            self.assertTrue(all(results))
            
            mock_get_model.assert_not_called()
        finally:
            for path in test_images:
                if os.path.exists(path):
                    os.unlink(path)

    @patch('filters.junk_detector.get_model')
    @patch('filters.junk_detector.has_camera_model')
    def test_is_junk_batch_with_camera_model(self, mock_has_camera, mock_get_model):
        """Test Stage 2: Images with camera model go to AI check"""
        mock_has_camera.return_value = True
        
        mock_model = Mock()
        mock_model.predict.return_value = np.array([[0.9], [0.7], [0.85]])
        mock_get_model.return_value = mock_model
        
        test_images = []
        for i in range(3):
            img = Image.new('RGB', (224, 224))
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                temp_path = f.name
                img.save(temp_path)
                test_images.append(temp_path)
        
        try:
            results = is_junk_batch(test_images)
            
            self.assertEqual(len(results), 3)
            self.assertFalse(results[0])
            self.assertTrue(results[1])
            self.assertFalse(results[2])
            
            mock_get_model.assert_called()
            mock_model.predict.assert_called_once()
        finally:
            for path in test_images:
                if os.path.exists(path):
                    os.unlink(path)

    @patch('filters.junk_detector.get_model')
    @patch('filters.junk_detector.has_camera_model')
    def test_is_junk_batch_model_failure(self, mock_has_camera, mock_get_model):
        """Test graceful handling when AI model fails to load"""
        mock_has_camera.return_value = True
        mock_get_model.return_value = None
        
        test_images = []
        for i in range(2):
            img = Image.new('RGB', (100, 100))
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                temp_path = f.name
                img.save(temp_path)
                test_images.append(temp_path)
        
        try:
            results = is_junk_batch(test_images)
            
            self.assertEqual(len(results), 2)
            self.assertFalse(all(results))
        finally:
            for path in test_images:
                if os.path.exists(path):
                    os.unlink(path)

    @patch('filters.junk_detector.is_junk_batch')
    def test_is_junk_single_image(self, mock_batch):
        """Test single image detection uses batch function"""
        mock_batch.return_value = [True]
        
        result = is_junk('test.jpg')
        
        self.assertTrue(result)
        mock_batch.assert_called_once_with(['test.jpg'])

    @patch('filters.junk_detector.has_camera_model')
    @patch('filters.junk_detector.get_model')
    def test_mixed_batch_camera_check(self, mock_get_model, mock_has_camera):
        """Test mixed batch: some with camera, some without"""
        mock_has_camera.side_effect = [False, True, False]
        
        mock_model = Mock()
        mock_model.predict.return_value = np.array([[0.9]])
        mock_get_model.return_value = mock_model
        
        test_images = []
        for i in range(3):
            img = Image.new('RGB', (224, 224))
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                temp_path = f.name
                img.save(temp_path)
                test_images.append(temp_path)
        
        try:
            results = is_junk_batch(test_images)
            
            self.assertEqual(len(results), 3)
            self.assertTrue(results[0])
            self.assertFalse(results[1])
            self.assertTrue(results[2])
        finally:
            for path in test_images:
                if os.path.exists(path):
                    os.unlink(path)