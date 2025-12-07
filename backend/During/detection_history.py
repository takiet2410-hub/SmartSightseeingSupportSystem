# detection_history.py (New File/Logic)
from datetime import datetime
import base64
import shared_resources
from core.config import HISTORY_COLLECTION

# Đặt router ở đây nếu bạn muốn định nghĩa thêm các API liên quan đến lịch sử
# Tuy nhiên, trong cấu trúc này, history_summary.py đã làm việc đó.
# Ta chỉ cần định nghĩa hàm helper:

def add_history_record(user_id: str, landmark_data: dict, uploaded_image_bytes: bytes, landmark_name: str):
    """
    Lưu bản ghi nhận diện vào lịch sử của người dùng.
    Sử dụng cơ chế LIFO: mục mới nhất/được cập nhật sẽ lên đầu danh sách.
    Kiểm tra duplicate: nếu landmark_id, score và ảnh base64 giống nhau,
    chỉ cập nhật timestamp và đẩy lên đầu (không thêm bản ghi mới).
    """
    
    # 1. Chuẩn bị dữ liệu cho bản ghi mới
    
    # Chuyển ảnh người dùng sang Base64
    user_image_base64 = base64.b64encode(uploaded_image_bytes).decode('utf-8')
    current_time_iso = datetime.utcnow().isoformat()
    
    new_record = {
        "landmark_id": landmark_data["landmark_id"],
        "name": landmark_name,
        "user_image_base64": user_image_base64,
        "timestamp": current_time_iso,
        "similarity_score": landmark_data["similarity_score"],
    }

    # 2. Truy cập MongoDB
    col = shared_resources.db[HISTORY_COLLECTION] # HISTORY_COLLECTION = "Detection_History"

    # Tìm kiếm bản ghi lịch sử của user
    user_doc = col.find_one({"user_id": user_id})

    # 3. Xử lý Lịch sử (Create/Update/Push)
    if not user_doc:
        # Trường hợp 1: User chưa có lịch sử
        col.insert_one({
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "history": [new_record]
        })
        return

    # Trường hợp 2: User đã có lịch sử. Tìm kiếm duplicate và xử lý LIFO.
    history_list = user_doc.get("history", [])
    
    # Tiêu chí Duplicate: landmark_id + user_image_base64 + similarity_score
    is_duplicate = False
    
    for i, item in enumerate(history_list):
        if (item["landmark_id"] == new_record["landmark_id"] and
            item["user_image_base64"] == new_record["user_image_base64"] and
            abs(item["similarity_score"] - new_record["similarity_score"]) < 1e-6): # So sánh float an toàn hơn
            
            # Đánh dấu duplicate và cập nhật timestamp
            is_duplicate = True
            
            # Loại bỏ bản ghi cũ khỏi vị trí hiện tại
            duplicate_record = history_list.pop(i) 
            
            # Cập nhật timestamp mới
            duplicate_record["timestamp"] = current_time_iso
            
            # Đẩy bản ghi đã cập nhật lên đầu danh sách (LIFO)
            history_list.insert(0, duplicate_record)
            break
            
    if not is_duplicate:
        # Nếu không phải duplicate, thêm bản ghi mới vào đầu danh sách (LIFO)
        history_list.insert(0, new_record)
        
    # Cập nhật lại toàn bộ danh sách lịch sử trong MongoDB
    col.update_one(
        {"user_id": user_id},
        {"$set": {"history": history_list}}
    )