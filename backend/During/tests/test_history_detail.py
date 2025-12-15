import unittest
from unittest import mock
from fastapi import HTTPException
import sys
import os

# --- CẤU HÌNH ĐƯỜNG DẪN ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from history_detail import history_summary, history_detail

# --- DỮ LIỆU TEST GIẢ LẬP ---
TEST_USER_ID = "user_123"
TEST_LANDMARK_ID = "lm_eiffel"
TEST_COLLECTION_HISTORY = "history_collection"
TEST_COLLECTION_BEFORE = "before_collection"

# Mock data trả về từ database
MOCK_USER_HISTORY_DOC = {
    "user_id": TEST_USER_ID,
    "history": [
        {
            "landmark_id": TEST_LANDMARK_ID,
            "name": "Eiffel Tower",
            "user_image_url": "http://cloud.com/user_img.jpg",
            "timestamp": "2023-01-01T10:00:00",
            "similarity_score": 0.98
        },
        {
            "landmark_id": "lm_other",
            "name": "Other Place",
            "user_image_url": "http://cloud.com/other.jpg",
            "timestamp": "2023-01-02T10:00:00"
        }
    ]
}

MOCK_METADATA_DOC = {
    "landmark_id": TEST_LANDMARK_ID,
    "name": "Eiffel Tower",
    "summary": "A famous tower in Paris.",
    "image_urls": ["http://wiki.com/img1.jpg", "http://wiki.com/img2.jpg"] 
}

# Patch các hằng số config để đảm bảo đồng bộ với file test
@mock.patch('history_detail.HISTORY_COLLECTION', TEST_COLLECTION_HISTORY)
@mock.patch('history_detail.BEFORE_COLLECTION', TEST_COLLECTION_BEFORE)
@mock.patch('history_detail.shared_resources.db')
class TestHistoryDetail(unittest.TestCase):

    def setUp(self):
        print("\n" + "-"*70)

    # Hàm hỗ trợ setup DB mock để tránh lỗi truy cập dict
    def setup_mock_db(self, mock_db, history_return=None, metadata_return=None):
        """
        Cấu hình mock_db để khi gọi db['collection_name'] sẽ trả về đúng mock object.
        """
        # Tạo 2 mock collection riêng biệt
        mock_history_col = mock.Mock()
        mock_before_col = mock.Mock()

        # Cấu hình dữ liệu trả về cho từng collection
        mock_history_col.find_one.return_value = history_return
        mock_before_col.find_one.return_value = metadata_return

        # Hàm định tuyến: Khi code gọi db[KEY], hàm này quyết định trả về mock nào
        def get_collection(name):
            if name == TEST_COLLECTION_HISTORY:
                return mock_history_col
            if name == TEST_COLLECTION_BEFORE:
                return mock_before_col
            return mock.Mock() # Trả về mock rỗng cho các collection khác

        # Gán hàm định tuyến vào __getitem__ (tương ứng với hành động db[name])
        mock_db.__getitem__.side_effect = get_collection

    # =================================================================
    # 1. TEST API: SUMMARY
    # =================================================================
    
    def test_01_summary_success(self, mock_db):
        """Test lấy danh sách lịch sử thành công."""
        print("➤ [TEST 01] Kiểm tra API Summary: Lấy danh sách thành công...")
        
        # Setup: History có data
        self.setup_mock_db(mock_db, history_return=MOCK_USER_HISTORY_DOC)

        result = history_summary(user_id=TEST_USER_ID)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['landmark_id'], TEST_LANDMARK_ID)
        print(f"   ✔ PASSED: Trả về đúng 2 items.")

    def test_02_summary_empty(self, mock_db):
        """Test trường hợp user chưa có lịch sử."""
        print("➤ [TEST 02] Kiểm tra API Summary: User chưa có lịch sử...")

        # Setup: History trả về None
        self.setup_mock_db(mock_db, history_return=None)

        result = history_summary(user_id=TEST_USER_ID)

        self.assertEqual(result, [])
        print("   ✔ PASSED: Trả về danh sách rỗng [] đúng như dự kiến.")

    # =================================================================
    # 2. TEST API: DETAIL
    # =================================================================

    def test_03_detail_unauthorized(self, mock_db):
        """Test lỗi 401 khi không có user_id."""
        print("➤ [TEST 03] Kiểm tra API Detail: Không có User ID...")

        with self.assertRaises(HTTPException) as cm:
            history_detail(landmark_id=TEST_LANDMARK_ID, user_id=None)
        
        self.assertEqual(cm.exception.status_code, 401)
        print("   ✔ PASSED: Đã bắt lỗi 401 Unauthorized.")

    def test_04_detail_user_not_found(self, mock_db):
        """Test lỗi 404 khi User không có document lịch sử."""
        print("➤ [TEST 04] Kiểm tra API Detail: User không có lịch sử nào...")

        # Setup: User doc là None
        self.setup_mock_db(mock_db, history_return=None)

        with self.assertRaises(HTTPException) as cm:
            history_detail(landmark_id=TEST_LANDMARK_ID, user_id=TEST_USER_ID)
        
        self.assertEqual(cm.exception.status_code, 404)
        self.assertEqual(cm.exception.detail, "User has no history.")
        print("   ✔ PASSED: Đã bắt lỗi 404 User history not found.")

    def test_05_detail_item_not_found_in_history(self, mock_db):
        """Test lỗi 404 khi tìm ID không có trong lịch sử User."""
        print("➤ [TEST 05] Kiểm tra API Detail: ID không có trong lịch sử user...")

        # Setup: User có history, nhưng ta tìm ID "invalid_id"
        self.setup_mock_db(mock_db, history_return=MOCK_USER_HISTORY_DOC)

        with self.assertRaises(HTTPException) as cm:
            history_detail(landmark_id="invalid_id", user_id=TEST_USER_ID)
        
        self.assertEqual(cm.exception.status_code, 404)
        self.assertIn("not detected by this user", cm.exception.detail)
        print("   ✔ PASSED: Đã bắt lỗi 404 Item not found.")

    def test_06_detail_metadata_missing(self, mock_db):
        """Test lỗi 404 khi tìm thấy trong History nhưng mất Metadata gốc."""
        print("➤ [TEST 06] Kiểm tra API Detail: Dữ liệu Metadata gốc bị mất...")

        # Setup: History CÓ data, nhưng Metadata (Before) trả về None
        self.setup_mock_db(mock_db, 
                           history_return=MOCK_USER_HISTORY_DOC, 
                           metadata_return=None)

        with self.assertRaises(HTTPException) as cm:
            history_detail(landmark_id=TEST_LANDMARK_ID, user_id=TEST_USER_ID)
        
        # Bây giờ code sẽ vượt qua check history và fail ở check metadata
        self.assertEqual(cm.exception.status_code, 404)
        self.assertEqual(cm.exception.detail, "Landmark metadata not found.")
        print("   ✔ PASSED: Đã bắt lỗi 404 Metadata missing.")

    def test_07_detail_success_full_flow(self, mock_db):
        """Test lấy chi tiết thành công (Kết hợp History + Metadata)."""
        print("➤ [TEST 07] Kiểm tra API Detail: Thành công (Full Flow)...")

        # Setup: Cả 2 đều có data
        self.setup_mock_db(mock_db, 
                           history_return=MOCK_USER_HISTORY_DOC, 
                           metadata_return=MOCK_METADATA_DOC)

        result = history_detail(landmark_id=TEST_LANDMARK_ID, user_id=TEST_USER_ID)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["landmark_id"], TEST_LANDMARK_ID)
        self.assertEqual(result["matched_image_url"], "http://wiki.com/img2.jpg")
        
        print(f"   ✔ PASSED: Lấy chi tiết thành công.")

if __name__ == '__main__':
    unittest.main(verbosity=2)