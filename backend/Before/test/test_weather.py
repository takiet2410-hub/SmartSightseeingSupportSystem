import pytest
from modules.weather import get_current_weather
import httpx
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_weather_success():
    # Mock response từ OpenWeather
    mock_response = {
        "main": {"temp": 30.5},
        "weather": [{"description": "mưa rào", "icon": "10d"}]
    }
    
    # Dùng patch để giả lập httpx.AsyncClient.get
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: mock_response
        )
        
        result = await get_current_weather("Hanoi")
        
        assert result is not None
        assert result["temp"] == 30.5
        assert result["description"] == "Mưa rào" # Hàm code có .capitalize()
        assert result["icon"] == "10d"

@pytest.mark.asyncio
async def test_weather_failure():
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=404)
        
        result = await get_current_weather("UnknownCity")
        assert result is None