from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from core.config import settings
# SỬA DÒNG NÀY: Import hàm get_users_collection
from core.db import get_users_collection 
from bson import ObjectId

# Token URL này trỏ về Auth Server (nếu chạy local thì là localhost:8000/auth/login)
# Nhưng ở Resource Server, swagger UI chỉ cần biết format token thôi.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login-proxy")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 1. Giải mã Token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
        
    # 2. (Optional) Kiểm tra user có tồn tại trong DB không
    # Vì bạn đã tách Auth và Resource, Resource server vẫn kết nối chung DB nên check được.
    
    # users_col = get_users_collection() # <--- Gọi hàm để lấy collection
    # if not users_col.find_one({"_id": ObjectId(user_id)}):
    #     raise credentials_exception
        
    return user_id