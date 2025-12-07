import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

# [QUAN TRỌNG] Sửa dòng này
# Ưu tiên lấy từ .env, nếu không có thì mặc định vào "SmartTourismDB"
DB_NAME = os.getenv("DB_NAME", "SmartTourismDB") 

# Kết nối
client = MongoClient(MONGO_URI)
db = client[DB_NAME] # Lúc này nó sẽ trỏ đúng vào SmartTourismDB

# Collection Albums
album_collection = db["Albums"]