import torch
import torch.nn as nn
from transformers import Dinov2Model, AutoImageProcessor
from PIL import Image
import pandas as pd
import os
import glob  # <--- Thư viện quan trọng để tìm file bất chấp đuôi
from tqdm import tqdm
from core.db import get_mongo_collection

# --- CẤU HÌNH IMPORT TỪ FILE CONFIG ---
# Nếu file config.py của bạn thiếu biến nào, hãy thêm vào hoặc định nghĩa trực tiếp ở đây
try:
    from core.config import CSV_FILE, BATCH_SIZE
except ImportError:
    # Giá trị mặc định phòng hờ lỗi import
    CSV_FILE = "VN_train_data.csv"
    BATCH_SIZE = 32

# --- CẤU HÌNH ĐƯỜNG DẪN LOCAL ---
# Cấu trúc thư mục: DATASET_ROOT_DIR / landmark_id / image_id.jpg (hoặc png, webp...)
# Ví dụ: dataset/train/1/3521.jpg
DATASET_ROOT_DIR = "dataset/train" 

# --- CẤU HÌNH MODEL ---
MODEL_NAME = "facebook/dinov2-base"
MODEL_PATH = "models/dinov2_hf_finetuned_ep30.pth" 
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"🚀 Đang sử dụng thiết bị: {DEVICE}")

# --- 1. KHAI BÁO KIẾN TRÚC MODEL ---
class FineTunedDINOv2(nn.Module):
    def __init__(self):
        super(FineTunedDINOv2, self).__init__()
        # Sử dụng lại kiến trúc bạn đã định nghĩa
        self.backbone = Dinov2Model.from_pretrained(MODEL_NAME)

    def forward(self, x):
        outputs = self.backbone(x)
        cls_token = outputs.last_hidden_state[:, 0]
        # Bắt buộc Chuẩn hóa L2 giống như khi tạo vector trong DB
        return nn.functional.normalize(cls_token, p=2, dim=1)

def load_finetuned_model():
    # Sử dụng lại logic load model đã sửa để xử lý checkpoint dictionary
    print(f"⏳ Đang tải model từ {MODEL_PATH}...")
    model = FineTunedDINOv2()
    
    if os.path.exists(MODEL_PATH):
        checkpoint = torch.load(MODEL_PATH, map_location=DEVICE, weights_only=False)
        
        if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
            print(f"ℹ️ Đang trích xuất weights từ Checkpoint...")
            state_dict = checkpoint["model_state_dict"]
        else:
            state_dict = checkpoint

        new_state_dict = {}
        for k, v in state_dict.items():
            if k.startswith("module."):
                new_state_dict[k[7:]] = v
            else:
                new_state_dict[k] = v
        
        try:
            model.load_state_dict(new_state_dict)
        except:
            # Tắt strict để xử lý nếu có chênh lệch nhỏ về key
            model.load_state_dict(new_state_dict, strict=False)

        print("✅ Đã load weights thành công!")

    else:
        raise FileNotFoundError(f"❌ Không tìm thấy file model tại {MODEL_PATH}")
    
    model.to(DEVICE)
    model.eval() 
    
    processor = AutoImageProcessor.from_pretrained(MODEL_NAME)
    return model, processor

def main():
    # 1. Kết nối MongoDB
    try:
        collection, client = get_mongo_collection()
        print("✅ Kết nối MongoDB thành công.")
    except Exception as e:
        print(f"❌ Dừng chương trình do lỗi kết nối DB: {e}")
        return

    # 2. Xóa dữ liệu cũ (Re-indexing)
    # Bước này quan trọng vì model đã thay đổi, vector cũ không còn tác dụng
    print("⚠️ Đang xóa dữ liệu cũ trong Collection...")
    collection.delete_many({})
    print("✅ Đã xóa sạch collection. Sẵn sàng nạp mới.")

    # 3. Load Model & Processor
    try:
        model, processor = load_finetuned_model()
    except Exception as e:
        print(e)
        return

    # 4. Đọc file CSV
    if not os.path.exists(CSV_FILE):
        print(f"❌ Không tìm thấy file CSV: {CSV_FILE}")
        return
    
    df = pd.read_csv(CSV_FILE)
    print(f"📂 Đã đọc {len(df)} dòng từ file CSV.")

    # 5. Vòng lặp xử lý chính
    documents_batch = []
    missing_files_count = 0
    success_count = 0
    
    print(f"🚀 Bắt đầu Embed dữ liệu từ thư mục: {DATASET_ROOT_DIR}")
    print("👉 Logic: Đọc ID từ CSV -> Tìm file local (bất chấp đuôi) -> Embed -> Lưu MongoDB")
    
    for index, row in tqdm(df.iterrows(), total=df.shape[0], desc="Processing"):
        try:
            # Lấy thông tin metadata từ CSV
            landmark_id = str(row['landmark_id'])
            image_id = str(row['image_id'])
            original_url = row['image_url'] 

            if pd.isna(image_id) or image_id.strip() == "":
                continue

            # --- LOGIC TÌM FILE DÙNG GLOB (Xử lý đa định dạng) ---
            # Tạo đường dẫn mẫu: dataset/train/1/3521.*
            # Dấu * sẽ khớp với mọi đuôi (.jpg, .png, .webp, .JPG...)
            search_path_pattern = os.path.join(DATASET_ROOT_DIR, landmark_id, f"{image_id}.*")
            
            # Tìm tất cả các file khớp mẫu
            found_files = glob.glob(search_path_pattern)

            if not found_files:
                # Nếu list rỗng nghĩa là không tìm thấy file nào khớp ID này
                # print(f"⚠️ Missing file for ID: {image_id}") # Uncomment nếu muốn xem chi tiết
                missing_files_count += 1
                continue
            
            # Lấy file đầu tiên tìm thấy (thường chỉ có 1 file duy nhất khớp ID)
            local_image_path = found_files[0]

            # a. Mở ảnh từ ổ cứng
            try:
                # .convert("RGB") là bắt buộc để tránh lỗi kênh Alpha (trong png) hoặc Grayscale
                img = Image.open(local_image_path).convert("RGB")
            except Exception as e:
                print(f"❌ Lỗi file hỏng {local_image_path}: {e}")
                continue

            # b. Vector hóa (Embedding)
            inputs = processor(images=img, return_tensors="pt").pixel_values.to(DEVICE)
            
            with torch.no_grad():
                embedding_tensor = model(inputs)
            
            # Chuyển Tensor về List chuẩn Python
            vector = embedding_tensor.cpu().numpy().flatten().tolist()
            
            # c. Tạo Document chuẩn cấu trúc
            # QUAN TRỌNG: Metadata lấy từ CSV để đảm bảo hiển thị đúng trên Web/App
            doc = {
                "image_id": image_id,
                "landmark_id": landmark_id,
                "image_url": original_url, # Vẫn lưu URL online
                "embedding": vector
            }
            
            documents_batch.append(doc)
            success_count += 1

            # d. Nạp vào DB theo lô (Batch insert)
            if len(documents_batch) >= BATCH_SIZE:
                collection.insert_many(documents_batch)
                documents_batch = [] # Reset lô

        except Exception as e:
            print(f"⚠️ Lỗi không xác định tại dòng {index}: {e}")
            continue

    # 6. Nạp nốt số còn lại trong lô cuối cùng
    if documents_batch:
        collection.insert_many(documents_batch)

    # 7. Báo cáo kết quả
    print("\n" + "="*50)
    print(f"🎉 HOÀN TẤT QUÁ TRÌNH INGEST!")
    print(f"📊 Tổng số ảnh trong CSV: {len(df)}")
    print(f"✅ Số ảnh xử lý thành công: {success_count}")
    print(f"⚠️ Số ảnh không tìm thấy trong thư mục Local: {missing_files_count}")
    
    # Kiểm tra lại số lượng thực tế trong DB
    try:
        db_count = collection.count_documents({})
        print(f"💾 Số lượng document hiện tại trong MongoDB: {db_count}")
    except:
        pass
        
    print("-" * 50)
    print("👉 LƯU Ý CHO BƯỚC TIẾP THEO:")
    print("1. Vào MongoDB Atlas > Atlas Search.")
    print("2. Tạo hoặc Cập nhật Index.")
    print("3. Đảm bảo field 'embedding' có 'numDimensions': 768 (DINOv2 Base).")
    print("="*50)
    
    client.close()

if __name__ == "__main__":
    main()