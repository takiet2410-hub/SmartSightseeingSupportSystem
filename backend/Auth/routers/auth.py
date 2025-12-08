# routers/auth.py
from fastapi import APIRouter, HTTPException, status
from schemas import UserAuth, Token, GoogleAuth, UserRegister
from core.db import user_collection
from core.config import settings
from core.security import get_password_hash, verify_password, create_access_token

import requests # <--- Import thư viện này để gọi API Facebook
from schemas import FacebookAuth # <--- Import Schema mới

# Thư viện cho Google OAuth
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

import uuid
from datetime import datetime, timedelta
from schemas import ForgotPasswordRequest, ResetPasswordRequest
from core.email_utils import send_reset_email, send_verification_email

router = APIRouter()

# --- 1. API ĐĂNG KÝ TÀI KHOẢN THƯỜNG ---
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserRegister):
    # Logic mới: Chỉ kiểm tra trùng nếu cùng là 'local'
    # Cho phép a@gmail.com (local) và a@gmail.com (google) cùng tồn tại
    # 1. Kiểm tra trùng Username local
    if user_collection.find_one({"username": user.username, "auth_provider": "local"}):
        raise HTTPException(status_code=400, detail="Username này đã được sử dụng.")

    # 2. Kiểm tra trùng Email recover (Bắt buộc, 1 email ko được dùng cho 2 nick)
    if user_collection.find_one({"email_recover": user.email}):
        raise HTTPException(status_code=400, detail="Email này đã được sử dụng.")
    

    # Băm mật khẩu
    hashed_password = get_password_hash(user.password)
    
    # Tạo Verification Token
    verification_token = str(uuid.uuid4())

    # Lưu vào MongoDB
    new_user = {
        "username": user.username,
        "password": hashed_password,
        "auth_provider": "local", 
        "full_name": user.username.split("@")[0], # Lấy tên tạm từ email
        "created_at": None,
        "email_recover": user.email,

        "is_active": False,  # Mặc định chưa kích hoạt
        "verification_token": verification_token
    }
    user_collection.insert_one(new_user)
    
    # Gửi Email xác thực
    try:
        await send_verification_email(user.email, verification_token)
    except Exception as e:
        print(f"Lỗi gửi mail verification: {e}")
        # Tùy chọn: Có thể xóa user vừa tạo nếu gửi mail lỗi để họ đk lại
        raise HTTPException(status_code=500, detail="Lỗi gửi email xác thực.")

    return {"message": "Đăng ký thành công! Vui lòng kiểm tra email để kích hoạt tài khoản."}

# --- 1.1 THÊM API XÁC THỰC EMAIL (Endpoint Mới) ---
@router.get("/verify-email")
async def verify_email_endpoint(token: str):
    # Tìm user có token tương ứng
    user = user_collection.find_one({"verification_token": token})
    
    if not user:
        raise HTTPException(status_code=400, detail="Token kích hoạt không hợp lệ hoặc đã được sử dụng.")
    
    # Kích hoạt tài khoản và xóa token
    user_collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"is_active": True},
            "$unset": {"verification_token": ""} # Xóa token để không dùng lại được
        }
    )
    
    # Trả về thông báo hoặc Redirect về trang Login của Frontend
    # return RedirectResponse("http://localhost:3000/login?verified=true")
    return {"message": "Tài khoản đã được kích hoạt thành công! Bạn có thể đăng nhập ngay bây giờ."}

# --- 2. API ĐĂNG NHẬP THƯỜNG (Login Local) ---
@router.post("/login", response_model=Token)
async def login(user: UserAuth):
    # Logic mới: Chỉ tìm user local
    db_user = user_collection.find_one({
        "username": user.username,
        "auth_provider": "local"
    })
    
    # Kiểm tra user & password
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai tài khoản hoặc mật khẩu",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # --- THÊM ĐOẠN CHECK NÀY ---
    # Nếu trường is_active là False thì chặn lại
    # Dùng .get("is_active", True) để tương thích ngược với các user cũ (coi như đã active)
    if not db_user.get("is_active", True): 
        raise HTTPException(
            status_code=400,
            detail="Tài khoản chưa được kích hoạt. Vui lòng kiểm tra email."
        )

    # Tạo Token
    user_id = str(db_user["_id"])
    access_token = create_access_token(data={"sub": user_id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": db_user["username"],
        "auth_provider": "local",
        "user_id": user_id,
        "full_name": db_user.get("full_name", "")
    }

# --- 3. API ĐĂNG NHẬP GOOGLE (Login Google) ---
@router.post("/google", response_model=Token)
async def login_google(body: GoogleAuth):
    token = body.token
    if not token:
        raise HTTPException(400, "Thiếu Google Token")

    try:
        # Verify Token Google
        id_info = id_token.verify_oauth2_token(
            token, 
            google_requests.Request(), 
            settings.GOOGLE_CLIENT_ID
        )
        
        email = id_info.get('email')
        name = id_info.get('name')
        
        # Logic mới: Chỉ tìm user google
        db_user = user_collection.find_one({
            "username": email,
            "auth_provider": "google"
        })
        
        if db_user:
            # Đã có tk Google -> Đăng nhập
            user_id = str(db_user["_id"])
            username = db_user["username"]
            full_name = db_user.get("full_name", name)
            
        else:
            # Chưa có tk Google -> Tạo mới (Dù đã có tk Local cũng kệ nó)
            new_user = {
                "username": email,
                "full_name": name,
                "password": None, # Không có pass
                "auth_provider": "google",
                "created_at": None,
                "email_recover": None,

                "is_active": True # Google thì luôn Active
            }
            result = user_collection.insert_one(new_user)
            user_id = str(result.inserted_id)
            username = email
            full_name = name
            
        # Tạo Token
        access_token = create_access_token(data={"sub": user_id})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": username,
            "auth_provider": "google",
            "user_id": user_id,
            "full_name": full_name
        }

    except ValueError:
        raise HTTPException(400, "Token Google không hợp lệ")
    except Exception as e:
        print(f"Google Login Error: {e}")
        raise HTTPException(500, "Lỗi xác thực Google")
    


# --- 4. API QUÊN MẬT KHẨU (Gửi Email) ---
@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    # 1. Tìm user theo username và phải là local
    user = user_collection.find_one({
        "username": body.username,
        "auth_provider": "local"
    })
    
    # 2. Kiểm tra tồn tại
    if not user:
        raise HTTPException(status_code=404, detail="Tài khoản không tồn tại.")

    # 3. KIỂM TRA KHỚP EMAIL (Logic bạn muốn)
    # Lấy email trong DB so với email người dùng nhập lên
    # DB: caulac2004@gmail.com  VS  Input: caulac2004@gmail.com
    if user.get("email_recover") != body.email:
        raise HTTPException(status_code=400, detail="Email cung cấp không khớp với tài khoản này.")
    

    # 4. Tạo Reset Token
    reset_token = str(uuid.uuid4())
    
    # 5. Lưu Token vào DB (Hết hạn sau 15 phút)
    user_collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "reset_token": reset_token,
                "reset_token_exp": datetime.utcnow() + timedelta(minutes=15)
            }
        }
    )
    
    # 6. Gửi Email thật
    try:
        await send_reset_email(body.email, reset_token)
    except Exception as e:
        print(f"Lỗi gửi mail: {e}")
        raise HTTPException(status_code=500, detail="Lỗi hệ thống gửi mail.")
        
    return {"message": "Đã gửi email hướng dẫn. Vui lòng kiểm tra hộp thư."}


# --- 5. API ĐẶT LẠI MẬT KHẨU (Đổi Pass) ---
@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    # 1. Tìm user có token này
    user = user_collection.find_one({"reset_token": body.token})
    
    if not user:
        raise HTTPException(status_code=400, detail="Token không hợp lệ hoặc đã sử dụng.")
        
    # 2. Kiểm tra hạn sử dụng
    if user.get("reset_token_exp") < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token đã hết hạn.")
        
    # 3. Kiểm tra pass nhập lại
    if body.new_password != body.confirm_password:
         raise HTTPException(status_code=400, detail="Mật khẩu nhập lại không khớp.")

    # 4. Băm mật khẩu mới
    hashed_pw = get_password_hash(body.new_password)
    
    # 5. Cập nhật & Xóa token
    user_collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"password": hashed_pw},
            "$unset": {"reset_token": "", "reset_token_exp": ""}
        }
    )
    
    return {"message": "Đặt lại mật khẩu thành công. Hãy đăng nhập lại."}


# --- 6. API ĐĂNG NHẬP FACEBOOK (MỚI THÊM) ---
@router.post("/facebook", response_model=Token)
async def login_facebook(body: FacebookAuth):
    """
    Frontend gửi Access Token của Facebook lên.
    Backend gọi sang Facebook để kiểm tra token đó có hợp lệ không và lấy info user.
    """
    token = body.access_token
    if not token:
        raise HTTPException(400, "Thiếu Facebook Access Token")

    # 1. Gọi Facebook Graph API để lấy thông tin User
    facebook_url = "https://graph.facebook.com/me"
    params = {
        "access_token": token,
        "fields": "id,name,email,picture" # Yêu cầu trả về id, tên, email, ảnh
    }
    
    try:
        response = requests.get(facebook_url, params=params)
        data = response.json()
        
        # Nếu token lỗi, Facebook trả về key 'error'
        if "error" in data:
            raise HTTPException(400, detail="Token Facebook không hợp lệ hoặc đã hết hạn")
            
        # Lấy thông tin
        fb_id = data.get("id")
        name = data.get("name")
        email = data.get("email") # Lưu ý: Một số acc FB đk bằng sđt sẽ không có email
        
        # Nếu không có email, ta dùng FB ID làm username giả lập
        final_username = email if email else f"fb_{fb_id}"

        # 2. Logic tìm User trong DB (Tương tự Google)
        # Chỉ tìm user có auth_provider là 'facebook'
        db_user = user_collection.find_one({
            "username": final_username, # Tìm theo email (hoặc fb_id)
            "auth_provider": "facebook"
        })

        if db_user:
            # User đã tồn tại -> Đăng nhập
            user_id = str(db_user["_id"])
            full_name = db_user.get("full_name", name)
        else:
            # User chưa tồn tại -> Tạo mới
            new_user = {
                "username": final_username,
                "full_name": name,
                "password": None, # Không có pass
                "auth_provider": "facebook",
                "facebook_id": fb_id, # Lưu thêm ID gốc của FB để chắc chắn
                "created_at": datetime.utcnow(),
                "email_recover": email, # Có thể None nếu FB ko trả về
                "is_active": True # Facebook thì luôn Active
            }
            result = user_collection.insert_one(new_user)
            user_id = str(result.inserted_id)
            full_name = name

        # 3. Tạo Token nội bộ (JWT)
        access_token = create_access_token(data={"sub": user_id})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": final_username,
            "auth_provider": "facebook",
            "user_id": user_id,
            "full_name": full_name
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Facebook Login Error: {e}")
        raise HTTPException(status_code=500, detail="Lỗi xác thực Facebook")