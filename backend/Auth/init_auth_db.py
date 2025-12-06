from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load biến môi trường
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "SmartTourismDB"
COLLECTION_NAME = "Users"

def init_db():
    print("⏳ Đang kết nối MongoDB...")
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        
        # 1. Kiểm tra xem collection đã có chưa
        collection_names = db.list_collection_names()
        if COLLECTION_NAME not in collection_names:
            db.create_collection(COLLECTION_NAME)
            print(f"✅ Đã tạo Collection: {COLLECTION_NAME}")
        else:
            print(f"ℹ️ Collection {COLLECTION_NAME} đã tồn tại.")

        users_col = db[COLLECTION_NAME]

        # 2. DỌN DẸP INDEX CŨ (QUAN TRỌNG)
        # Vì chúng ta đổi logic index, cần xóa index cũ đi để tránh lỗi "IndexOptionsConflict"
        try:
            # Thử xóa index tên "unique_username_idx" (nếu bạn đã chạy script cũ)
            users_col.drop_index("unique_username_idx")
            print("🧹 Đã xóa index cũ 'unique_username_idx'.")
        except:
            # Nếu chưa có thì thôi, bỏ qua
            pass
            
        try:
            # Thử xóa index mặc định "username_1" (nếu có)
            users_col.drop_index("username_1")
            print("🧹 Đã xóa index cũ 'username_1'.")
        except:
            pass

        # 3. TẠO INDEX KÉP MỚI (COMPOUND INDEX)
        # Logic: Cặp (username + auth_provider) phải là duy nhất.
        # Ví dụ: ("a@gmail.com", "local") khác ("a@gmail.com", "google").
        
        index_name = users_col.create_index(
            [("username", 1), ("auth_provider", 1)], 
            unique=True, 
            name="unique_user_provider_idx"
        )
        
        print(f"✅ Đã tạo Index Kép (Username + Provider). Tên index: {index_name}")
        print("🎉 Database Auth đã sẵn sàng cho mô hình Tách Biệt Tài Khoản!")

    except Exception as e:
        print(f"❌ Lỗi: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    if not MONGO_URI:
        print("❌ Lỗi: Chưa cấu hình MONGO_URI trong file .env")
    else:
        init_db()