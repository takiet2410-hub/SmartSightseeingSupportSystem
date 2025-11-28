# config.py

import os
from dotenv import load_dotenv

# Tự động tải các biến từ file .env
load_dotenv()
# 1. Lấy vị trí hiện tại của file config.py này
# Kết quả: .../SmartSightseeingSupportSystem/backend/During/core
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Lùi ra 3 cấp để về thư mục gốc (Project Root)
# core -> During -> backend -> ROOT
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))

# 3. Nối với folder data
# Kết quả chuẩn: .../SmartSightseeingSupportSystem/data/Image_Dataset.csv
CSV_FILE = os.path.join(project_root, "data", "Image_Dataset.csv")

# Kiểm tra xem file có tồn tại không (Debug)
if not os.path.exists(CSV_FILE):
    print(f"⚠️ CẢNH BÁO: Không tìm thấy file tại {CSV_FILE}")


# --- BIẾN MÔI TRƯỜNG CHO DATABASE ---
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")

# --- BIẾN KHÁC ---
BATCH_SIZE = 100 # Kích thước lô mặc định

if not MONGO_URI or not DB_NAME or not COLLECTION_NAME:
    raise EnvironmentError(
        "❌ Vui lòng kiểm tra lại file .env! Các biến MONGO_URI, DB_NAME, COLLECTION_NAME là bắt buộc."
    )