from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Header
from PIL import Image
import io
import uuid
from typing import Optional
from auth_deps import get_current_user_id
import shared_resources
from detection_history import add_history_record, add_temp_record # Import hàm mới
from core.config import BEFORE_COLLECTION, DURING_COLLECTION
import torch

router = APIRouter(tags=["Sightseeing Recognition"])

@router.post("/visual-search")
async def visual_search_endpoint(
    file: UploadFile = File(...),
    user_id: Optional[str] = Depends(get_current_user_id),
    # [NEW] Nhận temp_id từ header (Frontend gửi lên nếu có)
    x_temp_id: Optional[str] = Header(None, alias="X-Temp-ID") 
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
    landmark_info = before_col.find_one(
        {"landmark_id": landmark_id},
        {"_id": 0, "text_chunk": 0, "v_hybrid": 0, "combined_tags_array": 0} 
    )
    if not landmark_info:
        return {"status": "missing_info", "message": "Metadata not found"}

    # Chuẩn bị data response
    response_data = {
        "status": "success",
        "similarity_score": best_match["score"],
        "landmark_id": landmark_id,
        "matched_image_url": best_match.get("image_url"),
        "landmark_info": landmark_info,
        "temp_id": None # Mặc định
    }

    # 4. LOGIC LƯU LỊCH SỬ (QUAN TRỌNG)
    
    landmark_name = landmark_info.get("name", "Unknown Landmark")

    if user_id:
        # A. USER ĐÃ LOGIN -> Lưu thẳng vào User History
        add_history_record(
            user_id=user_id,
            landmark_data=response_data,
            uploaded_image_bytes=image_data,
            landmark_name=landmark_name
        )
    else:
        # B. USER CHƯA LOGIN -> Lưu vào Temp History
        
        # Nếu Frontend chưa gửi Temp ID, Backend tự tạo một cái mới
        current_temp_id = x_temp_id if x_temp_id else str(uuid.uuid4())
        
        add_temp_record(
            temp_id=current_temp_id,
            landmark_data=response_data,
            uploaded_image_bytes=image_data,
            landmark_name=landmark_name
        )
        
        # Trả về temp_id để Frontend lưu lại (nếu chưa có)
        response_data["temp_id"] = current_temp_id
        response_data["message"] = "Saved to temporary history. Please login to sync."

    return response_data