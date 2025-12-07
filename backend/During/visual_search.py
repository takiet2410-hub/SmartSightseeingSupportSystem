# visual_search.py

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from PIL import Image
import io
# Đã sửa lỗi: Cần import Optional để khai báo kiểu dữ liệu cho user_id
from typing import Optional 
from auth_deps import get_current_user_id 
import shared_resources 
from detection_history import add_history_record
from core.config import BEFORE_COLLECTION, DURING_COLLECTION
import torch

router = APIRouter(tags=["Sightseeing Recognition"])

@router.post("/visual-search")
async def visual_search_endpoint(
    file: UploadFile = File(...),
    # Sửa: Đặt kiểu trả về là Optional[str] để chấp nhận None từ auth_deps.py
    user_id: Optional[str] = Depends(get_current_user_id) 
):
    if shared_resources.model is None: 
        raise HTTPException(503, "Model service is currently unavailable.")
    if shared_resources.db is None: 
        raise HTTPException(503, "Database connection failed.")

    # 1. Read image
    try:
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
    except Exception:
        raise HTTPException(400, "Invalid image file format or corruption.")

    # 2. Embed & Search
    try:
        query_vector = shared_resources.embed_image(image)
        search_results = shared_resources.search_similar_landmark(
            query_vector, 
            collection_name=DURING_COLLECTION, 
            limit=1
        )
    except Exception as e:
        raise HTTPException(500, detail=f"Processing or search failed: {e}")

    if not search_results or search_results[0]["score"] < 0.6:
        return {"status": "not_found", "message": "Low confidence or no match."}

    best_match = search_results[0]
    landmark_id = best_match["landmark_id"]

    # 3. Lookup metadata
    before_col = shared_resources.db[BEFORE_COLLECTION]
    # Lấy thêm trường 'name' để lưu vào lịch sử
    landmark_info = before_col.find_one(
        {"landmark_id": landmark_id},
        {"_id": 0, "text_chunk": 0, "v_hybrid": 0, "combined_tags_array": 0} 
    )
    if not landmark_info:
        return {"status": "missing_info", "message": "Metadata not found"}

    response_data = {
        "landmark_info": landmark_info
    }

    # 4. Lưu vào lịch sử (truyền thêm ảnh người dùng)
    # Hàm này sẽ được gọi CHỈ KHI user_id có tồn tại (vì Depend là bắt buộc)
    # Tuy nhiên, theo yêu cầu 1, user không đăng nhập vẫn sử dụng được.
    # Ta cần chỉnh sửa auth_deps.get_current_user_id để cho phép user_id là None, hoặc chỉ gọi khi user_id có giá trị.
    
    # Giả sử user_id có thể là None nếu auth_deps được điều chỉnh:
    # Nếu user_id tồn tại (user đã đăng nhập), ta mới lưu lịch sử
    if user_id:
        add_history_record(
            user_id=user_id,
            landmark_data=response_data,
            uploaded_image_bytes=image_data,
            landmark_name=landmark_info.get("name", "Unknown Landmark") # Truyền tên để lưu vào lịch sử
        )

    return response_data