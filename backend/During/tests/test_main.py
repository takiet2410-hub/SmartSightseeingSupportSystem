import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys
import os
import importlib # [QUAN TRỌNG] Thư viện để reload module

# Cấu hình đường dẫn
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import shared_resources 
import main # Import module main ở ngoài để reload được

class TestMainApp(unittest.TestCase):

    def setUp(self):
        print("\n" + "="*60)
        
        # 1. Mock hàm load_resources (để không kết nối DB thật)
        self.patcher_load = patch('shared_resources.load_resources')
        self.mock_load = self.patcher_load.start()
        
        # 2. Mock biến 'db' (để code không bị lỗi NoneType khi gọi db[COLLECTION])
        self.patcher_db = patch('shared_resources.db', new_callable=MagicMock)
        self.mock_db = self.patcher_db.start()

        # 3. [QUAN TRỌNG] Reload main để app được khởi tạo lại với các Mock mới nhất
        # Nếu không có dòng này, app vẫn giữ tham chiếu đến hàm load_resources THẬT
        importlib.reload(main)
        
        # Lấy app mới sau khi reload
        self.app = main.app
        self.client = TestClient(self.app)

    def tearDown(self):
        # Dừng tất cả patch để không ảnh hưởng test khác
        patch.stopall()

    def test_01_read_root(self):
        """Test API gốc."""
        print("➤ [TEST 01] Kiểm tra endpoint gốc '/'...")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        print("   ✔ PASSED: Root endpoint OK.")

    def test_02_routers_are_attached(self):
        """Test xem các Router đã được gắn chưa."""
        print("➤ [TEST 02] Kiểm tra Integration (Routers)...")

        # Test History Summary
        response = self.client.get("/history/summary")
        # 200 OK (vì mock DB trả về magic mock list) hoặc 401/422 đều chứng tỏ router tồn tại
        self.assertNotEqual(response.status_code, 404, "Lỗi: Route /history/summary chưa được gắn.")
        print(f"   ✔ PASSED: Route /history/summary tồn tại (Status: {response.status_code}).")

        # Test Sync
        response = self.client.post("/history/sync")
        self.assertNotEqual(response.status_code, 404, "Lỗi: Route /history/sync chưa được gắn.")
        print(f"   ✔ PASSED: Route /history/sync tồn tại (Status: {response.status_code}).")

    def test_03_startup_event_triggered(self):
        """Test Startup Event."""
        print("➤ [TEST 03] Kiểm tra Startup Event...")
        
        # Dùng context manager để kích hoạt sự kiện lifespan/startup
        with TestClient(self.app) as client:
            client.get("/") 
            
            # Kiểm tra mock
            if self.mock_load.called:
                 print(f"   ✔ PASSED: Hàm load_resources đã được gọi {self.mock_load.call_count} lần.")
            else:
                 print(f"   ❌ FAILED: Call count: {self.mock_load.call_count}")
            
            self.assertTrue(self.mock_load.called, "Startup event không gọi hàm load_resources giả.")

if __name__ == '__main__':
    unittest.main(verbosity=2)