# history_detail.py
from fastapi import APIRouter, Depends, HTTPException
import shared_resources
from auth_deps import get_current_user_id
from core.config import BEFORE_COLLECTION, HISTORY_COLLECTION

router = APIRouter(tags=["History Read"])


# ======================================================
# 1) API: SUMMARY LIST — dùng để render thumbnail list
# ======================================================
@router.get("/history/summary")
def history_summary(user_id: str = Depends(get_current_user_id)):
    # ... (Giữ nguyên phần check user)
    col = shared_resources.db[HISTORY_COLLECTION] 
    doc = col.find_one({"user_id": user_id})

    if not doc or "history" not in doc:
        return [] 

    summary_list = []

    for item in doc["history"]:
        summary_list.append({
            "landmark_id": item.get("landmark_id"),
            "name": item.get("name"), 
            "user_image_url": item.get("user_image_url"), # [SỬA] Trả về URL
            "timestamp": item.get("timestamp"),
            "similarity_score": item.get("similarity_score"),
        })

    return summary_list


# ======================================================
# 2) API: DETAIL — dùng cho trang thông tin chi tiết
# ======================================================
@router.get("/history/detail/{landmark_id}")
def history_detail(
    landmark_id: str,
    user_id: str = Depends(get_current_user_id)
):
    if not user_id:
        raise HTTPException(401, "Authentication required to view history.")
        
    col = shared_resources.db[HISTORY_COLLECTION] # Sử dụng biến config
    doc = col.find_one({"user_id": user_id})

    if not doc:
        raise HTTPException(404, "User has no history.")

    # Lấy item user đã detect
    target = next(
        (x for x in doc.get("history", []) if x["landmark_id"] == landmark_id),
        None
    )
    
    # CHÚ Ý: Logic này chỉ tìm kiếm landmark_id đầu tiên khớp. 
    # Nếu user detect cùng một địa danh nhiều lần, nó chỉ trả về record đầu tiên tìm thấy.
    # Để chắc chắn, bạn có thể cân nhắc dùng _id của history item nếu có, nhưng ở đây ta dùng landmark_id.

    if not target:
        # Nếu không tìm thấy landmark_id trong lịch sử của user này
        raise HTTPException(404, "History item not found or not detected by this user.")

    # Metadata từ BEFORE_COLLECTION (đảm bảo lấy thông tin mới nhất)
    before = shared_resources.db[BEFORE_COLLECTION]
    info = before.find_one(
        {"landmark_id": landmark_id},
        {"_id": 0, "text_chunk": 0, "v_hybrid": 0, "combined_tags_array": 0}
    )

    if not info:
        # Rất hiếm khi xảy ra, trừ khi dữ liệu gốc bị xóa
        raise HTTPException(404, "Landmark metadata not found.")    

    # Main image from BEFORE_COLLECTION
    image_urls = info.get("image_urls", [])
    # Lấy ảnh thứ 2 (hoặc ảnh thứ 1 nếu chỉ có 1 ảnh) từ metadata gốc
    matched_image_url = image_urls[1] if len(image_urls) > 1 else (image_urls[0] if image_urls else None)

    # Response format
    return {
        "status": "success",
        "landmark_id": landmark_id,
        "name": info.get("name"), 
        "user_image_url": target.get("user_image_url"), # [SỬA] Trả về URL
        "timestamp": target.get("timestamp"),
        "similarity_score": target.get("similarity_score"),
        "matched_image_url": matched_image_url,
        "landmark_info": info, 
    }