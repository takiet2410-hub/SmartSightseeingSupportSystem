from fastapi import FastAPI, UploadFile, File, HTTPException
from sentence_transformers import SentenceTransformer
from pymongo import MongoClient
from PIL import Image
import io
from config import MONGO_URI, DB_NAME, COLLECTION_NAME, DESTINATION_NAME # Tận dụng file config cũ

# 1. Khởi tạo App & Database
app = FastAPI()

try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    img_collection = db[COLLECTION_NAME]       # Collection chứa Vector ảnh
    info_collection = db[DESTINATION_NAME]       # Collection chứa thông tin địa điểm (Module Before)
    print("✅ Kết nối MongoDB thành công")
except Exception as e:
    print(f"❌ Lỗi kết nối DB: {e}")

# 2. Load Model CLIP (Chỉ load 1 lần khi khởi động server)
print("⏳ Đang tải model CLIP...")
model = SentenceTransformer('clip-ViT-B-32')
print("✅ Model đã sẵn sàng.")

# --- HÀM TÌM KIẾM CORE ---
def search_similar_landmark(query_vector, limit=1):
    """
    Thực hiện Vector Search trên MongoDB Atlas
    """
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",           # Tên Index bạn đặt trên Atlas
                "path": "embedding",       # Tên field chứa vector
                "queryVector": query_vector,  # Vector của ảnh người dùng
                "numCandidates": 100,         # Số lượng ứng viên quét qua (càng cao càng chính xác nhưng chậm)
                "limit": limit                # Số lượng kết quả trả về
            }
        },
        {
            "$project": {
                "_id": 0,
                "landmark_id": 1,
                "image_url": 1,
                "score": {"$meta": "vectorSearchScore"} # Lấy điểm tương đồng
            }
        }
    ]
    
    results = list(img_collection.aggregate(pipeline))
    return results

# --- API ENDPOINT ---
@app.post("/visual-search")
async def visual_search(file: UploadFile = File(...)):
    # B1: Đọc ảnh từ User upload
    try:
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
    except Exception:
        raise HTTPException(status_code=400, detail="File không phải là ảnh hợp lệ")

    # B2: Vector hóa ảnh (Embedding)
    query_vector = model.encode(image).tolist()

    # B3: Tìm kiếm vector gần nhất trong DB
    search_results = search_similar_landmark(query_vector, limit=1)

    if not search_results:
        return {"message": "Không tìm thấy địa điểm tương đồng."}

    best_match = search_results[0]
    
    # --- LOGIC QUAN TRỌNG: THRESHOLDING (NGƯỠNG) ---
    # Nếu độ giống < 0.6 (ví dụ), có thể user up ảnh mèo/chó chứ không phải cảnh
    if best_match['score'] < 0.60: 
         return {
             "status": "not_found",
             "message": "Ảnh không giống địa điểm du lịch nào trong hệ thống.",
             "similarity_score": best_match['score']
         }

    # B4: Lấy thông tin chi tiết từ Module Before (Dùng landmark_id)
    landmark_id = best_match['landmark_id']
    landmark_id_str = str(landmark_id)

    print(f"🔍 Đang tìm ID: '{landmark_id_str}' (Type: {type(landmark_id_str)})")
    # Query bảng thông tin (giả sử bạn có collection 'destinations')
    landmark_info = info_collection.find_one(
        {"landmark_id": landmark_id_str}, 
        {"_id": 0, "embedding_text": 0} # Ẩn các trường không cần thiết
    )

    if not landmark_info:
        return {"message": "Tìm thấy ảnh giống nhưng không có thông tin chi tiết cho ID f{landmark_id_str}."}

    # B5: Trả về kết quả
    return {
        "status": "success",
        "similarity_score": best_match['score'],
        "matched_image_url": best_match['image_url'], # Trả về ảnh gốc trong DB để user so sánh
        "data": landmark_info # Tên, địa chỉ, mô tả...
    }
