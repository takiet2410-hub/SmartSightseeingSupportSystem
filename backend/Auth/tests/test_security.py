# tests/test_security.py
from core.security import verify_password, get_password_hash, create_access_token
from jose import jwt
from core.config import settings

def test_password_hashing():
    password = "secret_password"
    hashed = get_password_hash(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False

def test_jwt_token_generation():
    data = {"sub": "user_123"}
    token = create_access_token(data)
    
    # Giải mã token để kiểm tra nội dung
    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    
    assert decoded["sub"] == "user_123"
    assert "exp" in decoded