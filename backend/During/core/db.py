# db.py

from pymongo import MongoClient
from config import MONGO_URI, DB_NAME, DURING_COLLECTION

def get_mongo_collection(client=None, db_name=DB_NAME, during_collection=DURING_COLLECTION):
    """
    Khởi tạo và trả về đối tượng MongoDB Collection.
    """
    if client is None:
        try:
            # client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            client = MongoClient(MONGO_URI)
            # Kiểm tra kết nối nhanh (tùy chọn)
            client.admin.command('ping')
            print("✅ Đã kết nối thành công đến MongoDB Atlas.")
        except Exception as e:
            print(f"❌ Lỗi kết nối MongoDB: {e}")
            raise ConnectionError("Không thể kết nối tới MongoDB Atlas.")

    db = client[db_name]
    collection = db[during_collection]
    return collection, client