import os
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

class Settings:
    # 1. Database Config
    MONGO_URI = os.getenv("MONGO_URI")
    DB_NAME = "SmartTourismDB"
    COLLECTION_NAME = "Users"
    
    # 2. Security Config
    SECRET_KEY = os.getenv("SECRET_KEY") 
    ALGORITHM = os.getenv("ALGORITHM", "HS256") 
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 10080))

    # 3. Google OAuth Config (MỚI THÊM)
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    
    # 4. Facebook OAuth Config (MỚI THÊM)
    FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID")
    FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET")

# Kiểm tra nhanh: Nếu thiếu biến quan trọng thì báo lỗi
if not Settings.MONGO_URI:
    raise ValueError("❌ Lỗi: Thiếu biến MONGO_URI")

if not Settings.SECRET_KEY:
    raise ValueError("❌ Lỗi: Thiếu biến SECRET_KEY")
    
# Kiểm tra luôn Google Client ID để tránh quên
if not Settings.GOOGLE_CLIENT_ID:
    print("⚠️ CẢNH BÁO: Thiếu GOOGLE_CLIENT_ID. Tính năng đăng nhập Google sẽ không hoạt động.")

settings = Settings()