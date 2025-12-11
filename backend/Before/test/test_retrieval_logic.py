import pytest
import mongomock
from unittest.mock import patch
from modules.retrieval import build_filter_query, get_destinations_paginated
from schemas import HardConstraints, SortOption

# 1. Test hàm build_filter_query
def test_build_filter_query_correctness():
    # Case 1: Filter đầy đủ
    filters = HardConstraints(
        budget_range=["thấp", "trung bình"],
        location_province="Lâm Đồng"
    )
    query = build_filter_query(filters)
    
    assert query["budget_range"] == {"$in": ["thấp", "trung bình"]}
    assert query["location_province"] == "Lâm Đồng"

    # Case 2: Filter rỗng (None)
    empty_filters = HardConstraints()
    query_empty = build_filter_query(empty_filters)
    assert query_empty == {}

# 2. Test Defensive Coding (Chống lỗi 500)
@patch("modules.retrieval.get_db_collection") # Mock hàm lấy DB
def test_get_destinations_defensive_coding(mock_get_collection):
    # --- SETUP MOCK DB ---
    mock_collection = mongomock.MongoClient().db.collection
    
    # Thêm dữ liệu "BẨN" (Thiếu field, sai kiểu dữ liệu) để test độ bền
    dirty_data = [
        {
            "_id": "507f1f77bcf86cd799439011",
            "landmark_id": "L001",
            "name": "Địa điểm tốt",
            "overall_rating": 4.5,
            "image_urls": ["img1.jpg"]
        },
        {
            "_id": "507f1f77bcf86cd799439012",
            "landmark_id": "L002",
            "name": "Địa điểm LỖI RATING", 
            "overall_rating": None,   # <--- Rating Null
            "image_urls": None        # <--- Image Null
        },
        {
            "_id": "507f1f77bcf86cd799439013",
            # Thiếu landmark_id
            "name": "Địa điểm THIẾU ID",
            "overall_rating": "Not a number" # <--- Rating sai kiểu
        }
    ]
    mock_collection.insert_many(dirty_data)
    
    # Cho hàm get_db_collection trả về mock collection này
    mock_get_collection.return_value = mock_collection

    # --- EXECUTE ---
    # Gọi hàm xử lý
    filters = HardConstraints()
    result = get_destinations_paginated(filters, SortOption.RATING_DESC, page=1, limit=10)

    # --- ASSERT (KIỂM TRA) ---
    data = result["data"]
    
    # Kiểm tra số lượng: Phải trả về đủ 3 items (không được crash)
    assert len(data) == 3
    
    # Item 1: Chuẩn
    assert data[0]["overall_rating"] == 4.5
    
    # Item 2: Rating null phải thành 0.0, Image null phải thành []
    assert data[1]["overall_rating"] == 0.0
    assert data[1]["image_urls"] == []
    
    # Item 3: Rating sai kiểu phải thành 0.0, ID lấy từ _id
    assert data[2]["overall_rating"] == 0.0
    assert str(data[2]["id"]) == "507f1f77bcf86cd799439013"