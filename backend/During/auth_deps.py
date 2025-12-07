# auth_deps.py (Đã sửa theo gợi ý trước)

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader
import jwt
from core.config import JWT_SECRET_KEY, JWT_ALGORITHM
from typing import Optional # Quan trọng để hỗ trợ Optional[str]

# Sử dụng auto_error=False để FastAPI không tự động ném lỗi 403 nếu header thiếu
auth_header = APIKeyHeader(name="Authorization", auto_error=False) 

# HÀM NÀY CHO PHÉP TRẢ VỀ user_id HOẶC None
def get_current_user_id(token: Optional[str] = Depends(auth_header)) -> Optional[str]:
    # Nếu không có token nào được gửi, trả về None (cho phép truy cập)
    if not token:
        return None

    # Remove "Bearer "
    if token.lower().startswith("bearer "):
        token = token[7:]

    try:
        # Tạm thời bỏ verify signature (như code gốc của bạn)
        payload = jwt.decode(token, options={"verify_signature": False})

        user_id = payload.get("sub") or payload.get("user_id")

        if not user_id:
            # Token hợp lệ nhưng thiếu user_id, trả về None
            return None 

        return user_id

    except Exception:
        # Token không hợp lệ (hết hạn, sai định dạng), trả về None
        return None