import unittest
from unittest.mock import patch, MagicMock, ANY
from fastapi.testclient import TestClient
from fastapi import FastAPI
import sys
import os
import io
from PIL import Image

# --- CẤU HÌNH ĐƯỜNG DẪN ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import router cần test
from visual_search import router
from auth_deps import get_current_user_id
import shared_resources

# Tạo một App giả để gắn router vào test
app = FastAPI()
app.include_router(router)

class TestVisualSearchEndpoint(unittest.TestCase):

    def setUp(self):
        print("\n" + "-"*70)
        self.client = TestClient(app)
        
        # 1. Tạo ảnh giả (Valid Image Bytes) để upload
        img = Image.new('RGB', (100, 100), color='red')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        self.valid_image_bytes = img_byte_arr.getvalue()

        # 2. Reset dependency overrides (để mặc định là chưa login)
        app.dependency_overrides = {}

    def tearDown(self):
        # Clear overrides sau mỗi test
        app.dependency_overrides = {}

    # =================================================================
    # 1. TEST CÁC LỖI HỆ THỐNG (503, 400, 500)
    # =================================================================

    def test_01_service_unavailable(self):
        """Test lỗi 503 khi Model hoặc DB chưa sẵn sàng."""
        print("➤ [TEST 01] Kiểm tra Service Unavailable (Model/DB is None)...")
        
        # Giả lập model bị None
        shared_resources.model = None
        
        files = {"file": ("test.jpg", self.valid_image_bytes, "image/jpeg")}
        response = self.client.post("/visual-search", files=files)
        
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "Model service is currently unavailable.")
        print("   ✔ PASSED: Trả về 503 khi resource thiếu.")

    def test_02_invalid_image_file(self):
        """Test lỗi 400 khi file gửi lên không phải ảnh."""
        print("➤ [TEST 02] Kiểm tra lỗi file upload không hợp lệ...")
        
        # Mock resource sẵn sàng
        shared_resources.model = MagicMock()
        shared_resources.db = MagicMock()

        # Gửi file text thay vì ảnh
        files = {"file": ("test.txt", b"Day la file text", "text/plain")}
        response = self.client.post("/visual-search", files=files)

        self.assertEqual(response.status_code, 400)
        print("   ✔ PASSED: Trả về 400 khi file lỗi.")

    @patch('shared_resources.embed_image')
    def test_03_search_exception(self, mock_embed):
        """Test lỗi 500 khi quá trình search gặp Exception."""
        print("➤ [TEST 03] Kiểm tra lỗi 500 khi xử lý search thất bại...")
        
        shared_resources.model = MagicMock()
        shared_resources.db = MagicMock()
        
        # Giả lập hàm embed ném lỗi
        mock_embed.side_effect = Exception("CUDA Error")

        files = {"file": ("test.jpg", self.valid_image_bytes, "image/jpeg")}
        response = self.client.post("/visual-search", files=files)

        self.assertEqual(response.status_code, 500)
        self.assertIn("Processing or search failed", response.json()["detail"])
        print("   ✔ PASSED: Trả về 500 khi code ném Exception.")

    # =================================================================
    # 2. TEST LOGIC NGHIỆP VỤ (Happy Paths & Not Found)
    # =================================================================
    
    @patch('visual_search.add_temp_record')
    @patch('visual_search.add_history_record')
    @patch('shared_resources.search_similar_landmark')
    @patch('shared_resources.embed_image')
    def test_04_not_found_low_score(self, mock_embed, mock_search, mock_add_hist, mock_add_temp):
        """Test trường hợp tìm thấy nhưng độ tin cậy thấp (< 0.6)."""
        print("➤ [TEST 04] Kiểm tra kết quả Not Found (Low Confidence)...")
        
        shared_resources.model = MagicMock()
        shared_resources.db = MagicMock()
        mock_embed.return_value = [0.1] * 768
        
        # Giả lập kết quả search có score thấp
        mock_search.return_value = [{"landmark_id": "lm1", "score": 0.4}] # < 0.6

        files = {"file": ("test.jpg", self.valid_image_bytes, "image/jpeg")}
        response = self.client.post("/visual-search", files=files)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "not_found")
        
        # Đảm bảo KHÔNG gọi hàm lưu lịch sử nào
        mock_add_hist.assert_not_called()
        mock_add_temp.assert_not_called()
        print("   ✔ PASSED: Trả về 'not_found' và không lưu lịch sử.")

    @patch('visual_search.add_history_record') # Mock hàm lưu lịch sử user
    @patch('visual_search.add_temp_record')    # Mock hàm lưu lịch sử temp
    @patch('shared_resources.search_similar_landmark')
    @patch('shared_resources.embed_image')
    def test_05_success_logged_in_user(self, mock_embed, mock_search, mock_add_temp, mock_add_hist):
        """Test user ĐÃ LOGIN -> Lưu vào User History."""
        print("➤ [TEST 05] Kiểm tra thành công: User ĐÃ LOGIN...")

        # 1. Giả lập User đã login (Override Dependency)
        app.dependency_overrides[get_current_user_id] = lambda: "user_123"

        # 2. Mock Resources
        shared_resources.model = MagicMock()
        # Mock DB trả về metadata
        mock_db = MagicMock()
        mock_col = MagicMock()
        mock_col.find_one.return_value = {"name": "Eiffel Tower", "desc": "Paris"}
        mock_db.__getitem__.return_value = mock_col
        shared_resources.db = mock_db

        # 3. Mock Search Result (High Score)
        mock_embed.return_value = [0.1] * 768
        mock_search.return_value = [{"landmark_id": "lm_eiffel", "score": 0.95, "image_url": "url1"}]

        # 4. Action
        files = {"file": ("test.jpg", self.valid_image_bytes, "image/jpeg")}
        response = self.client.post("/visual-search", files=files)

        # 5. Assertions
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["landmark_id"], "lm_eiffel")

        # [QUAN TRỌNG] Kiểm tra add_history_record được gọi, còn add_temp thì KHÔNG
        mock_add_hist.assert_called_once()
        mock_add_temp.assert_not_called()
        
        # Kiểm tra tham số gọi hàm add_history_record
        # args[0] là user_id, kwargs check landmark_name
        call_kwargs = mock_add_hist.call_args.kwargs
        self.assertEqual(call_kwargs['user_id'], "user_123")
        self.assertEqual(call_kwargs['landmark_name'], "Eiffel Tower")
        
        print("   ✔ PASSED: Đã gọi add_history_record cho user_123.")

    @patch('visual_search.add_history_record')
    @patch('visual_search.add_temp_record')
    @patch('shared_resources.search_similar_landmark')
    @patch('shared_resources.embed_image')
    def test_06_success_anonymous_new_temp(self, mock_embed, mock_search, mock_add_temp, mock_add_hist):
        """Test user ẨN DANH (Chưa có Temp ID) -> Tạo Temp ID mới."""
        print("➤ [TEST 06] Kiểm tra thành công: User ẨN DANH (New Session)...")

        # 1. User chưa login (Dependency trả về None)
        app.dependency_overrides[get_current_user_id] = lambda: None

        # 2. Mock Resources & DB (Giống test 05)
        shared_resources.model = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__.return_value.find_one.return_value = {"name": "Big Ben"}
        shared_resources.db = mock_db
        
        mock_embed.return_value = [0.2] * 768
        mock_search.return_value = [{"landmark_id": "lm_bigben", "score": 0.96}]

        # 3. Action (Không gửi Header X-Temp-ID)
        files = {"file": ("test.jpg", self.valid_image_bytes, "image/jpeg")}
        response = self.client.post("/visual-search", files=files)

        # 4. Assertions
        data = response.json()
        self.assertEqual(data["status"], "success")
        
        # Kiểm tra Temp ID được sinh ra
        self.assertIsNotNone(data["temp_id"])
        print(f"      -> Generated Temp ID: {data['temp_id']}")

        # [QUAN TRỌNG] Kiểm tra add_temp_record được gọi
        mock_add_temp.assert_called_once()
        mock_add_hist.assert_not_called()
        
        print("   ✔ PASSED: Đã tạo Temp ID mới và gọi add_temp_record.")

    @patch('visual_search.add_history_record')
    @patch('visual_search.add_temp_record')
    @patch('shared_resources.search_similar_landmark')
    @patch('shared_resources.embed_image')
    def test_07_success_anonymous_existing_temp(self, mock_embed, mock_search, mock_add_temp, mock_add_hist):
        """Test user ẨN DANH (Đã có Temp ID gửi lên) -> Dùng lại ID đó."""
        print("➤ [TEST 07] Kiểm tra thành công: User ẨN DANH (Existing Session)...")

        app.dependency_overrides[get_current_user_id] = lambda: None
        
        # Mock Resources (vẫn cần để code chạy qua đoạn search)
        shared_resources.model = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__.return_value.find_one.return_value = {"name": "Tokyo Tower"}
        shared_resources.db = mock_db
        mock_search.return_value = [{"landmark_id": "lm_tokyo", "score": 0.9}]

        # 3. Action: Gửi kèm Header X-Temp-ID
        existing_id = "my-existing-uuid-999"
        headers = {"X-Temp-ID": existing_id}
        files = {"file": ("test.jpg", self.valid_image_bytes, "image/jpeg")}
        
        response = self.client.post("/visual-search", files=files, headers=headers)

        # 4. Assertions
        data = response.json()
        
        # Temp ID trả về phải trùng với cái gửi lên
        self.assertEqual(data["temp_id"], existing_id)

        # Kiểm tra add_temp_record được gọi đúng ID
        mock_add_temp.assert_called_once()
        call_kwargs = mock_add_temp.call_args.kwargs
        self.assertEqual(call_kwargs['temp_id'], existing_id)

        print(f"   ✔ PASSED: Đã lưu vào Temp History với ID cũ: {existing_id}")

if __name__ == '__main__':
    unittest.main(verbosity=2)