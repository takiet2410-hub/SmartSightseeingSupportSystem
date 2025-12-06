from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader
import jwt
from core.config import JWT_SECRET_KEY, JWT_ALGORITHM

# Header Authorization: Bearer <token>
auth_header = APIKeyHeader(name="Authorization")


def get_current_user_id(token: str = Depends(auth_header)) -> str:
    # Remove "Bearer "
    if token.lower().startswith("bearer "):
        token = token[7:]

    try:
        # ⚠️ TẠM THỜI BỎ VERIFY CHỮ KÝ ĐỂ DEV TEST
        # payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        payload = jwt.decode(token, options={"verify_signature": False})

        user_id = payload.get("sub") or payload.get("user_id")

        if not user_id:
            raise HTTPException(status_code=401, detail="user_id missing in token")

        return user_id

    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
