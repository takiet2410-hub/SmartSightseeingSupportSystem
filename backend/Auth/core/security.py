from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from core.config import settings

# Cấu hình băm mật khẩu (Hashing)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    """Kiểm tra mật khẩu nhập vào có khớp với hash trong DB không"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Băm mật khẩu trước khi lưu vào DB"""
    return pwd_context.hash(password)

def create_access_token(data: dict):
    """Tạo JWT Token (Thẻ bài)"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Payload chứa thông tin user và thời gian hết hạn
    to_encode.update({"exp": expire})
    
    # Ký tên đóng dấu bằng SECRET_KEY
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt