import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "SmartTourismDB") 

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Collections
album_collection = db["Albums"]
summary_collection = db["TripSummaries"]