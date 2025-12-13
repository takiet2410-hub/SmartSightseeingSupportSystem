import unittest
from unittest.mock import patch, MagicMock, Mock
import sys
import os
import torch
from PIL import Image

# Cấu hình đường dẫn
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import shared_resources

class TestSharedResources(unittest.TestCase):

    def setUp(self):
        print("\n" + "-"*60)
        shared_resources.db = None
        shared_resources.client = None
        shared_resources.model = None
        shared_resources.processor = None

    # =================================================================
    # 1. TEST CLASS MODEL WRAPPER
    # =================================================================
    @patch('shared_resources.Dinov2Model')
    def test_01_fine_tuned_dinov2_init(self, mock_dinov2):
        """Test khởi tạo class FineTunedDINOv2 wrapper."""
        print("➤ [TEST 01] Kiểm tra khởi tạo FineTunedDINOv2...")
        
        mock_backbone = Mock()
        mock_dinov2.from_pretrained.return_value = mock_backbone
        
        model_instance = shared_resources.FineTunedDINOv2()
        
        self.assertIsInstance(model_instance, torch.nn.Module)
        print("   ✔ PASSED: Class khởi tạo thành công.")

    # =================================================================
    # 2. TEST LOAD RESOURCES
    # =================================================================
    @patch('shared_resources.MongoClient')
    @patch('shared_resources.torch.load')
    @patch('shared_resources.os.path.exists')
    @patch('shared_resources.FineTunedDINOv2') 
    @patch('shared_resources.AutoImageProcessor')
    def test_02_load_resources_success(self, mock_processor, mock_cls, mock_exists, mock_torch_load, mock_mongo):
        """Test load_resources chạy thành công (Happy Path)."""
        print("➤ [TEST 02] Kiểm tra load_resources (Success Case)...")

        # --- [SỬA QUAN TRỌNG] Dùng MagicMock để hỗ trợ cú pháp client['db_name'] ---
        mock_client_instance = MagicMock() 
        mock_db_instance = MagicMock()
        
        # Cấu hình: MongoClient() -> trả về client giả
        mock_mongo.return_value = mock_client_instance
        # Cấu hình: client['tên_db'] -> trả về db giả
        mock_client_instance.__getitem__.return_value = mock_db_instance
        
        # Mock file model
        mock_exists.return_value = True 
        mock_checkpoint = {"model_state_dict": {"module.layer1": 1}}
        mock_torch_load.return_value = mock_checkpoint
        
        mock_model_instance = Mock()
        mock_cls.return_value = mock_model_instance

        # --- ACTION ---
        shared_resources.load_resources()

        # --- ASSERT ---
        self.assertIsNotNone(shared_resources.db)
        self.assertIsNotNone(shared_resources.client)
        
        # Kiểm tra lệnh tạo index (truy cập qua chuỗi magic mock)
        # db['collection'].create_index(...)
        mock_db_instance.__getitem__.return_value.create_index.assert_called()

        self.assertIsNotNone(shared_resources.model)
        print("   ✔ PASSED: DB connected & Model loaded.")

    @patch('shared_resources.MongoClient')
    def test_03_load_resources_db_fail(self, mock_mongo):
        """Test load_resources khi kết nối DB thất bại."""
        print("➤ [TEST 03] Kiểm tra load_resources (DB Fail)...")
        
        mock_mongo.side_effect = Exception("Connection Timeout")

        shared_resources.load_resources()

        self.assertIsNone(shared_resources.db)
        print("   ✔ PASSED: App handled DB error gracefully.")

    @patch('shared_resources.MongoClient')
    @patch('shared_resources.FineTunedDINOv2')
    def test_04_load_resources_model_fail(self, mock_cls, mock_mongo):
        """Test load_resources khi load Model thất bại."""
        print("➤ [TEST 04] Kiểm tra load_resources (Model Fail)...")

        # --- [SỬA QUAN TRỌNG] Dùng MagicMock ---
        # Nếu dùng Mock thường, dòng db = client[DB_NAME] sẽ lỗi TypeError
        mock_mongo.return_value = MagicMock()
        
        # Mock Model thất bại
        mock_cls.side_effect = Exception("CUDA Out of memory")

        shared_resources.load_resources()

        self.assertIsNotNone(shared_resources.db) # DB phải OK
        self.assertIsNone(shared_resources.model) # Model phải None
        print("   ✔ PASSED: DB OK, Model Failed (Correct behavior).")

    # =================================================================
    # 3. TEST EMBED IMAGE
    # =================================================================
    def test_05_embed_image_success(self):
        """Test hàm embed_image tạo ra vector."""
        print("➤ [TEST 05] Kiểm tra embed_image (Success)...")

        mock_model = Mock()
        mock_processor = Mock()
        shared_resources.model = mock_model
        shared_resources.processor = mock_processor
        shared_resources.DEVICE = "cpu"

        mock_output = torch.rand(1, 768) 
        mock_model.return_value = mock_output
        
        mock_processor_output = Mock()
        mock_processor_output.pixel_values = torch.zeros(1, 3, 224, 224)
        mock_processor.return_value = mock_processor_output

        result = shared_resources.embed_image(Image.new('RGB', (100, 100)))

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 768)
        print("   ✔ PASSED: Embed OK.")

    def test_06_embed_image_no_model(self):
        """Test embed_image báo lỗi khi model chưa load."""
        print("➤ [TEST 06] Kiểm tra embed_image (Model not loaded)...")
        shared_resources.model = None
        with self.assertRaises(RuntimeError):
            shared_resources.embed_image(Image.new('RGB', (10, 10)))
        print("   ✔ PASSED: RuntimeError raised.")

    # =================================================================
    # 4. TEST VECTOR SEARCH
    # =================================================================
    def test_07_search_similar_landmark_success(self):
        """Test hàm search gọi MongoDB aggregation đúng cách."""
        print("➤ [TEST 07] Kiểm tra search_similar_landmark (Aggregation)...")

        # --- [SỬA QUAN TRỌNG] Dùng MagicMock cho DB ---
        mock_db = MagicMock() 
        mock_col = MagicMock()
        
        # Cấu hình: db['collection_name'] -> trả về collection giả
        mock_db.__getitem__.return_value = mock_col 
        shared_resources.db = mock_db
        
        mock_results = [{"landmark_id": "123", "score": 0.9}]
        mock_col.aggregate.return_value = mock_results

        dummy_vector = [0.1] * 768
        result = shared_resources.search_similar_landmark(dummy_vector, "my_collection")

        self.assertEqual(result, mock_results)
        
        mock_col.aggregate.assert_called_once()
        print("   ✔ PASSED: Aggregation called correctly.")

    def test_08_search_no_db(self):
        """Test search báo lỗi khi DB chưa kết nối."""
        print("➤ [TEST 08] Kiểm tra search_similar_landmark (No DB)...")
        shared_resources.db = None
        with self.assertRaises(RuntimeError):
            shared_resources.search_similar_landmark([], "col")
        print("   ✔ PASSED: RuntimeError raised.")

if __name__ == '__main__':
    unittest.main(verbosity=2)