from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth

app = FastAPI(title="Auth Service")

# Cấu hình CORS (Để Frontend gọi được)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Production nên sửa thành domain của Vercel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gắn router vào app
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])

@app.get("/")
def root():
    return {"message": "Auth Service is running!"}


from fastapi.responses import HTMLResponse

# Endpoint này sẽ hiển thị giao diện khi người dùng click link trong email
@app.get("/demo-reset-password", response_class=HTMLResponse)
async def demo_reset_page(token: str):
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Demo Đặt Lại Mật Khẩu</title>
        <style>
            body {{ font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f4f4f4; }}
            .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); width: 350px; }}
            input {{ width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }}
            button {{ width: 100%; padding: 10px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; }}
            button:hover {{ background: #218838; }}
            .message {{ margin-top: 10px; text-align: center; font-size: 0.9em; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2 style="text-align: center">Đặt lại mật khẩu</h2>
            <form id="resetForm">
                <input type="hidden" id="token" value="{token}">
                
                <label>Mật khẩu mới:</label>
                <input type="password" id="new_password" required placeholder="Nhập mật khẩu mới">
                
                <label>Xác nhận mật khẩu:</label>
                <input type="password" id="confirm_password" required placeholder="Nhập lại mật khẩu">
                
                <button type="submit">Đổi mật khẩu</button>
            </form>
            <div id="responseMessage" class="message"></div>
        </div>

        <script>
            document.getElementById('resetForm').addEventListener('submit', async function(e) {{
                e.preventDefault();
                
                const token = document.getElementById('token').value;
                const newPass = document.getElementById('new_password').value;
                const confirmPass = document.getElementById('confirm_password').value;
                const msgDiv = document.getElementById('responseMessage');

                // Gọi API Reset Password thật của bạn
                try {{
                    const response = await fetch('/auth/reset-password', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            token: token,
                            new_password: newPass,
                            confirm_password: confirmPass
                        }})
                    }});

                    const data = await response.json();

                    if (response.ok) {{
                        msgDiv.style.color = 'green';
                        msgDiv.innerText = "Thành công: " + data.message;
                        // Vô hiệu hóa nút sau khi thành công
                        document.querySelector('button').disabled = true;
                    }} else {{
                        msgDiv.style.color = 'red';
                        msgDiv.innerText = "Lỗi: " + (data.detail || 'Có lỗi xảy ra');
                    }}
                }} catch (error) {{
                    msgDiv.style.color = 'red';
                    msgDiv.innerText = "Lỗi kết nối tới Server";
                    console.error(error);
                }}
            }});
        </script>
    </body>
    </html>
    """
    return html_content

from fastapi.responses import HTMLResponse

# Endpoint này khớp với link trong ảnh: GET /reset-password
@app.get("/reset-password", response_class=HTMLResponse)
async def serve_reset_password_page(token: str):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Đặt lại mật khẩu</title>
        <style>
            body {{ font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #f0f2f5; }}
            .card {{ background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 100%; max-width: 400px; }}
            input {{ width: 100%; padding: 0.8rem; margin-bottom: 1rem; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }}
            button {{ width: 100%; padding: 0.8rem; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }}
            button:hover {{ background: #0056b3; }}
            .msg {{ margin-top: 1rem; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2 style="text-align:center; margin-top:0">Tạo mật khẩu mới</h2>
            <form onsubmit="handleReset(event)">
                <label>Mật khẩu mới</label>
                <input type="password" id="new_pass" required>
                <label>Nhập lại mật khẩu</label>
                <input type="password" id="confirm_pass" required>
                <button type="submit" id="btn">Xác nhận</button>
            </form>
            <div id="message" class="msg"></div>
        </div>

        <script>
            async function handleReset(event) {{
                event.preventDefault();
                const btn = document.getElementById('btn');
                const msg = document.getElementById('message');
                const newPass = document.getElementById('new_pass').value;
                const confirmPass = document.getElementById('confirm_pass').value;
                
                // Lấy token từ URL hiện tại
                const urlParams = new URLSearchParams(window.location.search);
                const token = urlParams.get('token');

                btn.disabled = true;
                btn.innerText = "Đang xử lý...";

                try {{
                    // Gọi vào API thật: /auth/reset-password
                    const response = await fetch('http://localhost:8000/auth/reset-password', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            token: token,
                            new_password: newPass,
                            confirm_password: confirmPass
                        }})
                    }});

                    const data = await response.json();

                    if (response.ok) {{
                        msg.style.color = 'green';
                        msg.innerText = "Thành công! Bạn có thể đăng nhập ngay.";
                    }} else {{
                        msg.style.color = 'red';
                        msg.innerText = data.detail || "Có lỗi xảy ra.";
                        btn.disabled = false;
                        btn.innerText = "Xác nhận";
                    }}
                }} catch (error) {{
                    msg.style.color = 'red';
                    msg.innerText = "Lỗi kết nối server!";
                    btn.disabled = false;
                    btn.innerText = "Xác nhận";
                }}
            }}
        </script>
    </body>
    </html>
    """


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)