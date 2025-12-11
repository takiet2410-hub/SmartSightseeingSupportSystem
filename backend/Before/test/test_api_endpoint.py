from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch

client = TestClient(app)

# Mock hàm logic bên dưới để chỉ test lớp API (Controller)
@patch("main.get_destinations_paginated")
def test_list_destinations_url_parsing(mock_logic):
    # Setup mock return
    mock_logic.return_value = {
        "data": [], "total": 0, "page": 1, "limit": 10, "total_pages": 0
    }

    # --- TEST QUERY PARAMETER ---
    # Giả lập gọi GET request với query string
    response = client.get(
        "/destinations?budget_range=thấp&budget_range=cao&location_province=Đà Lạt&page=1&limit=10"
    )

    # 1. Kiểm tra HTTP Status
    assert response.status_code == 200

    # 2. Kiểm tra Backend nhận được tham số gì
    # Lấy arguments mà hàm get_destinations_paginated đã được gọi
    args, _ = mock_logic.call_args
    filters_received = args[0] # Tham số đầu tiên là filters

    # ĐÂY LÀ PHẦN QUAN TRỌNG NHẤT:
    # Nếu API parse đúng, budget_range phải là list ['thấp', 'cao']
    assert filters_received.budget_range == ["thấp", "cao"]
    assert filters_received.location_province == "Đà Lạt"

def test_search_api_integration():
    # Test endpoint POST /search vẫn hoạt động
    payload = {
        "query": "du lịch biển",
        "hard_constraints": {
            "budget_range": ["cao"]
        }
    }
    # Vì API này gọi DB thật/Vector Search, ta chỉ check validation 
    # hoặc phải mock retrieve_context. Ở đây check validation error nếu sai format.
    response = client.post("/search", json=payload)
    
    # Nếu setup DB mock thì check 200, còn không thì check không phải 422 (Validation Error)
    assert response.status_code != 422