from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth
from fastapi.responses import HTMLResponse

app = FastAPI(title="Auth Service")

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gắn router vào app
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])

@app.get("/")
def root():
    return {"message": "Auth Service is running!"}

# Endpoint hiển thị giao diện Đặt lại mật khẩu
@app.get("/reset-password", response_class=HTMLResponse)
async def serve_reset_password_page(token: str):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Đặt lại mật khẩu</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #f0f2f5; margin: 0; }}
            .card {{ background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 90%; max-width: 400px; }}
            input {{ width: 100%; padding: 0.8rem; margin-bottom: 1rem; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }}
            button {{ width: 100%; padding: 0.8rem; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 1rem; }}
            button:hover {{ background: #0056b3; }}
            button:disabled {{ background: #cccccc; cursor: not-allowed; }}
            .msg {{ margin-top: 1rem; text-align: center; font-size: 0.9rem; }}
            h2 {{ text-align: center; margin-top: 0; color: #333; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>Tạo mật khẩu mới</h2>
            <form onsubmit="handleReset(event)">
                <label style="display:block; margin-bottom: 5px; color: #666;">Mật khẩu mới</label>
                <input type="password" id="new_pass" required placeholder="Nhập mật khẩu mới">
                
                <label style="display:block; margin-bottom: 5px; color: #666;">Nhập lại mật khẩu</label>
                <input type="password" id="confirm_pass" required placeholder="Xác nhận mật khẩu">
                
                <button type="submit" id="btn">Đổi mật khẩu</button>
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

                if (!token) {{
                    msg.style.color = 'red';
                    msg.innerText = "Lỗi: Không tìm thấy Token xác thực.";
                    return;
                }}

                btn.disabled = true;
                btn.innerText = "Đang xử lý...";
                msg.innerText = "";

                try {{
                    // Dùng đường dẫn tương đối (Relative Path) cho môi trường production/hosting
                    const response = await fetch('/auth/reset-password', {{
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
                        msg.innerText = "✅ Thành công! Bạn có thể đăng nhập ngay.";
                        btn.innerText = "Đã đổi xong";
                        // Xóa input sau khi thành công
                        document.getElementById('new_pass').value = "";
                        document.getElementById('confirm_pass').value = "";
                    }} else {{
                        msg.style.color = 'red';
                        msg.innerText = "❌ " + (data.detail || "Có lỗi xảy ra.");
                        btn.disabled = false;
                        btn.innerText = "Đổi mật khẩu";
                    }}
                }} catch (error) {{
                    msg.style.color = 'red';
                    msg.innerText = "❌ Lỗi kết nối server!";
                    console.error(error);
                    btn.disabled = false;
                    btn.innerText = "Đổi mật khẩu";
                }}
            }}
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
