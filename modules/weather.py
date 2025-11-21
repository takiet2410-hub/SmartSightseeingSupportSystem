import httpx
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")

async def get_current_weather(city_name: str):
    """
    Lấy thời tiết hiện tại theo tên thành phố/tỉnh.
    """
    if not city_name or not API_KEY:
        return None
    
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city_name, # Tìm theo tên tỉnh
        "appid": API_KEY,
        "units": "metric", # Độ C
        "lang": "vi" # Trả về mô tả tiếng Việt
    }
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=3.0)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "temp": data["main"]["temp"],
                    "description": data["weather"][0]["description"].capitalize(),
                    "icon": data["weather"][0]["icon"] # Dùng để hiện ảnh: http://openweathermap.org/img/wn/{icon}.png
                }
            else:
                print(f"Weather API Error for {city_name}: {resp.status_code}")
                return None
        except Exception as e:
            print(f"Weather Exception: {e}")
            return None