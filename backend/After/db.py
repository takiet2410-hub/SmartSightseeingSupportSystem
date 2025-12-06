import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME") # Phải chung tên DB với Auth

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Chỉ cần Collection này để lưu Album
album_collection = db["Albums"]