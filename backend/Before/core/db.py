from pymongo import MongoClient
from core.config import settings

class Database:
    def __init__(self):
        try:
            self.client = MongoClient(settings.MONGO_DB_URL)
            self.db = self.client[settings.MONGO_DB_NAME]
            
            # Khởi tạo các Collection
            self.destinations = self.db[settings.DESTINATIONS_COLLECTION]
            self.users = self.db["Users"]       # Collection Users
            self.favorites = self.db["Favorites"] # Collection Favorites
            
            print("Connected to MongoDB Atlas successfully!")
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
            self.client = None
            self.db = None
            self.destinations = None
            self.users = None
            self.favorites = None

    def get_collection(self):
        return self.destinations

    def get_users_collection(self):
        return self.users

    def get_favorites_collection(self):
        return self.favorites

db_client = Database()

# --- CÁC HÀM GETTER (Export ra để các file khác dùng) ---

def get_db_collection():
    return db_client.get_collection()

def get_users_collection(): # <--- deps.py sẽ import hàm này
    return db_client.get_users_collection()

def get_favorites_collection(): # <--- favourite.py sẽ import hàm này
    return db_client.get_favorites_collection()