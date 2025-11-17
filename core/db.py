from pymongo import MongoClient
from core.config import settings

class Database:
    def __init__(self):
        try:
            self.client = MongoClient(settings.MONGO_DB_URL)
            self.db = self.client[settings.MONGO_DB_NAME]
            self.destinations = self.db[settings.DESTINATIONS_COLLECTION]
            print("Connected to MongoDB Atlas successfully!")
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
            self.client = None
            self.db = None
            self.destinations = None

    def get_collection(self):
        return self.destinations

# Khởi tạo một instance để các file khác có thể import
db_client = Database()

def get_db_collection():
    return db_client.get_collection()