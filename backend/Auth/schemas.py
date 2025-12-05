# schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional

# 1. Dữ liệu gửi lên khi Đăng nhập THƯỜNG
class UserAuth(BaseModel):
    username: str
    password: str

# 2. Dữ liệu gửi lên khi Đăng ký (Thêm email)
class UserRegister(BaseModel):
    username: str
    password: str
    email: EmailStr  # <--- Bắt buộc nhập email khi đăng ký

# 3. Dữ liệu gửi lên khi Đăng nhập GOOGLE
class GoogleAuth(BaseModel):
    token: str

# 4. Dữ liệu Token trả về cho Frontend (Sau khi login thành công)
class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    auth_provider: str     # local / google
    user_id: str           # ID Mongo (string)
    full_name: Optional[str] = None # Tên hiển thị (VD: Nguyễn Văn A)

# 5. Schema cho User trong Database (Dùng nội bộ nếu cần)
class UserInDB(BaseModel):
    username: str
    full_name: Optional[str] = None
    auth_provider: str

# 6. Dữ liệu gửi lên khi Yêu cầu Quên mật khẩu
class ForgotPasswordRequest(BaseModel):
    username: str
    email: EmailStr

# 7. Dữ liệu gửi lên khi Đặt lại mật khẩu
class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str

# 8. Dữ liệu gửi lên khi Đăng nhập FACEBOOK (MỚI THÊM)
class FacebookAuth(BaseModel):
    access_token: str