from unittest.mock import patch
import json
from modules.generation import parse_llm_response

def test_weather_timeout(client):
    """Weather API timeout -> Trả về detail nhưng weather=None"""
    mock_detail = {"landmark_id": "lm_1", "name": "Hue", "location_province": "Hue"}
    
    with patch("main.get_destination_details", return_value=mock_detail), \
         patch("httpx.AsyncClient.get", side_effect=Exception("Timeout")):
        
        response = client.get("/destinations/lm_1")
        assert response.status_code == 200
        assert response.json()["weather"] is None # Fail gracefully

def test_gemini_bad_json():
    """LLM trả về JSON lỗi -> Xử lý ngoại lệ"""
    res = parse_llm_response("Not JSON")
    assert "error" in res

def test_login_proxy_fail(client):
    """Auth Server lỗi -> Báo lỗi 503"""
    import requests
    with patch("requests.post", side_effect=requests.exceptions.ConnectionError):
        response = client.post("/login-proxy", data={"username": "u", "password": "p"})
        assert response.status_code == 503