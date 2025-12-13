from unittest.mock import MagicMock, patch
from schemas import HardConstraints, SortOption
from modules.retrieval import build_filter_query, get_destinations_paginated

def test_build_filter_query():
    """Test chuyển đổi tham số URL thành MongoDB Query"""
    constraints = HardConstraints(
        budget_range=["cao"],
        location_province="Hà Nội"
    )
    query = build_filter_query(constraints)
    assert query["location_province"] == "Hà Nội"
    assert query["budget_range"] == {"$in": ["cao"]}
    assert "companion_tag" not in query

def test_data_mapping_safety():
    """Test xử lý dữ liệu bẩn (Null/Missing fields)"""
    mock_collection = MagicMock()
    # Giả lập dữ liệu thiếu field từ DB
    raw_docs = [{
        "_id": "obj_id_123", 
        "landmark_id": "lm_1", 
        "name": "Test Place", 
        "overall_rating": None,
        "image_urls": None
    }]
    
    # Tạo Mock Cursor
    mock_cursor = MagicMock()
    mock_cursor.__iter__.return_value = iter(raw_docs)
    
    # Đảm bảo chuỗi gọi hàm trả về chính mock_cursor
    mock_collection.find.return_value = mock_cursor
    mock_cursor.collation.return_value = mock_cursor
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.skip.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor 
    
    mock_collection.count_documents.return_value = 1

    with patch("modules.retrieval.get_db_collection", return_value=mock_collection):
        # Gọi hàm cần test
        result = get_destinations_paginated(HardConstraints(), SortOption.RATING_DESC, page=1, limit=10)
        
        # Bây giờ result["data"] sẽ có dữ liệu
        assert len(result["data"]) > 0
        item = result["data"][0]
        
        # Assert logic
        assert item["id"] == "lm_1"
        assert item["overall_rating"] == 0.0 
        assert item["image_urls"] == []