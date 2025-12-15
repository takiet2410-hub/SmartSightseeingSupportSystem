import pytest
from unittest.mock import patch, MagicMock
from core.email_utils import send_email_via_brevo, send_verification_email, send_reset_email

# --- 1. TEST HÀM GỐC: send_email_via_brevo ---

@pytest.mark.asyncio
async def test_send_email_via_brevo_success():
    """Test trường hợp gửi mail thành công (API trả về 201)"""
    # Mock requests.post để không gọi API thật
    with patch("core.email_utils.requests.post") as mock_post:
        # Giả lập phản hồi từ Brevo là 201 (Created/Success)
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        # Gọi hàm
        result = await send_email_via_brevo("test@example.com", "Subject", "<h1>Body</h1>")

        # Kiểm tra
        assert result is True
        # Đảm bảo requests.post đã được gọi đúng URL và data
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["to"][0]["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_send_email_via_brevo_api_error():
    """Test trường hợp API Brevo báo lỗi (ví dụ 400 hoặc 401)"""
    with patch("core.email_utils.requests.post") as mock_post:
        # Giả lập phản hồi lỗi (400 Bad Request)
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid API Key"
        mock_post.return_value = mock_response

        result = await send_email_via_brevo("test@example.com", "Subject", "Body")

        # Kiểm tra hàm phải trả về False và in lỗi (cover dòng print lỗi)
        assert result is False

@pytest.mark.asyncio
async def test_send_email_via_brevo_exception():
    """Test trường hợp lỗi mạng hoặc requests bị crash (Exception)"""
    with patch("core.email_utils.requests.post") as mock_post:
        # Giả lập requests.post ném ra Exception
        mock_post.side_effect = Exception("Mất kết nối mạng")

        result = await send_email_via_brevo("test@example.com", "Subject", "Body")

        # Kiểm tra hàm phải trả về False và nhảy vào block except
        assert result is False


# --- 2. TEST HÀM WRAPPER: send_verification_email ---

@pytest.mark.asyncio
async def test_send_verification_email_content():
    """Test xem hàm này có tạo đúng link và gọi hàm gửi mail không"""
    # Mock hàm send_email_via_brevo để chỉ kiểm tra input đầu vào của nó
    with patch("core.email_utils.send_email_via_brevo") as mock_send_func:
        mock_send_func.return_value = True

        email = "user@verify.com"
        token = "token_kich_hoat_123"
        
        await send_verification_email(email, token)

        # Kiểm tra xem hàm send_email_via_brevo có được gọi không
        mock_send_func.assert_called_once()
        
        # Lấy tham số đã truyền vào mock
        call_args = mock_send_func.call_args
        # args[0] là email, args[1] là subject, args[2] là html_content
        args, _ = call_args
        
        assert args[0] == email
        assert "[Smart Tourism] Kích hoạt tài khoản" in args[1]
        
        # QUAN TRỌNG: Kiểm tra trong HTML có chứa đúng Link kèm token không
        expected_link = f"token={token}"
        assert expected_link in args[2]
        assert "takiet2410-auth-server.hf.space" in args[2]


# --- 3. TEST HÀM WRAPPER: send_reset_email ---

@pytest.mark.asyncio
async def test_send_reset_email_content():
    """Test xem hàm gửi quên mật khẩu có tạo đúng link không"""
    with patch("core.email_utils.send_email_via_brevo") as mock_send_func:
        mock_send_func.return_value = True

        email = "user@reset.com"
        token = "token_reset_pass_abc"
        
        await send_reset_email(email, token)

        mock_send_func.assert_called_once()
        
        # Lấy tham số kiểm tra
        args, _ = mock_send_func.call_args
        
        assert args[0] == email
        assert "[Smart Tourism] Đặt lại mật khẩu" in args[1]
        
        # Kiểm tra link reset
        expected_link = f"/reset-password?token={token}"
        assert expected_link in args[2]