import unittest
from unittest import mock
import os
import sys
import importlib

# Cấu hình đường dẫn
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import core.config

class TestConfig(unittest.TestCase):

    def setUp(self):
        print("\n" + "-"*70)
        self.original_env = os.environ.copy()

        # Biến môi trường chuẩn (Full)
        self.valid_env = {
            "JWT_SECRET_KEY": "test_secret",
            "JWT_ALGORITHM": "HS256",
            "MONGO_URI": "mongodb://localhost:27017",
            "DB_NAME": "test_db",
            "DURING_COLLECTION": "during",
            "BEFORE_COLLECTION": "before",
            "HISTORY_COLLECTION": "history",
            "TEMP_HISTORY_COLLECTION": "temp",
            "MODEL_NAME": "dinov2_vits14",
            "MODEL_PATH": "model.pth",
            "DEVICE_PREF": "cpu",
            "CLOUDINARY_CLOUD_NAME": "cloud",
            "CLOUDINARY_API_KEY": "123",
            "CLOUDINARY_API_SECRET": "abc"
        }

    def tearDown(self):
        # 1. Xoá sạch và khôi phục môi trường gốc
        os.environ.clear()
        os.environ.update(self.original_env)
        
        # 2. [QUAN TRỌNG] Reload lại config lần cuối ở trạng thái sạch
        # Cần chặn load_dotenv để nó không đọc file thật đè lên env gốc
        with mock.patch('dotenv.load_dotenv'), mock.patch('os.path.exists', return_value=True):
             importlib.reload(core.config)

    # =================================================================
    # 1. TEST KHÔNG TÌM THẤY FILE .ENV
    # =================================================================
    def test_01_env_file_not_found(self):
        """Test trường hợp không tìm thấy file .env."""
        print("➤ [TEST 01] Config: Không tìm thấy file .env...")
        
        os.environ.clear()
        os.environ.update(self.valid_env)

        # Mock os.path.exists trả về False (.env missing)
        # Mock dotenv.load_dotenv để đảm bảo không có magic nào xảy ra
        with mock.patch('os.path.exists', return_value=False), \
             mock.patch('dotenv.load_dotenv'):
            
            importlib.reload(core.config)
        
        print("   ✔ PASSED: Đã chạy qua nhánh 'else: print(KHÔNG tìm thấy file .env)'")

    # =================================================================
    # 2. TEST THIẾU BIẾN JWT (Đã sửa lỗi Fail)
    # =================================================================
    def test_02_missing_jwt_vars(self):
        """Test thiếu JWT_SECRET_KEY -> Raise EnvironmentError."""
        print("➤ [TEST 02] Config: Thiếu JWT Var...")

        env_missing_jwt = self.valid_env.copy()
        del env_missing_jwt["JWT_SECRET_KEY"] # Xoá biến
        
        os.environ.clear()
        os.environ.update(env_missing_jwt)

        # [FIX QUAN TRỌNG] Patch 'dotenv.load_dotenv' để ngăn config đọc file .env thật
        # Nếu không patch, load_dotenv sẽ đọc file thật và điền lại JWT_SECRET_KEY vào -> Test Fail
        with mock.patch('os.path.exists', return_value=True), \
             mock.patch('dotenv.load_dotenv'):
            
            with self.assertRaises(EnvironmentError) as cm:
                importlib.reload(core.config)
            
            # Kiểm tra thông báo lỗi có chứa tên biến thiếu không
            self.assertIn("JWT_SECRET_KEY", str(cm.exception))
        
        print("   ✔ PASSED: Đã bắt lỗi thiếu JWT config.")

    # =================================================================
    # 3. TEST THIẾU BIẾN DATABASE/MODEL (Đã sửa lỗi Fail)
    # =================================================================
    def test_03_missing_required_vars(self):
        """Test thiếu các biến bắt buộc khác -> Raise EnvironmentError."""
        print("➤ [TEST 03] Config: Thiếu Required Var (MONGO_URI)...")

        env_missing_mongo = self.valid_env.copy()
        del env_missing_mongo["MONGO_URI"] # Xoá biến
        
        os.environ.clear()
        os.environ.update(env_missing_mongo)

        # [FIX QUAN TRỌNG] Tương tự, chặn load_dotenv
        with mock.patch('os.path.exists', return_value=True), \
             mock.patch('dotenv.load_dotenv'):
            
            with self.assertRaises(EnvironmentError) as cm:
                importlib.reload(core.config)
            
            self.assertIn("MONGO_URI", str(cm.exception))

        print("   ✔ PASSED: Đã bắt lỗi thiếu Required Vars.")

    # =================================================================
    # 4. TEST HAPPY PATH
    # =================================================================
    def test_04_config_load_success(self):
        """Test khi có đầy đủ biến môi trường."""
        print("➤ [TEST 04] Config: Load thành công (Full Vars)...")

        os.environ.clear()
        os.environ.update(self.valid_env)

        with mock.patch('os.path.exists', return_value=True), \
             mock.patch('dotenv.load_dotenv'):
            
            importlib.reload(core.config)
            self.assertEqual(core.config.JWT_SECRET_KEY, "test_secret")

        print("   ✔ PASSED: Config load thành công.")

if __name__ == '__main__':
    unittest.main(verbosity=2)