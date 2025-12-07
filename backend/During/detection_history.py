# detection_history.py
from fastapi import APIRouter, Depends, HTTPException, Body
from datetime import datetime
import shared_resources
import cloudinary.uploader # [NEW]
import io
from core.config import HISTORY_COLLECTION, TEMP_HISTORY_COLLECTION
from auth_deps import get_current_user_id
from typing import Optional

router = APIRouter(tags=["History Management"])

# Helper để upload ảnh (Dùng chung cho cả Main và Temp)
def upload_image_to_cloud(image_bytes: bytes) -> str:
    try:
        # Upload file từ bytes
        upload_result = cloudinary.uploader.upload(io.BytesIO(image_bytes))
        return upload_result.get("secure_url") # Trả về URL ảnh
    except Exception as e:
        print(f"Error uploading image: {e}")
        return None

# =========================================================================
# HELPER: ADD RECORD (CHÍNH THỨC)
# =========================================================================
def add_history_record(
    user_id: str, 
    landmark_data: dict, 
    landmark_name: str,
    uploaded_image_bytes: Optional[bytes] = None,
    existing_url: Optional[str] = None, # [SỬA] Đổi từ base64 sang url
    custom_timestamp: Optional[str] = None 
):
    
    # 1. Xử lý ảnh: Ưu tiên dùng URL có sẵn (khi migrate), nếu không thì upload mới
    user_image_url = None
    
    if existing_url:
        user_image_url = existing_url
    elif uploaded_image_bytes:
        # [SỬA] Upload lên Cloud lấy URL thay vì Base64
        user_image_url = upload_image_to_cloud(uploaded_image_bytes)
    
    if not user_image_url:
        return # Không có ảnh thì không lưu (hoặc xử lý lỗi tùy bạn)

    # 2. Xử lý thời gian
    timestamp = custom_timestamp if custom_timestamp else datetime.utcnow().isoformat()
    
    new_record = {
        "landmark_id": landmark_data["landmark_id"],
        "name": landmark_name,
        "user_image_url": user_image_url, # [SỬA] Lưu URL
        "timestamp": timestamp,
        "similarity_score": landmark_data.get("similarity_score", 0),
    }

    col = shared_resources.db[HISTORY_COLLECTION]
    user_doc = col.find_one({"user_id": user_id})

    # Logic Create/Update + LIFO + Duplicate Check
    if not user_doc:
        col.insert_one({
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "history": [new_record]
        })
        return

    history_list = user_doc.get("history", [])
    is_duplicate = False
    
    for i, item in enumerate(history_list):
        # Check duplicate dựa trên ID và URL
        if (item["landmark_id"] == new_record["landmark_id"] and
            item.get("user_image_url") == new_record["user_image_url"]): # [SỬA] Check URL
            
            is_duplicate = True
            duplicate_record = history_list.pop(i)
            duplicate_record["timestamp"] = timestamp 
            history_list.insert(0, duplicate_record)
            break
            
    if not is_duplicate:
        history_list.insert(0, new_record)
        
    col.update_one({"user_id": user_id}, {"$set": {"history": history_list}})

# =========================================================================
# HELPER: ADD TEMP RECORD (TẠM THỜI)
# =========================================================================
def add_temp_record(temp_id: str, landmark_data: dict, uploaded_image_bytes: bytes, landmark_name: str):
    
    # [SỬA] Upload ngay cả khi là Temp (để khi sync không cần upload lại)
    user_image_url = upload_image_to_cloud(uploaded_image_bytes)
    current_time_iso = datetime.utcnow().isoformat()

    new_record = {
        "landmark_id": landmark_data["landmark_id"],
        "name": landmark_name,
        "user_image_url": user_image_url, # [SỬA] Lưu URL
        "timestamp": current_time_iso,
        "similarity_score": landmark_data.get("similarity_score", 0),
    }

    col = shared_resources.db[TEMP_HISTORY_COLLECTION]
    
    col.update_one(
        {"temp_id": temp_id},
        {
            "$push": {
                "history": {
                    "$each": [new_record],
                    "$position": 0 
                }
            },
            "$setOnInsert": {"created_at": datetime.utcnow()} 
        },
        upsert=True
    )

# =========================================================================
# API: SYNC / MIGRATE
# =========================================================================
@router.post("/history/sync")
def sync_temp_history(
    temp_id: str = Body(..., embed=True), 
    user_id: str = Depends(get_current_user_id)
):
    if not user_id:
        raise HTTPException(401, "User must be logged in to sync history.")
    
    temp_col = shared_resources.db[TEMP_HISTORY_COLLECTION]
    temp_doc = temp_col.find_one({"temp_id": temp_id})

    if not temp_doc or "history" not in temp_doc:
        return {"status": "no_data", "message": "No temporary history to sync."}

    temp_history = temp_doc["history"]

    for item in reversed(temp_history):
        add_history_record(
            user_id=user_id,
            landmark_data={
                "landmark_id": item["landmark_id"], 
                "similarity_score": item["similarity_score"]
            },
            landmark_name=item["name"],
            uploaded_image_bytes=None,
            existing_url=item.get("user_image_url"), # [SỬA] Truyền URL cũ sang
            custom_timestamp=item["timestamp"]          
        )

    temp_col.delete_one({"temp_id": temp_id})

    return {"status": "synced", "count": len(temp_history)}