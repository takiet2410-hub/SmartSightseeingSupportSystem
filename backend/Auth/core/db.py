from pymongo import MongoClient
from core.config import settings

client = MongoClient(settings.MONGO_URI)
db = client[settings.DB_NAME]
user_collection = db[settings.COLLECTION_NAME]

