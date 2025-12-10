# core/email_utils.py
import os
import requests
from pydantic import EmailStr
from dotenv import load_dotenv

load_dotenv()

# Lấy API Key từ biến môi trường
BREVO_API_KEY = os.getenv("BREVO_API_KEY")

# Cấu hình thông tin người gửi (Nên dùng email bạn đã đăng ký Brevo)
SENDER_EMAIL = os.getenv("MAIL_USERNAME", "noreply.smarttourism@gmail.com") 
SENDER_NAME = "Smart Sightseeing Support System"

async def send_email_via_brevo(to_email: str, subject: str, html_content: str):
    """Hàm chung để gửi email qua Brevo API"""
    url = "https://api.brevo.com/v3/smtp/email"
    
    payload = {
        "sender": {
            "name": SENDER_NAME,
            "email": SENDER_EMAIL
        },
        "to": [
            {
                "email": to_email
            }
        ],
        "subject": subject,
        "htmlContent": html_content
    }
    
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }
    
    try:
        # Dùng requests để gửi lệnh POST (HTTP) thay vì SMTP
        response = requests.post(url, json=payload, headers=headers)
        
        # Kiểm tra xem gửi thành công không (Code 201 là thành công)
        if response.status_code == 201:
            print(f"✅ Đã gửi mail thành công tới {to_email}")
            return True
        else:
            print(f"❌ Lỗi gửi mail Brevo: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Lỗi kết nối Brevo: {e}")
        return False

# --- Hàm gửi xác thực tài khoản ---
async def send_verification_email(email: EmailStr, token: str):
    # 👇 THAY LINK NÀY BẰNG LINK DIRECT SPACE CỦA BẠN
    # Cách lấy: Vào Space -> Bấm "Embed this space" -> Copy cái "Direct URL"
    base_url = "https://takiet2410-auth-server.hf.space"
    
    # Link trỏ về API Backend để kích hoạt
    verification_link = f"{base_url}/auth/verify-email?token={token}"
    
    subject = "[Smart Tourism] Kích hoạt tài khoản"
    html_content = f"""
    <html>
        <body>
            <h2>Xin chào!</h2>
            <p>Cảm ơn bạn đã đăng ký. Vui lòng bấm vào link dưới để kích hoạt:</p>
            <a href="{verification_link}" style="padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px;">
                Kích hoạt ngay
            </a>
            <p>Hoặc copy link này: {verification_link}</p>
        </body>
    </html>
    """
    
    return await send_email_via_brevo(email, subject, html_content)

# --- Hàm gửi quên mật khẩu ---
async def send_reset_email(email: EmailStr, token: str):
    base_url = "https://takiet2410-auth-server.hf.space"
    
    # Link trỏ về trang Giao diện HTML (main.py)
    reset_link = f"{base_url}/reset-password?token={token}"
    
    subject = "[Smart Tourism] Đặt lại mật khẩu"
    html_content = f"""
    <html>
        <body>
            <h2>Yêu cầu đặt lại mật khẩu</h2>
            <p>Bấm vào nút bên dưới để tạo mật khẩu mới:</p>
            <a href="{reset_link}" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">
                Đổi mật khẩu
            </a>
            <p>Link hết hạn sau 15 phút.</p>
        </body>
    </html>
    """
    
    return await send_email_via_brevo(email, subject, html_content)
