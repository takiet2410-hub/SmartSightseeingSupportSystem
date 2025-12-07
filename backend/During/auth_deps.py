# auth_deps.py

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from core.config import JWT_SECRET_KEY, JWT_ALGORITHM
from typing import Optional

# Sử dụng HTTPBearer thay vì APIKeyHeader
# auto_error=False: Nếu không có header Authorization, nó trả về None thay vì lỗi 403
security = HTTPBearer(auto_error=False)

def get_current_user_id(token: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[str]:
    # 1. Kiểm tra nếu không có token được gửi lên
    if not token:
        return None

    try:
        # 2. Lấy chuỗi JWT thực tế
        # HTTPBearer tự động tách "Bearer " ra, nên token.credentials chính là chuỗi JWT sạch
        jwt_token = token.credentials 

        # 3. Decode token (Tạm thời bỏ verify signature như logic cũ)
        payload = jwt.decode(jwt_token, options={"verify_signature": False})

        user_id = payload.get("sub") or payload.get("user_id")

        if not user_id:
            return None 

        return user_id

    except Exception:
        # Token không hợp lệ (hết hạn, sai định dạng...), trả về None
        return None