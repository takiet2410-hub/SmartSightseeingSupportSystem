from sentence_transformers import SentenceTransformer
from PIL import Image
import pandas as pd
import requests
from io import BytesIO
from tqdm import tqdm
import os
from core.db import get_mongo_collection
# Đảm bảo file config.py đã có các biến này
from core.config import CSV_FILE, BATCH_SIZE 


def main():
    # 1. Kết nối MongoDB
    try:
        collection, client = get_mongo_collection()
    except Exception as e:
        print(f"Dừng chương trình do lỗi kết nối: {e}")
        return

    # --- BƯỚC MỚI: KIỂM TRA DỮ LIỆU CŨ ---
    print("🔍 Đang quét Database để tìm dữ liệu đã tồn tại...")
    # Chỉ lấy trường image_id để tiết kiệm băng thông
    # cursor trả về danh sách các dict {'image_id': '...', '_id': ...}
    existing_docs = collection.find({}, {"image_id": 1})
    
    # Tạo một set chứa các ID đã có để tra cứu cho nhanh (O(1))
    existing_ids = set(doc["image_id"] for doc in existing_docs)
    
    print(f"👉 Tìm thấy {len(existing_ids)} ảnh đã có trong Database.")
    if len(existing_ids) > 0:
        print("⚡ Hệ thống sẽ tự động BỎ QUA những ảnh này và chỉ nạp ảnh mới.")
    # -------------------------------------



    # 2. Tải Model CLIP
    print("\n⏳ Đang tải model CLIP (clip-ViT-B-32)...")
    model = SentenceTransformer('clip-ViT-B-32')
    print("✅ Model đã sẵn sàng.")

    # 3. Đọc file CSV
    if not os.path.exists(CSV_FILE):
        print(f"❌ Không tìm thấy file: {CSV_FILE}")
        client.close()
        return
    
    df = pd.read_csv(CSV_FILE)
    if 'image_url' not in df.columns:
        print("❌ Lỗi: File CSV không có cột 'image_url'.")
        client.close()
        return

    print(f"📂 Đã đọc {len(df)} dòng từ file CSV.")

    # 4. Vòng lặp xử lý
    documents_batch = []
    processed_count = 0
    skipped_count = 0
    
    print("🚀 Bắt đầu xử lý...")
    
    for index, row in tqdm(df.iterrows(), total=df.shape[0], desc="Processing"):
        try:
            # Lấy image_id từ file CSV (chuyển sang string để so sánh với DB)
            current_id = str(row['image_id'])
            
            # --- LOGIC BỎ QUA (SKIP) ---
            if current_id in existing_ids:
                skipped_count += 1
                continue 
            # ---------------------------

            url = row['image_url']
            if pd.isna(url) or str(url).strip() == '':
                continue

            # a. Tải ảnh
            response = requests.get(url, timeout=5)
            if response.status_code != 200:
                continue 
                
            img = Image.open(BytesIO(response.content))
            
            # b. Vector hóa
            vector = model.encode(img).tolist()
            
            # c. Tạo Document
            doc = {
                "image_id": current_id,
                "landmark_id": int(row['landmark_id']), 
                "image_url": url,
                "embedding": vector
            }
            
            documents_batch.append(doc)
            processed_count += 1

            # d. Nạp theo lô
            if len(documents_batch) >= BATCH_SIZE:
                collection.insert_many(documents_batch)
                documents_batch = [] # Reset

        except Exception as e:
            continue

    # 5. Nạp nốt số còn lại
    if documents_batch:
        collection.insert_many(documents_batch)

    print("\n" + "="*40)
    print(f"🎉 HOÀN TẤT QUÁ TRÌNH INGEST!")
    print(f"⏭️  Đã bỏ qua (có sẵn): {skipped_count} ảnh")
    print(f"wb  Đã nạp mới thêm   : {processed_count} ảnh")
    print(f"📊 Tổng số trong DB   : {collection.count_documents({})} ảnh")
    print("="*40)
    
    client.close()

if __name__ == "__main__":
    main()