from fastapi import Depends, HTTPException, status
# 1. Đổi import từ OAuth2PasswordBearer sang HTTPBearer
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials 
from jose import JWTError, jwt
from core.config import settings
from core.db import get_users_collection 
from bson import ObjectId

# 2. Khai báo HTTPBearer thay vì OAuth2PasswordBearer
# security này không cần tokenUrl, nên Swagger sẽ chỉ hiện ổ nhập Token
security = HTTPBearer()

async def get_current_user(token_obj: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 3. Lấy chuỗi token từ object trả về
    # HTTPBearer trả về object có dạng: { scheme: "Bearer", credentials: "..." }
    token = token_obj.credentials 

    try:
        # Phần logic giải mã giữ nguyên như cũ
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
        
    # (Optional) Kiểm tra user trong DB (giữ nguyên code cũ của bạn)
    # users_col = get_users_collection()
    # if not users_col.find_one({"_id": ObjectId(user_id)}):
    #     raise credentials_exception
        
    return user_id