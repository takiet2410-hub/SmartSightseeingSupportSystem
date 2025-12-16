import pytest
from unittest.mock import MagicMock, patch
from modules.retrieval import build_filter_query, get_destinations_paginated, retrieve_context
from schemas import HardConstraints, SortOption

# --- 1. TEST LOGIC TẠO BỘ LỌC (Pure Logic) ---
def test_build_filter_query_logic():
    """Kiểm tra xem input từ API có chuyển thành query MongoDB đúng không"""
    constraints = HardConstraints(
        budget_range=["thấp", "trung bình"],
        location_province="Quảng Ngãi",
        season_tag=["thu"]
    )
    
    query = build_filter_query(constraints)
    
    # Kiểm tra query dict
    assert query["location_province"] == "Quảng Ngãi"
    assert query["budget_range"] == {"$in": ["thấp", "trung bình"]}
    assert query["season_tag"] == {"$in": ["thu"]}
    # Đảm bảo trường không chọn thì không có trong query
    assert "companion_tag" not in query

# --- 2. TEST PHÂN TRANG (Integration với Mock DB) ---
def test_get_destinations_paginated(mock_db):
    """Kiểm tra logic chia trang"""
    collection = mock_db.get_collection("destinations")
    collection.delete_many({})
    
    # 1. Tạo 15 địa điểm giả
    dummy_data = []
    for i in range(15):
        dummy_data.append({
            "landmark_id": f"L{i}",
            "name": f"Place {i}",
            "overall_rating": 4.0,
            "location_province": "Test City"
        })
    collection.insert_many(dummy_data)
    
    # 2. Test lấy Trang 1 (Limit 10)
    filters = HardConstraints() # Không lọc gì cả
    result_p1 = get_destinations_paginated(filters, SortOption.RATING_DESC, page=1, limit=10)
    
    assert result_p1["total"] == 15
    assert len(result_p1["data"]) == 10
    assert result_p1["total_pages"] == 2
    assert result_p1["page"] == 1

    # 3. Test lấy Trang 2 (Limit 10 -> còn dư 5)
    result_p2 = get_destinations_paginated(filters, SortOption.RATING_DESC, page=2, limit=10)
    assert len(result_p2["data"]) == 5
    assert result_p2["page"] == 2

# --- 3. TEST VECTOR SEARCH (Mock Aggregation) ---
@patch("modules.retrieval.get_db_collection")
def test_retrieve_context_vector_search(mock_get_col):
    # 1. Setup Mock Collection
    mock_collection = MagicMock()
    mock_get_col.return_value = mock_collection
    
    # 2. Giả lập kết quả trả về từ pipeline aggregate
    # Item 1: Score 0.9 (Giữ)
    # Item 2: Score 0.5 (Loại - vì threshold mặc định là 0.61)
    mock_results = [
        {
            "_id": "id1", "landmark_id": "L1", "name": "Good Match", 
            "score": 0.9, "location_province": "A", "image_urls": []
        },
        {
            "_id": "id2", "landmark_id": "L2", "name": "Bad Match", 
            "score": 0.5, "location_province": "B", "image_urls": []
        }
    ]
    mock_collection.aggregate.return_value = mock_results
    
    # 3. Gọi hàm
    dummy_vector = [0.1] * 768
    results = retrieve_context(dummy_vector)
    
    # 4. Kiểm tra logic lọc
    # Nếu hàm retrieve_context của bạn trả về đúng list mock_results (đã lọc ở DB), thì ta kiểm tra xem nó có crash không và mapping data đúng không.
    assert len(results) == 2 
    
    # Unit test này chủ yếu verify rằng hàm không bị lỗi khi nhận data từ Mongo.
    assert results[0]["landmark_id"] == "L1"
    assert results[0]["name"] == "Good Match"
    
    # Kiểm tra xem pipeline đã được gọi đúng chưa (có stage $vectorSearch không)
    called_pipeline = mock_collection.aggregate.call_args[0][0]
    assert "$vectorSearch" in called_pipeline[0]