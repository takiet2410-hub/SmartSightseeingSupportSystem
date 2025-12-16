import pytest
from unittest.mock import MagicMock, patch, AsyncMock

# --- TEST GET LIST ---
def test_list_destinations_default(client):
    """Test lấy danh sách mặc định"""
    mock_result = {
        "data": [{
            "id": "1", 
            "name": "Place A", 
            "location_province": "Hà Nội", 
            "overall_rating": 4.5
        }],
        "total": 1, "page": 1, "limit": 10, "total_pages": 1
    }
    
    with patch("main.get_destinations_paginated", return_value=mock_result):
        response = client.get("/destinations")
        assert response.status_code == 200
        assert len(response.json()["data"]) == 1
        assert response.json()["data"][0]["name"] == "Place A"

def test_list_destinations_with_filter(client):
    """Test lấy danh sách có filter param"""
    mock_result = {"data": [], "total": 0, "page": 1, "limit": 10, "total_pages": 0}
    
    with patch("main.get_destinations_paginated", return_value=mock_result) as mock_func:
        response = client.get("/destinations?budget_range=thấp&location_province=Hà Nội")
        assert response.status_code == 200
        
        args, _ = mock_func.call_args
        filters = args[0]
        assert filters.budget_range == ["thấp"]
        assert filters.location_province == "Hà Nội"

# --- TEST DETAIL & WEATHER ---
def test_get_detail_found_with_weather(client):
    """Test lấy chi tiết địa điểm + Mock thời tiết"""
    mock_detail = {
        "id": "lm_1",
        "landmark_id": "lm_1",
        "name": "Ha Long Bay",
        "location_province": "Quảng Ninh",
        "overall_rating": 5.0
    }
    
    mock_weather = {
        "temp": 25.5, "description": "Nắng đẹp", "icon": "01d"
    }

    with patch("main.get_destination_details", return_value=mock_detail), \
         patch("main.get_current_weather", new_callable=AsyncMock) as mock_weather_func:
        
        mock_weather_func.return_value = mock_weather
        
        response = client.get("/destinations/lm_1")
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "Ha Long Bay"
        assert data["weather"]["temp"] == 25.5
        mock_weather_func.assert_called_with("Quảng Ninh")

def test_get_detail_not_found(client):
    """Test 404 khi không tìm thấy"""
    with patch("main.get_destination_details", return_value=None):
        response = client.get("/destinations/invalid")
        assert response.status_code == 404