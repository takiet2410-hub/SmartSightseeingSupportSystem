import unittest
from unittest import mock
import sys
import os
import hashlib

# --- CẤU HÌNH ĐƯỜNG DẪN ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import các hàm cần test từ detection_history.py
from detection_history import (
    add_history_record, 
    add_temp_record, 
    sync_temp_history, 
    get_image_hash,
    delete_history_items,   # [NEW] Import hàm xoá
    get_public_id_from_url  # [NEW] Import hàm tách ID
)

# --- DỮ LIỆU GIẢ LẬP (MOCK DATA) ---
TEST_USER_ID = "user_123"
TEST_TEMP_ID = "temp_456"
TEST_LANDMARK = {"landmark_id": "lm_001", "similarity_score": 0.95}
TEST_IMAGE_BYTES = b"fake_image_content"
TEST_IMAGE_HASH = hashlib.md5(TEST_IMAGE_BYTES).hexdigest()
TEST_URL = "http://cloudinary.com/fake_image.jpg"

class TestHistoryManagement(unittest.TestCase):

    def setUp(self):
        print("\n" + "-"*70)

    # ----------------------------------------------------------------
    # 1. TEST CÁC HÀM HELPER VÀ UPLOAD
    # ----------------------------------------------------------------
    def test_01_get_image_hash(self):
        """Test hàm tính mã Hash MD5."""
        print("➤ [TEST 01] Kiểm tra hàm tính Hash MD5...")
        result = get_image_hash(TEST_IMAGE_BYTES)
        self.assertEqual(result, TEST_IMAGE_HASH)
        print(f"   ✔ PASSED: Hash tính ra chính xác: {result}")

    @mock.patch('detection_history.cloudinary.uploader.upload')
    def test_02_upload_fail_handles_exception(self, mock_upload):
        """Test hàm upload ảnh trả về None khi gặp lỗi."""
        print("➤ [TEST 02] Kiểm tra xử lý lỗi khi Upload ảnh thất bại...")
        
        mock_upload.side_effect = Exception("Upload failed")
        from detection_history import upload_image_to_cloud
        result = upload_image_to_cloud(TEST_IMAGE_BYTES)
        
        self.assertIsNone(result)
        print("   ✔ PASSED: Hàm trả về None khi upload gặp lỗi.")

    # ----------------------------------------------------------------
    # 2. TEST LOGIC THÊM LỊCH SỬ (ADD HISTORY)
    # ----------------------------------------------------------------
    @mock.patch('detection_history.shared_resources.db')
    @mock.patch('detection_history.upload_image_to_cloud')
    def test_03_add_history_new_user(self, mock_upload, mock_db):
        """Test thêm lịch sử cho người dùng mới."""
        print("➤ [TEST 03] Kiểm tra thêm record mới cho User chưa tồn tại...")

        mock_upload.return_value = TEST_URL
        mock_col = mock_db["history_collection"]
        mock_col.find_one.return_value = None

        add_history_record(
            user_id=TEST_USER_ID,
            landmark_data=TEST_LANDMARK,
            landmark_name="Eiffel Tower",
            uploaded_image_bytes=TEST_IMAGE_BYTES
        )

        self.assertTrue(mock_col.insert_one.called)
        print("   ✔ PASSED: Đã tạo mới User document.")

    @mock.patch('detection_history.shared_resources.db')
    def test_04_add_history_duplicate(self, mock_db):
        """Test logic chống trùng lặp."""
        print("➤ [TEST 04] Kiểm tra logic Duplicate (trùng hash) -> Move to Top...")

        mock_col = mock_db["history_collection"]
        existing_history = [{
            "landmark_id": "lm_001",
            "name": "Eiffel Tower",
            "user_image_url": TEST_URL,
            "image_hash": TEST_IMAGE_HASH,
            "timestamp": "2023-01-01"
        }, {
            "landmark_id": "lm_002",
            "name": "Big Ben", 
            "timestamp": "2023-01-02"
        }]

        mock_col.find_one.return_value = {"user_id": TEST_USER_ID, "history": existing_history}

        add_history_record(
            user_id=TEST_USER_ID,
            landmark_data=TEST_LANDMARK,
            landmark_name="Eiffel Tower",
            uploaded_image_bytes=TEST_IMAGE_BYTES
        )

        self.assertTrue(mock_col.update_one.called)
        args, _ = mock_col.update_one.call_args
        updated_history = args[1]['$set']['history']
        
        self.assertEqual(updated_history[0]['landmark_id'], "lm_001")
        self.assertNotEqual(updated_history[0]['timestamp'], "2023-01-01")
        
        print("   ✔ PASSED: Record trùng lặp đã được đưa lên đầu danh sách.")

    # ----------------------------------------------------------------
    # 3. TEST LOGIC SYNC (TEMP -> MAIN)
    # ----------------------------------------------------------------
    @mock.patch('detection_history.add_history_record')
    @mock.patch('detection_history.shared_resources.db')
    def test_05_sync_temp_history_success(self, mock_db, mock_add_record):
        """Test API Sync."""
        print("➤ [TEST 05] Kiểm tra API Sync từ Temp sang History chính...")

        mock_temp_col = mock_db["temp_history_collection"]
        temp_data = {
            "temp_id": TEST_TEMP_ID,
            "history": [
                {"landmark_id": "lm_A", "name": "A", "similarity_score": 0.9, "timestamp": "t1", "user_image_url": "u1", "image_hash": "h1"},
                {"landmark_id": "lm_B", "name": "B", "similarity_score": 0.8, "timestamp": "t2", "user_image_url": "u2", "image_hash": "h2"}
            ]
        }
        mock_temp_col.find_one.return_value = temp_data

        result = sync_temp_history(temp_id=TEST_TEMP_ID, user_id=TEST_USER_ID)

        self.assertEqual(mock_add_record.call_count, 2)
        mock_temp_col.delete_one.assert_called_once_with({"temp_id": TEST_TEMP_ID})
        self.assertEqual(result["status"], "synced")
        
        print("   ✔ PASSED: Đã sync thành công và xóa temp data.")

    @mock.patch('detection_history.shared_resources.db')
    def test_06_sync_no_data(self, mock_db):
        """Test Sync khi không có dữ liệu."""
        print("➤ [TEST 06] Kiểm tra Sync khi không có dữ liệu tạm...")

        mock_temp_col = mock_db["temp_history_collection"]
        mock_temp_col.find_one.return_value = None

        result = sync_temp_history(temp_id="invalid_id", user_id=TEST_USER_ID)

        self.assertEqual(result["status"], "no_data")
        print("   ✔ PASSED: API trả về thông báo 'no_data'.")

    # ----------------------------------------------------------------
    # [NEW] 4. TEST CÁC CHỨC NĂNG XOÁ VÀ TÁCH ID
    # ----------------------------------------------------------------
    def test_07_get_public_id_from_url(self):
        """Test helper tách Public ID từ URL Cloudinary."""
        print("➤ [TEST 07] Kiểm tra hàm tách Public ID từ URL...")
        
        # Case 1: URL chuẩn có version
        url1 = "https://res.cloudinary.com/demo/image/upload/v123456/folder/sample.jpg"
        self.assertEqual(get_public_id_from_url(url1), "folder/sample")

        # Case 2: URL không có folder
        url2 = "https://res.cloudinary.com/demo/image/upload/v123456/sample.png"
        self.assertEqual(get_public_id_from_url(url2), "sample")

        # Case 3: URL không phải Cloudinary
        url3 = "https://google.com/image.jpg"
        self.assertIsNone(get_public_id_from_url(url3))

        print("   ✔ PASSED: Hàm tách Public ID hoạt động chính xác các trường hợp.")

    @mock.patch('detection_history.cloudinary.uploader.destroy')
    @mock.patch('detection_history.shared_resources.db')
    def test_08_delete_history_success(self, mock_db, mock_destroy):
        """Test API Xoá (Success): Xoá Cloudinary và DB thành công."""
        print("➤ [TEST 08] Kiểm tra API Xoá thành công...")

        # Setup Mock Cloudinary trả về "ok"
        mock_destroy.return_value = {"result": "ok"}

        # Setup Mock DB
        mock_col = mock_db["history_collection"]
        # Mock kết quả trả về của update_one (deleted count)
        mock_result = mock.Mock()
        mock_result.modified_count = 1
        mock_col.update_one.return_value = mock_result

        # Input
        urls_to_delete = [
            "https://res.cloudinary.com/demo/image/upload/v1/img1.jpg",
            "https://res.cloudinary.com/demo/image/upload/v1/img2.jpg"
        ]

        # Action
        result = delete_history_items(image_urls=urls_to_delete, user_id=TEST_USER_ID)

        # Assertion 1: Cloudinary destroy được gọi 2 lần
        self.assertEqual(mock_destroy.call_count, 2)
        
        # Assertion 2: DB update_one ($pull) được gọi đúng query
        self.assertTrue(mock_col.update_one.called)
        args, _ = mock_col.update_one.call_args
        # Kiểm tra query filter có đúng user_id không
        self.assertEqual(args[0]['user_id'], TEST_USER_ID)
        # Kiểm tra lệnh $pull có chứa danh sách url không
        pull_query = args[1]['$pull']['history']['user_image_url']['$in']
        self.assertEqual(pull_query, urls_to_delete)

        # Assertion 3: Kết quả trả về
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["deleted_cloud_images"], 2) # Xoá được 2 ảnh trên cloud
        
        print("   ✔ PASSED: Đã gọi lệnh xoá Cloud và xoá DB chính xác.")

    @mock.patch('detection_history.cloudinary.uploader.destroy')
    @mock.patch('detection_history.shared_resources.db')
    def test_09_delete_history_partial_cloud_fail(self, mock_db, mock_destroy):
        """Test API Xoá: Cloudinary lỗi 1 ảnh, nhưng DB vẫn phải xoá."""
        print("➤ [TEST 09] Kiểm tra API Xoá khi Cloudinary gặp lỗi...")

        # Setup Mock: Lần 1 OK, Lần 2 Exception
        mock_destroy.side_effect = [{"result": "ok"}, Exception("Network Error")]

        mock_col = mock_db["history_collection"]
        mock_result = mock.Mock()
        mock_result.modified_count = 1
        mock_col.update_one.return_value = mock_result

        # [SỬA LẠI] Dùng URL giả nhưng đúng định dạng Cloudinary để vượt qua check của get_public_id_from_url
        urls_to_delete = [
            "https://res.cloudinary.com/demo/image/upload/v1/ok.jpg",   # Link 1 (Sẽ xoá OK)
            "https://res.cloudinary.com/demo/image/upload/v1/fail.jpg"  # Link 2 (Sẽ gây lỗi Exception)
        ]

        # Action
        result = delete_history_items(image_urls=urls_to_delete, user_id=TEST_USER_ID)

        # Assertion
        self.assertTrue(mock_col.update_one.called)
        
        # deleted_cloud_images = 1 (vì ảnh 1 xoá được, ảnh 2 bị lỗi exception nên không tính)
        self.assertEqual(result["deleted_cloud_images"], 1)
        self.assertEqual(result["status"], "success")

        print("   ✔ PASSED: Hệ thống vẫn xoá DB và đếm đúng số lượng ảnh cloud đã xoá được.")

if __name__ == '__main__':
    unittest.main(verbosity=2)