import os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from dotenv import load_dotenv

load_dotenv()

# Lấy cấu hình giống bên Auth
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

# OAuth2 scheme chỉ để Swagger UI hiển thị nút "Authorize"
# URL này trỏ về Service Auth đang chạy ở port 8001
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://localhost:8001/auth/login")

def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    """
    Hàm này chỉ làm 1 việc: Kiểm tra Token có đúng chữ ký SECRET_KEY không.
    Nếu đúng -> Trả về User ID.
    Không cần truy vấn Database User.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Giải mã Token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
            
        return user_id
        
    except JWTError:
        raise credentials_exception