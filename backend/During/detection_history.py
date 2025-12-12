from fastapi import APIRouter, Depends, HTTPException, Body
from datetime import datetime
from zoneinfo import ZoneInfo
import shared_resources
import cloudinary.uploader 
import io
import hashlib 
from core.config import HISTORY_COLLECTION, TEMP_HISTORY_COLLECTION
from auth_deps import get_current_user_id
from typing import Optional

router = APIRouter(tags=["History Management"])

# Helper tính MD5 Hash của ảnh
def get_image_hash(image_bytes: bytes) -> str:
    return hashlib.md5(image_bytes).hexdigest()

def upload_image_to_cloud(image_bytes: bytes) -> str:
    try:
        upload_result = cloudinary.uploader.upload(io.BytesIO(image_bytes))
        return upload_result.get("secure_url") 
    except Exception as e:
        print(f"Error uploading image: {e}")
        return None

# =========================================================================
# 1. ADD RECORD (CHÍNH THỨC) - [SỬA] Thêm existing_hash
# =========================================================================
def add_history_record(
    user_id: str, 
    landmark_data: dict, 
    landmark_name: str,
    uploaded_image_bytes: Optional[bytes] = None,
    existing_url: Optional[str] = None, 
    existing_hash: Optional[str] = None, # [NEW] Nhận hash từ sync
    custom_timestamp: Optional[str] = None 
):
    col = shared_resources.db[HISTORY_COLLECTION]
    user_doc = col.find_one({"user_id": user_id})
    history_list = user_doc.get("history", []) if user_doc else []
    
    # 1. Xác định Hash hiện tại
    # Ưu tiên lấy hash có sẵn (từ sync), nếu không thì tính từ ảnh mới
    current_image_hash = None
    if existing_hash:
        current_image_hash = existing_hash
    elif uploaded_image_bytes:
        current_image_hash = get_image_hash(uploaded_image_bytes)

    vn_time = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")) 
    timestamp = custom_timestamp if custom_timestamp else vn_time.isoformat()
    
    # --- CHECK DUPLICATE ---
    for i, item in enumerate(history_list):
        if item["landmark_id"] == landmark_data["landmark_id"]:
            # So sánh URL
            url_match = existing_url and item.get("user_image_url") == existing_url
            
            # So sánh Hash (Bây giờ cả Sync và Direct đều có hash để so sánh)
            # item.get("image_hash") có thể None với data cũ, nên cần check cẩn thận
            hash_match = False
            if current_image_hash and item.get("image_hash"):
                hash_match = item.get("image_hash") == current_image_hash
            
            if url_match or hash_match:
                # DUPLICATE -> Move to top
                duplicate_record = history_list.pop(i)
                duplicate_record["timestamp"] = timestamp
                # Cập nhật hash mới nếu record cũ chưa có (để fix data cũ luôn)
                if current_image_hash and not duplicate_record.get("image_hash"):
                    duplicate_record["image_hash"] = current_image_hash
                
                history_list.insert(0, duplicate_record)
                
                if user_doc:
                    col.update_one({"user_id": user_id}, {"$set": {"history": history_list}})
                return 

    # --- ADD NEW RECORD ---
    user_image_url = None
    if existing_url:
        user_image_url = existing_url
    elif uploaded_image_bytes:
        user_image_url = upload_image_to_cloud(uploaded_image_bytes)
    
    if not user_image_url:
        return 

    new_record = {
        "landmark_id": landmark_data["landmark_id"],
        "name": landmark_name,
        "user_image_url": user_image_url,
        "image_hash": current_image_hash, # Luôn lưu hash (dù là sync hay direct)
        "timestamp": timestamp,
        "similarity_score": landmark_data.get("similarity_score", 0),
    }

    if not user_doc:
        col.insert_one({
            "user_id": user_id,
            "created_at": datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")),
            "history": [new_record]
        })
    else:
        history_list.insert(0, new_record)
        col.update_one({"user_id": user_id}, {"$set": {"history": history_list}})

# =========================================================================
# 2. ADD TEMP RECORD (TẠM THỜI)
# =========================================================================
def add_temp_record(temp_id: str, landmark_data: dict, uploaded_image_bytes: bytes, landmark_name: str):
    
    col = shared_resources.db[TEMP_HISTORY_COLLECTION]
    temp_doc = col.find_one({"temp_id": temp_id})
    
    current_image_hash = get_image_hash(uploaded_image_bytes)
    # Lấy giờ hiện tại theo múi giờ Hồ Chí Minh
    current_time_iso = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat()

    history_list = temp_doc.get("history", []) if temp_doc else []
    
    # Check Duplicate
    for i, item in enumerate(history_list):
        if (item["landmark_id"] == landmark_data["landmark_id"] and 
            item.get("image_hash") == current_image_hash):
            
            duplicate_record = history_list.pop(i)
            duplicate_record["timestamp"] = current_time_iso
            history_list.insert(0, duplicate_record)
            
            col.update_one({"temp_id": temp_id}, {"$set": {"history": history_list}})
            return 

    # New Record
    user_image_url = upload_image_to_cloud(uploaded_image_bytes)
    if not user_image_url:
        return

    new_record = {
        "landmark_id": landmark_data["landmark_id"],
        "name": landmark_name,
        "user_image_url": user_image_url,
        "image_hash": current_image_hash,
        "timestamp": current_time_iso,
        "similarity_score": landmark_data.get("similarity_score", 0),
    }

    if not temp_doc:
        col.insert_one({
            "temp_id": temp_id,
            "created_at": datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")),
            "history": [new_record]
        })
    else:
        history_list.insert(0, new_record)
        col.update_one({"temp_id": temp_id}, {"$set": {"history": history_list}})

# =========================================================================
# 3. API: SYNC / MIGRATE - [SỬA] Truyền image_hash
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
            existing_url=item.get("user_image_url"), 
            existing_hash=item.get("image_hash"), # [NEW] Truyền hash từ temp sang chính
            custom_timestamp=item["timestamp"]          
        )

    temp_col.delete_one({"temp_id": temp_id})

    return {"status": "synced", "count": len(temp_history)}