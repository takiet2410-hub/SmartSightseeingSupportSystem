from fastapi import APIRouter, Depends, HTTPException
from core.db import get_favorites_collection, get_db_collection 
from deps import get_current_user
from schemas import PaginatedResponse
# [FIX 1] Import thêm timezone
from datetime import datetime, timezone 

router = APIRouter()

# --- 1. LƯU ĐỊA ĐIỂM (LIKE) ---
@router.post("/{landmark_id}")
async def add_favorite(landmark_id: str, current_user_id: str = Depends(get_current_user)):
    # 1. Lấy collection từ hàm getter
    fav_collection = get_favorites_collection() 
    dest_collection = get_db_collection()

    if not dest_collection.find_one({"landmark_id": landmark_id}):
        raise HTTPException(status_code=404, detail="Địa điểm không tồn tại")

    fav_collection.update_one(
        {"user_id": current_user_id, "landmark_id": landmark_id},
        {
            "$set": {
                "user_id": current_user_id,
                "landmark_id": landmark_id,
                "saved_at": datetime.now(timezone.utc)
            }
        },
        upsert=True
    )
    return {"message": "Đã thêm vào mục yêu thích"}

# --- 2. BỎ LƯU (UNLIKE) ---
@router.delete("/{landmark_id}")
async def remove_favorite(landmark_id: str, current_user_id: str = Depends(get_current_user)):
    fav_collection = get_favorites_collection()
    
    result = fav_collection.delete_one({
        "user_id": current_user_id, 
        "landmark_id": landmark_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Địa điểm này chưa được lưu trước đó")
        
    return {"message": "Đã xóa khỏi mục yêu thích"}

# --- 3. XEM DANH SÁCH YÊU THÍCH ---
@router.get("/", response_model=PaginatedResponse)
async def get_my_favorites(current_user_id: str = Depends(get_current_user)):
    fav_collection = get_favorites_collection()
    dest_collection = get_db_collection()
    
    fav_cursor = fav_collection.find({"user_id": current_user_id})
    fav_landmark_ids = [doc["landmark_id"] for doc in fav_cursor]
    
    if not fav_landmark_ids:
         return {
            "data": [], "total": 0, "page": 1, "limit": 0, "total_pages": 0
        }

    projection = {
        "_id": 0, "landmark_id": 1, "name": 1, 
        "location_province": 1, "image_urls": 1, "overall_rating": 1
    }
    
    destinations = list(dest_collection.find(
        {"landmark_id": {"$in": fav_landmark_ids}}, 
        projection
    ))
    
    final_data = []
    for doc in destinations:
        doc["id"] = str(doc.get("landmark_id"))
        final_data.append(doc)

    return {
        "data": final_data,
        "total": len(final_data),
        "page": 1,
        "limit": len(final_data),
        "total_pages": 1
    }

# --- 4. CHECK TRẠNG THÁI ---
@router.get("/check/{landmark_id}")
async def check_is_favorite(landmark_id: str, current_user_id: str = Depends(get_current_user)):
    fav_collection = get_favorites_collection() 
    
    is_fav = fav_collection.find_one({
        "user_id": current_user_id, 
        "landmark_id": landmark_id
    })
    return {"is_favorite": bool(is_fav)}