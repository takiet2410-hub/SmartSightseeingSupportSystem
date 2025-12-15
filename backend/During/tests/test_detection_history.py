import unittest
from unittest import mock
from fastapi import HTTPException 
import sys
import os
import hashlib

# --- CẤU HÌNH ĐƯỜNG DẪN ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from detection_history import (
    add_history_record, 
    add_temp_record, 
    sync_temp_history, 
    get_image_hash,
    delete_history_items,   
    get_public_id_from_url,
    upload_image_to_cloud
)

# --- DỮ LIỆU GIẢ LẬP ---
TEST_USER_ID = "user_123"
TEST_TEMP_ID = "temp_456"
TEST_LANDMARK = {"landmark_id": "lm_001", "similarity_score": 0.95}
TEST_IMAGE_BYTES = b"fake_image_content"
TEST_IMAGE_HASH = hashlib.md5(TEST_IMAGE_BYTES).hexdigest()
TEST_URL = "http://res.cloudinary.com/demo/image/upload/v1234/sample.jpg"

class TestHistoryManagement(unittest.TestCase):

    def setUp(self):
        print("\n" + "-"*70)

    # =================================================================
    # 1. TEST HELPER & UPLOAD (Cover dòng 65, Helper)
    # =================================================================
    def test_01_get_image_hash(self):
        print("➤ [TEST 01] Helper: Hash MD5...")
        self.assertEqual(get_image_hash(TEST_IMAGE_BYTES), TEST_IMAGE_HASH)

    def test_02_get_public_id_edge_cases(self):
        print("➤ [TEST 02] Helper: Public ID from URL...")
        self.assertEqual(get_public_id_from_url(TEST_URL), "sample")
        self.assertIsNone(get_public_id_from_url("http://google.com/img.jpg"))
        self.assertIsNone(get_public_id_from_url("http://res.cloudinary.com/demo/image/no_upload/v1/img.jpg"))

    @mock.patch('detection_history.cloudinary.uploader.upload')
    def test_03_upload_success(self, mock_cloud):
        """Cover dòng 65: return secure_url"""
        print("➤ [TEST 03] Upload: Success...")
        mock_cloud.return_value = {"secure_url": "https://ok.com/img.jpg"}
        self.assertEqual(upload_image_to_cloud(TEST_IMAGE_BYTES), "https://ok.com/img.jpg")

    @mock.patch('detection_history.cloudinary.uploader.upload')
    def test_04_upload_fail(self, mock_cloud):
        print("➤ [TEST 04] Upload: Fail (Exception)...")
        mock_cloud.side_effect = Exception("Error")
        self.assertIsNone(upload_image_to_cloud(TEST_IMAGE_BYTES))

    # =================================================================
    # 2. TEST ADD HISTORY (Cover dòng 89, 129-134, 139, 151)
    # =================================================================
    @mock.patch('detection_history.shared_resources.db')
    @mock.patch('detection_history.upload_image_to_cloud')
    def test_05_add_history_new_user(self, mock_upload, mock_db):
        """Cover dòng 151 (if not user_doc)"""
        print("➤ [TEST 05] History: New User (Insert One)...")
        mock_upload.return_value = TEST_URL
        mock_col = mock_db["history_collection"]
        mock_col.find_one.return_value = None 

        add_history_record(TEST_USER_ID, TEST_LANDMARK, "Name", uploaded_image_bytes=TEST_IMAGE_BYTES)
        self.assertTrue(mock_col.insert_one.called)

    @mock.patch('detection_history.shared_resources.db')
    @mock.patch('detection_history.upload_image_to_cloud')
    def test_06_add_history_append_new_record(self, mock_upload, mock_db):
        """Cover dòng 157-158 (else: insert(0))"""
        print("➤ [TEST 06] History: Existing User, New Record (Update One)...")
        mock_upload.return_value = TEST_URL
        mock_col = mock_db["history_collection"]
        mock_col.find_one.return_value = {"user_id": TEST_USER_ID, "history": [{"landmark_id": "lm_OLD"}]}

        add_history_record(TEST_USER_ID, TEST_LANDMARK, "Name", uploaded_image_bytes=TEST_IMAGE_BYTES)
        
        self.assertTrue(mock_col.update_one.called)
        args = mock_col.update_one.call_args[0]
        self.assertEqual(len(args[1]['$set']['history']), 2)

    @mock.patch('detection_history.shared_resources.db')
    def test_07_add_history_duplicate_logic(self, mock_db):
        """Cover dòng 129-134 (Move to top, Update timestamp)"""
        print("➤ [TEST 07] History: Duplicate Record (Move to Top)...")
        mock_col = mock_db["history_collection"]
        # Record cũ trùng URL
        history = [{"landmark_id": TEST_LANDMARK["landmark_id"], "user_image_url": TEST_URL, "timestamp": "old"}]
        mock_col.find_one.return_value = {"user_id": TEST_USER_ID, "history": history}

        add_history_record(TEST_USER_ID, TEST_LANDMARK, "Name", uploaded_image_bytes=TEST_IMAGE_BYTES, existing_url=TEST_URL)

        self.assertTrue(mock_col.update_one.called)
        args = mock_col.update_one.call_args[0]
        # Timestamp phải thay đổi
        self.assertNotEqual(args[1]['$set']['history'][0]['timestamp'], "old")

    @mock.patch('detection_history.shared_resources.db')
    def test_08_add_history_sync_hash(self, mock_db):
        """Cover dòng 89 (current_image_hash = existing_hash)"""
        print("➤ [TEST 08] History: Sync Hash Logic...")
        mock_col = mock_db["history_collection"]
        mock_col.find_one.return_value = None

        add_history_record(TEST_USER_ID, TEST_LANDMARK, "Name", existing_hash="hash_123", existing_url="url")
        
        args = mock_col.insert_one.call_args[0]
        self.assertEqual(args[0]['history'][0]['image_hash'], "hash_123")

    # =================================================================
    # 3. TEST ADD TEMP RECORD (KHÔI PHỤC PHẦN BỊ THIẾU - Cover 171-195)
    # =================================================================
    @mock.patch('detection_history.shared_resources.db')
    @mock.patch('detection_history.upload_image_to_cloud')
    def test_09_add_temp_new_session(self, mock_upload, mock_db):
        """Test thêm Temp mới (Insert One)"""
        print("➤ [TEST 09] Temp: New Session (Insert)...")
        mock_upload.return_value = TEST_URL
        mock_col = mock_db["temp_history_collection"]
        mock_col.find_one.return_value = None

        add_temp_record(TEST_TEMP_ID, TEST_LANDMARK, TEST_IMAGE_BYTES, "Name")
        self.assertTrue(mock_col.insert_one.called)

    @mock.patch('detection_history.shared_resources.db')
    @mock.patch('detection_history.upload_image_to_cloud')
    def test_10_add_temp_existing_session(self, mock_upload, mock_db):
        """Test thêm Temp vào session cũ (Update One)"""
        print("➤ [TEST 10] Temp: Existing Session (Update)...")
        mock_upload.return_value = TEST_URL
        mock_col = mock_db["temp_history_collection"]
        mock_col.find_one.return_value = {"temp_id": TEST_TEMP_ID, "history": [{"landmark_id": "lm_OLD"}]}

        add_temp_record(TEST_TEMP_ID, TEST_LANDMARK, TEST_IMAGE_BYTES, "Name")
        
        self.assertTrue(mock_col.update_one.called)
        args = mock_col.update_one.call_args[0]
        self.assertEqual(len(args[1]['$set']['history']), 2)

    # =================================================================
    # 4. TEST SYNC & DELETE (Cover 225-227, 253-254)
    # =================================================================
    def test_11_sync_unauthorized(self):
        """Cover 225-227 (Check user_id)"""
        print("➤ [TEST 11] Sync: Unauthorized Check...")
        with self.assertRaises(HTTPException) as cm:
            sync_temp_history(TEST_TEMP_ID, None)
        self.assertEqual(cm.exception.status_code, 401)

    @mock.patch('detection_history.add_history_record')
    @mock.patch('detection_history.shared_resources.db')
    def test_12_sync_success(self, mock_db, mock_add_hist):
        print("➤ [TEST 12] Sync: Success Flow...")
        mock_col = mock_db["temp_history_collection"]
        mock_col.find_one.return_value = {
            "history": [{"landmark_id": "lm1", "name": "n", "similarity_score": 0.9, "timestamp": "t"}]
        }
        
        sync_temp_history(TEST_TEMP_ID, TEST_USER_ID)
        
        self.assertTrue(mock_add_hist.called)
        self.assertTrue(mock_col.delete_one.called)

    def test_13_delete_validations(self):
        """Cover 253-254 (Check list empty)"""
        print("➤ [TEST 13] Delete: Validations...")
        with self.assertRaises(HTTPException):
            delete_history_items(["url"], None) # Thiếu User
        
        res = delete_history_items([], TEST_USER_ID) # List rỗng
        self.assertEqual(res['status'], "ignored")

    @mock.patch('detection_history.cloudinary.uploader.destroy')
    @mock.patch('detection_history.shared_resources.db')
    def test_14_delete_success(self, mock_db, mock_destroy):
        print("➤ [TEST 14] Delete: Success...")
        mock_destroy.return_value = {"result": "ok"}
        mock_col = mock_db["history_collection"]
        mock_col.update_one.return_value.modified_count = 1

        delete_history_items([TEST_URL], TEST_USER_ID)
        self.assertTrue(mock_col.update_one.called)

if __name__ == '__main__':
    unittest.main(verbosity=2)