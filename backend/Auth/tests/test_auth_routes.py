# tests/test_auth_routes.py
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException
from datetime import datetime, timedelta

# --- 1. TEST ĐĂNG KÝ (REGISTER) ---

# Mock DB và Email để không lưu thật và không gửi mail thật
@patch("routers.auth.user_collection")
@patch("routers.auth.send_verification_email", new_callable=AsyncMock)
def test_register_success(mock_send_email, mock_collection, client):
    # 1. Giả lập DB: Không tìm thấy user trùng (return None)
    mock_collection.find_one.return_value = None
    
    payload = {
        "username": "newuser",
        "password": "password123",
        "email": "newuser@example.com"
    }
    
    response = client.post("/auth/register", json=payload)
    
    assert response.status_code == 201
    assert "Đăng ký thành công" in response.json()["message"]
    
    # Kiểm tra xem code có gọi lệnh insert vào DB không
    assert mock_collection.insert_one.called
    # Kiểm tra xem code có gọi hàm gửi mail không
    assert mock_send_email.called

@patch("routers.auth.user_collection")
def test_register_duplicate_username(mock_collection, client):
    # 1. Giả lập DB: Tìm thấy user đã tồn tại
    mock_collection.find_one.side_effect = [{"username": "existing"}, None] 
    # (Lần gọi đầu cho username, lần sau cho email - tuỳ logic find_one của bạn)

    payload = {
        "username": "existing",
        "password": "password123",
        "email": "new@example.com"
    }
    
    response = client.post("/auth/register", json=payload)
    
    assert response.status_code == 400
    assert "Username này đã được sử dụng" in response.json()["detail"]


# --- 2. TEST ĐĂNG NHẬP LOCAL (LOGIN) ---

@patch("routers.auth.user_collection")
@patch("routers.auth.verify_password") # Mock hàm check pass để không cần hash thật
def test_login_success(mock_verify, mock_collection, client):
    # 1. Giả lập DB trả về user hợp lệ
    mock_user = {
        "_id": "123456",
        "username": "testuser",
        "password": "hashed_password",
        "auth_provider": "local",
        "is_active": True
    }
    mock_collection.find_one.return_value = mock_user
    # 2. Giả lập mật khẩu đúng
    mock_verify.return_value = True
    
    payload = {"username": "testuser", "password": "password123"}
    response = client.post("/auth/login", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["auth_provider"] == "local"

@patch("routers.auth.user_collection")
def test_login_inactive_user(mock_collection, client):
    # Giả lập user chưa kích hoạt (is_active = False)
    mock_user = {
        "username": "testuser",
        "password": "hashed_pw",
        "auth_provider": "local",
        "is_active": False 
    }
    mock_collection.find_one.return_value = mock_user
    
    # Cần mock verify_password trả về True ở tầng logic, 
    # nhưng ở đây ta test logic check active sau khi check pass
    with patch("routers.auth.verify_password", return_value=True):
        payload = {"username": "testuser", "password": "password123"}
        response = client.post("/auth/login", json=payload)
        
    assert response.status_code == 400
    assert "chưa được kích hoạt" in response.json()["detail"]


# --- 3. TEST GOOGLE LOGIN ---

@patch("routers.auth.user_collection")
@patch("routers.auth.id_token.verify_oauth2_token") # Mock thư viện Google
def test_google_login_new_user(mock_google_verify, mock_collection, client):
    # 1. Giả lập Google trả về thông tin user hợp lệ
    mock_google_verify.return_value = {
        "email": "google@gmail.com",
        "name": "Google User"
    }
    
    # 2. Giả lập DB: Chưa có user này (Find -> None) -> Phải Insert
    mock_collection.find_one.return_value = None
    # Insert trả về một object có attribute inserted_id
    mock_insert_result = MagicMock()
    mock_insert_result.inserted_id = "new_google_id_123"
    mock_collection.insert_one.return_value = mock_insert_result
    
    payload = {"token": "fake_google_token"}
    response = client.post("/auth/google", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "google@gmail.com"
    assert data["auth_provider"] == "google"
    # Kiểm tra xem code có gọi insert không
    assert mock_collection.insert_one.called


# --- 4. TEST FACEBOOK LOGIN ---

@patch("routers.auth.user_collection")
@patch("routers.auth.requests.get") # Mock thư viện requests gọi sang FB
def test_facebook_login_success(mock_requests_get, mock_collection, client):
    # 1. Giả lập FB trả về JSON thành công
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "id": "fb_12345",
        "name": "Facebook User",
        "email": "fb@example.com"
    }
    mock_requests_get.return_value = mock_resp
    
    # 2. Giả lập DB: User đã tồn tại
    mock_collection.find_one.return_value = {
        "_id": "db_id_999",
        "username": "fb@example.com",
        "auth_provider": "facebook",
        "full_name": "Facebook User"
    }
    
    payload = {"access_token": "fake_fb_token"}
    response = client.post("/auth/facebook", json=payload)
    
    assert response.status_code == 200
    assert response.json()["user_id"] == "db_id_999"


# --- 5. TEST FORGOT PASSWORD ---

@patch("routers.auth.user_collection")
@patch("routers.auth.send_reset_email", new_callable=AsyncMock)
def test_forgot_password_success(mock_send_email, mock_collection, client):
    # 1. User tồn tại và email khớp
    mock_user = {
        "_id": "user_id",
        "username": "forgot_user",
        "email_recover": "me@example.com",
        "auth_provider": "local"
    }
    mock_collection.find_one.return_value = mock_user
    
    payload = {"username": "forgot_user", "email": "me@example.com"}
    response = client.post("/auth/forgot-password", json=payload)
    
    assert response.status_code == 200
    assert "Đã gửi email" in response.json()["message"]
    # Kiểm tra DB có được update token không
    assert mock_collection.update_one.called
    
    # BỔ SUNG: Kiểm tra xem hàm gửi mail có được gọi 1 lần không?
    mock_send_email.assert_called_once() 
    
    # (Nâng cao) Kiểm tra xem có gửi đúng địa chỉ email không?
    # args[0] là tham số đầu tiên truyền vào hàm send_reset_email (chính là email)
    args, _ = mock_send_email.call_args
    assert args[0] == "me@example.com"




# --- 6. TEST VERIFY EMAIL (Xác thực Email) ---
# Mục tiêu: Test các dòng báo lỗi khi Token sai hoặc Email gửi lỗi

@patch("routers.auth.user_collection")
def test_verify_email_invalid_token(mock_collection, client):
    # Case: Token không tìm thấy trong DB
    mock_collection.find_one.return_value = None

    response = client.get("/auth/verify-email?token=token_fake_khong_co_that")

    # Coverage: Dòng "if not user: raise HTTPException..."
    assert response.status_code == 400
    assert "Token không hợp lệ" in response.json()["detail"]

@patch("routers.auth.user_collection")
def test_verify_email_success(mock_collection, client):
    # Case: Token đúng
    mock_user = {"_id": "user_123", "verification_token": "valid_token"}
    mock_collection.find_one.return_value = mock_user

    # Đổi allow_redirects -> follow_redirects
    response = client.get("/auth/verify-email?token=valid_token", follow_redirects=False)

    # Coverage: Dòng "user_collection.update_one(...)" và "return RedirectResponse"
    # 307 là mã chuyển hướng (Redirect)
    assert response.status_code == 307 
    assert response.headers["location"] == "/docs" # Hoặc trang login tùy cấu hình
    
    # Kiểm tra DB đã set is_active = True chưa
    mock_collection.update_one.assert_called_once()
    args, _ = mock_collection.update_one.call_args
    assert args[1]["$set"]["is_active"] is True


# --- 7. TEST GOOGLE LOGIN - CÁC TRƯỜNG HỢP LỖI ---

@patch("routers.auth.id_token.verify_oauth2_token")
def test_google_login_invalid_token(mock_verify, client):
    # Case: Thư viện Google báo lỗi (token rác)
    mock_verify.side_effect = ValueError("Token Signature Invalid")

    response = client.post("/auth/google", json={"token": "bad_token"})

    # Coverage: Dòng "except ValueError: raise HTTPException(400...)"
    assert response.status_code == 400
    assert "Token Google không hợp lệ" in response.json()["detail"]

@patch("routers.auth.id_token.verify_oauth2_token")
def test_google_login_general_error(mock_verify, client):
    # Case: Lỗi hệ thống bất ngờ
    mock_verify.side_effect = Exception("Mất mạng")

    response = client.post("/auth/google", json={"token": "token_gay_loi"})

    # Coverage: Dòng "except Exception: raise HTTPException(500...)"
    assert response.status_code == 500
    assert "Lỗi xác thực Google" in response.json()["detail"]


# --- 8. TEST FACEBOOK LOGIN - CÁC TRƯỜNG HỢP LỖI ---

@patch("routers.auth.requests.get")
def test_facebook_login_api_error(mock_requests, client):
    # Case: Facebook trả về JSON chứa key "error"
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"error": {"message": "Invalid access token"}}
    mock_requests.return_value = mock_resp

    response = client.post("/auth/facebook", json={"access_token": "expired_token"})

    # Coverage: Dòng "if 'error' in data: raise HTTPException..."
    assert response.status_code == 400
    assert "Token Facebook không hợp lệ" in response.json()["detail"]


# --- 9. TEST FORGOT PASSWORD - CÁC TRƯỜNG HỢP LỖI ---

@patch("routers.auth.user_collection")
def test_forgot_password_user_not_found(mock_collection, client):
    # Case: Nhập username lung tung
    mock_collection.find_one.return_value = None

    response = client.post("/auth/forgot-password", json={"username": "ghost", "email": "a@a.com"})

    # Coverage: Dòng "if not user: raise HTTPException(404...)"
    assert response.status_code == 404
    assert "Tài khoản không tồn tại" in response.json()["detail"]

@patch("routers.auth.user_collection")
def test_forgot_password_email_mismatch(mock_collection, client):
    # Case: Username đúng nhưng Email sai
    mock_user = {"username": "hacker", "email_recover": "real@gmail.com"}
    mock_collection.find_one.return_value = mock_user

    response = client.post("/auth/forgot-password", json={"username": "hacker", "email": "fake@gmail.com"})

    # Coverage: Dòng "if user.get('email_recover') != body.email..."
    assert response.status_code == 400
    assert "Email cung cấp không khớp" in response.json()["detail"]

@patch("routers.auth.user_collection")
@patch("routers.auth.send_reset_email", new_callable=AsyncMock)
def test_forgot_password_send_mail_fail(mock_send_email, mock_collection, client):
    # Case: User đúng, nhưng server mail bị lỗi
    mock_collection.find_one.return_value = {"username": "u", "email_recover": "e@e.com", "_id": "1"}
    mock_send_email.side_effect = Exception("SMTP Error")

    response = client.post("/auth/forgot-password", json={"username": "u", "email": "e@e.com"})

    # Coverage: Dòng "except Exception as e: raise HTTPException(500...)"
    assert response.status_code == 500
    assert "Lỗi hệ thống gửi mail" in response.json()["detail"]


# --- 10. TEST RESET PASSWORD (ĐẶT LẠI MK) ---

@patch("routers.auth.user_collection")
def test_reset_password_token_expired(mock_collection, client):
    # Case: Token hết hạn
    mock_user = {
        "_id": "u1", 
        "reset_token": "expired_token",
        # Set thời gian hết hạn là quá khứ
        "reset_token_exp": datetime.utcnow() - timedelta(minutes=1)
    }
    mock_collection.find_one.return_value = mock_user

    payload = {
        "token": "expired_token",
        "new_password": "123",
        "confirm_password": "123"
    }
    response = client.post("/auth/reset-password", json=payload)

    # Coverage: Dòng "if user.get('reset_token_exp') < datetime.utcnow()..."
    assert response.status_code == 400
    assert "Token đã hết hạn" in response.json()["detail"]

@patch("routers.auth.user_collection")
def test_reset_password_mismatch(mock_collection, client):
    # Case: 2 mật khẩu không khớp
    # Token vẫn còn hạn
    mock_user = {
        "_id": "u1", 
        "reset_token": "valid",
        "reset_token_exp": datetime.utcnow() + timedelta(minutes=10)
    }
    mock_collection.find_one.return_value = mock_user

    payload = {
        "token": "valid",
        "new_password": "abc",
        "confirm_password": "xyz" # Khác nhau
    }
    response = client.post("/auth/reset-password", json=payload)

    # Coverage: Dòng "if body.new_password != body.confirm_password..."
    assert response.status_code == 400
    assert "Mật khẩu nhập lại không khớp" in response.json()["detail"]

# --- BỔ SUNG: REGISTER CÁC CASE LỖI (HÌNH 2) ---

@patch("routers.auth.user_collection")
def test_register_duplicate_email(mock_collection, client):
    # Case: Username chưa có, nhưng Email ĐÃ có trong DB
    # find_one lần 1 (check username) -> None (ok)
    # find_one lần 2 (check email) -> Có user (trùng)
    mock_collection.find_one.side_effect = [None, {"email_recover": "dup@test.com"}]

    payload = {
        "username": "new_user",
        "password": "123",
        "email": "dup@test.com"
    }
    response = client.post("/auth/register", json=payload)

    assert response.status_code == 400
    assert "Email này đã được sử dụng" in response.json()["detail"]

@patch("routers.auth.user_collection")
@patch("routers.auth.send_verification_email", new_callable=AsyncMock)
def test_register_send_email_fail(mock_send_email, mock_collection, client):
    # Case: Mọi thứ ok, nhưng hàm gửi mail bị lỗi
    mock_collection.find_one.return_value = None # Không trùng
    mock_send_email.side_effect = Exception("SMTP connect fail") # Giả lập lỗi gửi mail

    payload = {
        "username": "user_fail_mail",
        "password": "123",
        "email": "fail@test.com"
    }
    response = client.post("/auth/register", json=payload)

    # Code của bạn catch Exception -> raise 500
    assert response.status_code == 500
    assert "Lỗi gửi email xác thực" in response.json()["detail"]


# --- BỔ SUNG: LOGIN CASE SAI PASS (HÌNH 3) ---

@patch("routers.auth.user_collection")
@patch("routers.auth.verify_password")
def test_login_wrong_password(mock_verify, mock_collection, client):
    # Case: User tìm thấy, nhưng pass sai
    mock_user = {
        "username": "user_ok",
        "password": "hashed_pass",
        "is_active": True
    }
    mock_collection.find_one.return_value = mock_user
    mock_verify.return_value = False # Giả lập pass sai

    response = client.post("/auth/login", json={"username": "user_ok", "password": "wrongpass"})

    assert response.status_code == 401
    assert "Sai tài khoản hoặc mật khẩu" in response.json()["detail"]

@patch("routers.auth.user_collection")
def test_login_user_not_found(mock_collection, client):
    # Case: Không tìm thấy user trong DB
    mock_collection.find_one.return_value = None

    response = client.post("/auth/login", json={"username": "ghost_user", "password": "123"})

    assert response.status_code == 401
    assert "Sai tài khoản hoặc mật khẩu" in response.json()["detail"]

# --- BỔ SUNG: GOOGLE LOGIN (HÌNH 5) ---

@patch("routers.auth.user_collection")
def test_google_login_missing_token(mock_collection, client):
    # Case: Gửi body rỗng hoặc token rỗng
    response = client.post("/auth/google", json={"token": ""})
    
    assert response.status_code == 400
    assert "Thiếu Google Token" in response.json()["detail"]

@patch("routers.auth.user_collection")
@patch("routers.auth.id_token.verify_oauth2_token")
def test_google_login_existing_user(mock_verify, mock_collection, client):
    # Case: User Google ĐÃ CÓ trong DB (đi vào nhánh if db_user)
    mock_verify.return_value = {"email": "old@gmail.com", "name": "Old User"}
    
    mock_existing_user = {
        "_id": "existing_id_123",
        "username": "old@gmail.com",
        "full_name": "Old User",
        "auth_provider": "google"
    }
    mock_collection.find_one.return_value = mock_existing_user

    response = client.post("/auth/google", json={"token": "valid_token"})

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "existing_id_123"
    # Kiểm tra xem nó KHÔNG gọi insert_one (vì user đã có rồi)
    mock_collection.insert_one.assert_not_called()

# --- BỔ SUNG: GOOGLE LOGIN (HÌNH 5) ---

@patch("routers.auth.user_collection")
def test_google_login_missing_token(mock_collection, client):
    # Case: Gửi body rỗng hoặc token rỗng
    response = client.post("/auth/google", json={"token": ""})
    
    assert response.status_code == 400
    assert "Thiếu Google Token" in response.json()["detail"]

@patch("routers.auth.user_collection")
@patch("routers.auth.id_token.verify_oauth2_token")
def test_google_login_existing_user(mock_verify, mock_collection, client):
    # Case: User Google ĐÃ CÓ trong DB (đi vào nhánh if db_user)
    mock_verify.return_value = {"email": "old@gmail.com", "name": "Old User"}
    
    mock_existing_user = {
        "_id": "existing_id_123",
        "username": "old@gmail.com",
        "full_name": "Old User",
        "auth_provider": "google"
    }
    mock_collection.find_one.return_value = mock_existing_user

    response = client.post("/auth/google", json={"token": "valid_token"})

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "existing_id_123"
    # Kiểm tra xem nó KHÔNG gọi insert_one (vì user đã có rồi)
    mock_collection.insert_one.assert_not_called()


# --- BỔ SUNG: RESET PASSWORD SUCCESS (HÌNH 4) ---

@patch("routers.auth.user_collection")
def test_reset_password_success_update(mock_collection, client):
    # Case: Mọi thứ đúng hết -> Update DB
    from datetime import datetime, timedelta
    
    mock_user = {
        "_id": "uid_reset",
        "reset_token": "valid_reset_token",
        # Token còn hạn
        "reset_token_exp": datetime.utcnow() + timedelta(minutes=10)
    }
    mock_collection.find_one.return_value = mock_user

    payload = {
        "token": "valid_reset_token",
        "new_password": "newPass123",
        "confirm_password": "newPass123"
    }
    response = client.post("/auth/reset-password", json=payload)

    assert response.status_code == 200
    assert "thành công" in response.json()["message"]
    
    # Kiểm tra lệnh update_one có được gọi đúng format không
    mock_collection.update_one.assert_called_once()
    args, _ = mock_collection.update_one.call_args
    # Kiểm tra xem có unset token không
    assert "$unset" in args[1]
    assert "reset_token" in args[1]["$unset"]


# --- BỔ SUNG: REGISTER CÁC TRƯỜNG HỢP LỖI ---

@patch("routers.auth.user_collection")
def test_register_duplicate_email(mock_collection, client):
    # Case: Username hợp lệ (chưa có), nhưng Email ĐÃ CÓ
    # find_one được gọi 2 lần:
    # Lần 1: Check username -> trả về None (ok)
    # Lần 2: Check email -> trả về object (báo lỗi trùng)
    mock_collection.find_one.side_effect = [None, {"email_recover": "dup@test.com"}]

    payload = {
        "username": "new_user_ok",
        "password": "123",
        "email": "dup@test.com"
    }
    response = client.post("/auth/register", json=payload)

    assert response.status_code == 400
    assert "Email này đã được sử dụng" in response.json()["detail"]

@patch("routers.auth.user_collection")
@patch("routers.auth.send_verification_email", new_callable=AsyncMock)
def test_register_send_email_fail(mock_send_email, mock_collection, client):
    # Case: DB ok, nhưng hàm gửi mail bị lỗi (Exception)
    mock_collection.find_one.return_value = None # Không trùng username/email
    mock_send_email.side_effect = Exception("SMTP connect fail") # Giả lập lỗi

    payload = {
        "username": "user_mail_fail",
        "password": "123",
        "email": "fail@test.com"
    }
    response = client.post("/auth/register", json=payload)

    # Code catch Exception -> raise 500
    assert response.status_code == 500
    assert "Lỗi gửi email xác thực" in response.json()["detail"]

# --- BỔ SUNG: LOGIN SAI PASS / KHÔNG TỒN TẠI ---

@patch("routers.auth.user_collection")
@patch("routers.auth.verify_password")
def test_login_wrong_password(mock_verify, mock_collection, client):
    # Case: Tìm thấy user, nhưng verify_password trả về False
    mock_user = {
        "username": "user_ok",
        "password": "hashed_pass",
        "is_active": True
    }
    mock_collection.find_one.return_value = mock_user
    mock_verify.return_value = False # Password sai

    response = client.post("/auth/login", json={"username": "user_ok", "password": "wrongpass"})

    assert response.status_code == 401
    assert "Sai tài khoản hoặc mật khẩu" in response.json()["detail"]

@patch("routers.auth.user_collection")
def test_login_user_not_found(mock_collection, client):
    # Case: Không tìm thấy user trong DB (find_one -> None)
    mock_collection.find_one.return_value = None

    response = client.post("/auth/login", json={"username": "ghost", "password": "123"})

    assert response.status_code == 401
    assert "Sai tài khoản hoặc mật khẩu" in response.json()["detail"]

# --- BỔ SUNG: LOGIN SAI PASS / KHÔNG TỒN TẠI ---

@patch("routers.auth.user_collection")
@patch("routers.auth.verify_password")
def test_login_wrong_password(mock_verify, mock_collection, client):
    # Case: Tìm thấy user, nhưng verify_password trả về False
    mock_user = {
        "username": "user_ok",
        "password": "hashed_pass",
        "is_active": True
    }
    mock_collection.find_one.return_value = mock_user
    mock_verify.return_value = False # Password sai

    response = client.post("/auth/login", json={"username": "user_ok", "password": "wrongpass"})

    assert response.status_code == 401
    assert "Sai tài khoản hoặc mật khẩu" in response.json()["detail"]

@patch("routers.auth.user_collection")
def test_login_user_not_found(mock_collection, client):
    # Case: Không tìm thấy user trong DB (find_one -> None)
    mock_collection.find_one.return_value = None

    response = client.post("/auth/login", json={"username": "ghost", "password": "123"})

    assert response.status_code == 401
    assert "Sai tài khoản hoặc mật khẩu" in response.json()["detail"]

# --- BỔ SUNG: GOOGLE LOGIN ---

def test_google_login_missing_token(client):
    # Case: Gửi body rỗng hoặc token rỗng -> Báo lỗi 400
    response = client.post("/auth/google", json={"token": ""})
    assert response.status_code == 400
    assert "Thiếu Google Token" in response.json()["detail"]

@patch("routers.auth.user_collection")
@patch("routers.auth.id_token.verify_oauth2_token")
def test_google_login_existing_user(mock_verify, mock_collection, client):
    # Case: User Google ĐÃ CÓ trong DB (đi vào nhánh if db_user)
    mock_verify.return_value = {"email": "old@gmail.com", "name": "Old Google User"}
    
    mock_existing_user = {
        "_id": "existing_id_123",
        "username": "old@gmail.com",
        "full_name": "Old Google User",
        "auth_provider": "google"
    }
    mock_collection.find_one.return_value = mock_existing_user

    response = client.post("/auth/google", json={"token": "valid_token"})

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "existing_id_123"
    # Quan trọng: Kiểm tra code KHÔNG gọi insert_one (vì đã có user)
    mock_collection.insert_one.assert_not_called()

# --- BỔ SUNG: FACEBOOK LOGIN ---

def test_facebook_login_missing_token(client):
    # Case: Thiếu token -> Báo lỗi 400
    response = client.post("/auth/facebook", json={"access_token": ""})
    assert response.status_code == 400
    assert "Thiếu Facebook Access Token" in response.json()["detail"]

@patch("routers.auth.user_collection")
@patch("routers.auth.requests.get")
def test_facebook_login_new_user_insert(mock_requests, mock_collection, client):
    # Case: FB trả về OK, DB chưa có user -> Phải Insert (nhánh else)
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": "fb_new", "name": "New FB", "email": "new@fb.com"}
    mock_requests.return_value = mock_resp
    
    # DB không tìm thấy user cũ (find_one -> None)
    mock_collection.find_one.return_value = None
    
    # Giả lập kết quả insert thành công
    mock_insert_res = MagicMock()
    mock_insert_res.inserted_id = "new_fb_id_db"
    mock_collection.insert_one.return_value = mock_insert_res

    response = client.post("/auth/facebook", json={"access_token": "token"})

    assert response.status_code == 200
    assert response.json()["user_id"] == "new_fb_id_db"
    # Kiểm tra hàm insert_one ĐÃ ĐƯỢC GỌI
    mock_collection.insert_one.assert_called_once()

@patch("routers.auth.requests.get")
def test_facebook_login_exception(mock_requests, client):
    # Case: Lỗi bất ngờ (Exception chung)
    mock_requests.side_effect = Exception("Crash connect FB")

    response = client.post("/auth/facebook", json={"access_token": "token"})

    # Code catch Exception -> raise 500
    assert response.status_code == 500
    assert "Lỗi xác thực Facebook" in response.json()["detail"]

# --- BỔ SUNG: RESET PASSWORD ---

@patch("routers.auth.user_collection")
def test_reset_password_token_not_found(mock_collection, client):
    # Case: Token không tồn tại
    mock_collection.find_one.return_value = None
    
    response = client.post("/auth/reset-password", json={
        "token": "bad_token", "new_password": "1", "confirm_password": "1"
    })
    
    assert response.status_code == 400
    assert "Token không hợp lệ" in response.json()["detail"]

@patch("routers.auth.user_collection")
def test_reset_password_success_update(mock_collection, client):
    # Case: Update thành công (Cover đoạn update_one bị đỏ)
    from datetime import datetime, timedelta
    
    mock_user = {
        "_id": "uid_reset",
        "reset_token": "valid_reset_token",
        # Token còn hạn (tương lai)
        "reset_token_exp": datetime.utcnow() + timedelta(minutes=10)
    }
    mock_collection.find_one.return_value = mock_user

    payload = {
        "token": "valid_reset_token",
        "new_password": "newPass123",
        "confirm_password": "newPass123"
    }
    response = client.post("/auth/reset-password", json=payload)

    assert response.status_code == 200
    assert "thành công" in response.json()["message"]
    
    # Kiểm tra lệnh update_one có được gọi để lưu pass mới và xóa token
    mock_collection.update_one.assert_called_once()
    args, _ = mock_collection.update_one.call_args
    # Kiểm tra xem có field $set (pass) và $unset (token) không
    assert "$set" in args[1]
    assert "$unset" in args[1]