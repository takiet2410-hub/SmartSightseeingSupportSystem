from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

def test_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_get_destinations_list(client: TestClient, sample_data):
    # Test lấy danh sách mặc định
    response = client.get("/destinations")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["data"]) == 2
    assert data["data"][0]["name"] == "Hồ Gươm"

def test_filter_destinations(client: TestClient, sample_data):
    # Test lọc theo budget
    response = client.get("/destinations?budget_range=cao")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["name"] == "Bà Nà Hills"

# Mock Weather API để test chi tiết địa điểm
@patch("main.get_current_weather", new_callable=AsyncMock)
def test_get_destination_detail(mock_weather, client: TestClient, sample_data):
    # Setup mock weather return
    mock_weather.return_value = {
        "temp": 25.0,
        "description": "Nắng nhẹ",
        "icon": "01d"
    }

    response = client.get("/destinations/L001")
    assert response.status_code == 200
    data = response.json()
    
    assert data["id"] == "L001"
    assert data["name"] == "Hồ Gươm"
    # Kiểm tra xem weather có được enrich vào không
    assert data["weather"]["temp"] == 25.0
    assert data["weather"]["description"] == "Nắng nhẹ"

def test_get_destination_not_found(client: TestClient):
    response = client.get("/destinations/NON_EXISTENT_ID")
    assert response.status_code == 404