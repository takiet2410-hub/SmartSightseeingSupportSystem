import pytest
import mongomock
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import os
import sys

# Thêm đường dẫn project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from deps import get_current_user

# --- 1. MOCK DATABASE ---
@pytest.fixture(scope="session")
def mock_mongo_client():
    return mongomock.MongoClient()

@pytest.fixture(scope="session")
def mock_db(mock_mongo_client):
    return mock_mongo_client.get_database("test_db")

# --- 2. FIX QUAN TRỌNG: Patch đúng nơi sử dụng ---
@pytest.fixture(autouse=True)
def override_db_dependencies(mock_db):
    # Hàm giả thay thế trả về mock collection
    def _get_dest_collection():
        return mock_db.get_collection("destinations")
    
    def _get_fav_collection():
        return mock_db.get_collection("favorites")

    def _get_users_collection():
        return mock_db.get_collection("users")

    # PATCH TẤT CẢ CÁC MODULE ĐANG IMPORT HÀM KẾT NỐI DB
    # 1. Patch cho file modules/retrieval.py
    p1 = patch("modules.retrieval.get_db_collection", side_effect=_get_dest_collection)
    # 2. Patch cho file favorites.py (Cả collection địa điểm và yêu thích)
    p2 = patch("favorites.get_db_collection", side_effect=_get_dest_collection)
    p3 = patch("favorites.get_favorites_collection", side_effect=_get_fav_collection)
    # 3. Patch cho deps.py (Nếu có check user)
    p4 = patch("deps.get_users_collection", side_effect=_get_users_collection)
    # 4. Patch cho modules/retrieval.py (Phần vector search dùng aggregation)
    #    Lưu ý: mongomock hỗ trợ aggregation cơ bản, nhưng vectorSearch thì không.
    #    Ta cần mock hàm retrieve_context nếu test đụng tới vector search sâu.
    
    with p1, p2, p3, p4:
        yield

# --- 3. MOCK VECTORIZER ---
@pytest.fixture(autouse=True)
def mock_vectorizer():
    # Patch trực tiếp object vectorizer đã khởi tạo trong main.py
    with patch("main.vectorizer") as mock_vec:
        # Giả lập hàm transform trả về vector dummy 768 chiều
        mock_vec.transform_single.return_value = [0.1] * 768
        yield mock_vec

# --- 4. MOCK AUTHENTICATION ---
@pytest.fixture
def mock_user_id():
    return "user_123_test"

@pytest.fixture
def client(mock_user_id):
    # Override dependency get_current_user
    app.dependency_overrides[get_current_user] = lambda: mock_user_id
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {}

# --- 5. PRELOAD DATA (QUAN TRỌNG: Dùng id String) ---
@pytest.fixture
def sample_data(mock_db):
    destinations = mock_db.get_collection("destinations")
    destinations.delete_many({}) 
    
    data = [
        {
            "landmark_id": "L001", # ID dùng để query trong code
            "name": "Hồ Gươm",
            "location_province": "Hà Nội",
            "overall_rating": 4.8,
            "budget_range": "thấp",
            "available_time": ["1-2 giờ", "4-8 giờ"],
            "image_urls": ["url1.jpg"],
            "v_hybrid": [0.1] * 768
        },
        {
            "landmark_id": "L002",
            "name": "Bà Nà Hills",
            "location_province": "Đà Nẵng",
            "overall_rating": 4.5,
            "budget_range": "cao",
            "available_time": ["4-8 giờ"],
            "image_urls": ["url2.jpg"],
            "v_hybrid": [0.2] * 768
        }
    ]
    # Insert dữ liệu giả vào Mock DB
    destinations.insert_many(data)
    return data