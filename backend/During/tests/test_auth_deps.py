import unittest
from unittest import mock
import jwt
from typing import Optional
import sys
import os

# --- CẤU HÌNH ĐƯỜNG DẪN (Để tìm thấy file ở thư mục cha) ---
# Thêm thư mục gốc (DURING) vào sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from auth_deps import get_current_user_id 
# -----------------------------------------------------------

# Hằng số giả lập
TEST_USER_ID = "user-123-abc"
TEST_TOKEN_CREDENTIALS = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.S6S"

# Mock Class giả lập đối tượng credentials của FastAPI
class MockHTTPAuthorizationCredentials:
    def __init__(self, credentials: str):
        self.scheme: str = "Bearer"
        self.credentials: str = credentials

# Bắt đầu Class Test
@mock.patch('auth_deps.jwt')
@mock.patch('auth_deps.JWT_SECRET_KEY', 'TEST_SECRET')
@mock.patch('auth_deps.JWT_ALGORITHM', 'HS256')
class TestAuthDeps(unittest.TestCase):

    # Hàm này chạy MỞ ĐẦU mỗi test case để in dòng kẻ phân cách cho đẹp
    def setUp(self):
        print("\n" + "-"*70)

    def test_01_success_with_sub_claim(self, mock_jwt):
        """Test 1: Token chuẩn (chứa 'sub')."""
        print("➤ [TEST 01] Đang kiểm tra: Token hợp lệ chứa claim 'sub'...")
        
        # 1. Setup giả lập
        mock_jwt.decode.return_value = {"sub": TEST_USER_ID, "exp": 9999999999}
        mock_token = MockHTTPAuthorizationCredentials(TEST_TOKEN_CREDENTIALS)

        # 2. Chạy hàm
        result = get_current_user_id(mock_token)

        # 3. Kiểm tra kết quả
        self.assertEqual(result, TEST_USER_ID)
        print(f"   ✔ PASSED: Hàm trả về đúng user_id: {result}")

    def test_02_success_with_user_id_claim(self, mock_jwt):
        """Test 2: Token kiểu cũ (chứa 'user_id')."""
        print("➤ [TEST 02] Đang kiểm tra: Token hợp lệ chứa claim 'user_id' (legacy)...")

        mock_jwt.decode.return_value = {"user_id": TEST_USER_ID}
        mock_token = MockHTTPAuthorizationCredentials(TEST_TOKEN_CREDENTIALS)

        result = get_current_user_id(mock_token)
        
        self.assertEqual(result, TEST_USER_ID)
        print(f"   ✔ PASSED: Hàm nhận diện được 'user_id' và trả về: {result}")

    def test_03_no_token_provided(self, mock_jwt):
        """Test 3: Không gửi token lên."""
        print("➤ [TEST 03] Đang kiểm tra: Trường hợp người dùng không gửi Token...")

        result = get_current_user_id(None)

        self.assertIsNone(result)
        print("   ✔ PASSED: Hàm trả về None đúng như dự kiến.")

    def test_04_invalid_or_expired_token(self, mock_jwt):
        """Test 4: Token bị lỗi hoặc hết hạn."""
        print("➤ [TEST 04] Đang kiểm tra: Token bị lỗi hoặc hết hạn...")

        # Giả lập jwt ném lỗi khi decode
        mock_jwt.decode.side_effect = jwt.exceptions.ExpiredSignatureError("Token expired")
        mock_token = MockHTTPAuthorizationCredentials(TEST_TOKEN_CREDENTIALS)

        result = get_current_user_id(mock_token)

        self.assertIsNone(result)
        mock_jwt.decode.side_effect = None # Reset lại để không ảnh hưởng test sau
        print("   ✔ PASSED: Hàm đã bắt được lỗi và trả về None an toàn.")

    def test_05_missing_user_id_in_payload(self, mock_jwt):
        """Test 5: Token đúng nhưng thiếu thông tin user."""
        print("➤ [TEST 05] Đang kiểm tra: Token decode được nhưng thiếu field user_id...")

        mock_jwt.decode.return_value = {"aud": "some_api"} # Không có sub, không có user_id
        mock_token = MockHTTPAuthorizationCredentials(TEST_TOKEN_CREDENTIALS)

        result = get_current_user_id(mock_token)

        self.assertIsNone(result)
        print("   ✔ PASSED: Hàm trả về None vì không tìm thấy ID người dùng.")

if __name__ == '__main__':
    # verbosity=2 giúp hiển thị thêm tên docstring của hàm test
    unittest.main(verbosity=2)