# config.py

import os
from dotenv import load_dotenv
import torch

# 1. Xác định vị trí
current_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(current_dir, '.env')

# --- ĐOẠN DEBUG BẮT ĐẦU (Xóa sau khi fix xong) ---
print(f"🔍 DEBUG: Đang tìm file .env tại: {dotenv_path}")
if os.path.exists(dotenv_path):
    print("✅ DEBUG: Đã tìm thấy file .env!")
else:
    print("❌ DEBUG: KHÔNG tìm thấy file .env! Hãy kiểm tra lại tên file hoặc vị trí.")
    # Liệt kê các file đang có trong thư mục để xem bạn có đặt nhầm tên không
    print(f"📂 Các file hiện có trong thư mục '{current_dir}':")
    print(os.listdir(current_dir))
# --- ĐOẠN DEBUG KẾT THÚC ---

load_dotenv(dotenv_path=dotenv_path)

# 2. Lùi ra 3 cấp để về thư mục gốc (Project Root)
# core -> During -> backend -> ROOT
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))

# 3. Nối với folder data
# Kết quả chuẩn: .../SmartSightseeingSupportSystem/data/Image_Dataset.csv
CSV_FILE = os.path.join(project_root, "data", "Image_Dataset.csv")

# Kiểm tra xem file có tồn tại không (Debug)
if not os.path.exists(CSV_FILE):
    print(f"⚠️ CẢNH BÁO: Không tìm thấy file tại {CSV_FILE}")

# ----------------------------------------------------
# --- BIẾN MÔI TRƯỜNG CHO DATABASE ---
# ----------------------------------------------------
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
DURING_COLLECTION = os.getenv("DURING_COLLECTION")
BEFORE_COLLECTION = os.getenv("BEFORE_COLLECTION")

# ----------------------------------------------------
# --- BỔ SUNG: BIẾN MÔI TRƯỜNG CHO MODEL DINOV2 ---
# ----------------------------------------------------
MODEL_NAME = os.getenv("MODEL_NAME")
MODEL_PATH = os.getenv("MODEL_PATH")
DEVICE_PREF = os.getenv("DEVICE_PREF") # Lấy giá trị ưu tiên

# ----------------------------------------------------
# --- BIẾN MÔI TRƯỜNG CHO JWT AUTH ---
# ----------------------------------------------------
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")

if not JWT_SECRET_KEY or not JWT_ALGORITHM:
    raise EnvironmentError("❌ Thiếu JWT_SECRET_KEY hoặc JWT_ALGORITHM trong .env")

# Quyết định DEVICE cuối cùng dựa trên điều kiện môi trường
DEVICE = DEVICE_PREF if torch.cuda.is_available() and DEVICE_PREF == "cuda" else "cpu"

# --- BIẾN KHÁC ---
BATCH_SIZE = 100 # Kích thước lô mặc định

# --- KIỂM TRA BẮT BUỘC ---
required_vars = [
    MONGO_URI, DB_NAME, DURING_COLLECTION, BEFORE_COLLECTION,
    MODEL_NAME, MODEL_PATH, DEVICE_PREF, JWT_SECRET_KEY, JWT_ALGORITHM # BỔ SUNG: Kiểm tra các biến model
]

if not all(required_vars):
    required_names = [
        "MONGO_URI", "DB_NAME", "DURING_COLLECTION", "BEFORE_COLLECTION",
        "MODEL_NAME", "MODEL_PATH", "DEVICE_PREF", "JWT_SECRET_KEY", "JWT_ALGORITHM"
    ]
    missing_vars = [name for name, val in zip(required_names, required_vars) if not val]
    raise EnvironmentError(
        f"❌ Vui lòng kiểm tra lại file .env! Các biến sau là bắt buộc nhưng chưa được tìm thấy hoặc chưa có giá trị: {', '.join(missing_vars)}"
    )

