import os
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from dotenv import load_dotenv

load_dotenv()

# Cấu hình kết nối (Đọc từ .env)
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_USERNAME"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def send_reset_email(email: EmailStr, token: str):
    # Link trỏ về Frontend (User sẽ bấm vào đây)
    # Bạn nhớ thay đổi http://localhost:3000 thành domain thật khi deploy
    reset_link = f"http://localhost:8000/reset-password?token={token}"
    
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #2c3e50;">Yêu cầu đặt lại mật khẩu</h2>
        <p>Xin chào,</p>
        <p>Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản của bạn.</p>
        <p>Vui lòng bấm vào nút bên dưới để tạo mật khẩu mới (Link hết hạn sau 15 phút):</p>
        
        <a href="{reset_link}" style="background-color: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 0;">
            Đặt lại mật khẩu
        </a>
        
        <p style="color: #7f8c8d; font-size: 0.9em;">Nếu bạn không yêu cầu, vui lòng bỏ qua email này.</p>
        <hr style="border: 0; border-top: 1px solid #eee;" />
        <p style="font-size: 0.8em; color: #999;">Smart Tourism Support Team</p>
    </div>
    """

    message = MessageSchema(
        subject="[Smart Tourism] Hướng dẫn đặt lại mật khẩu",
        recipients=[email],
        body=html,
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    await fm.send_message(message)
    return True


