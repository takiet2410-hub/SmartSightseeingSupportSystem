import pytest
from unittest.mock import patch, MagicMock
import json
from modules.generation import call_llm_api, parse_llm_response

# --- 1. TEST HÀM PARSE (XỬ LÝ LOGIC JSON) ---

def test_parse_llm_response_success():
    """Test trường hợp AI trả về JSON chuẩn"""
    # Giả lập string JSON mà AI trả về
    valid_json_str = """
    {
        "recommendations": [
            {"name": "Hồ Gươm", "reason": "Đẹp"}
        ]
    }
    """
    result = parse_llm_response(valid_json_str)
    
    assert "recommendations" in result
    assert result["recommendations"][0]["name"] == "Hồ Gươm"
    assert "error" not in result

def test_parse_llm_response_invalid_json():
    """Test trường hợp AI trả về văn bản thường (lỗi format)"""
    # AI trả về linh tinh, thiếu ngoặc
    bad_json_str = "Đây là gợi ý của tôi: Hồ Gươm..." 
    
    result = parse_llm_response(bad_json_str)
    
    # Hàm parse phải bắt được lỗi và trả về dict chứa key "error"
    assert "error" in result
    assert result["error"] == "Invalid JSON from Gemini"

# --- 2. TEST HÀM GỌI API (MOCK GOOGLE GEMINI) ---

@patch("modules.generation.model") # Giả lập cái biến 'model' trong file generation.py
def test_call_llm_api_success(mock_model):
    """Test gọi hàm call_llm_api thành công"""
    
    # 1. Cấu hình Mock trả về object có thuộc tính .text
    mock_response = MagicMock()
    mock_response.text = '{"status": "ok"}'
    
    # Khi gọi model.generate_content(...), nó sẽ trả về mock_response
    mock_model.generate_content.return_value = mock_response
    
    # 2. Gọi hàm cần test
    result_text = call_llm_api("Test prompt")
    
    # 3. Kiểm tra kết quả
    assert result_text == '{"status": "ok"}'
    
    # Kiểm tra xem hàm generate_content có thực sự được gọi không
    mock_model.generate_content.assert_called_once_with("Test prompt")

@patch("modules.generation.model")
def test_call_llm_api_failure(mock_model):
    """Test trường hợp gọi Google API bị lỗi (mất mạng/hết quota)"""
    
    # 1. Cấu hình Mock để QUĂNG LỖI (Raise Exception)
    mock_model.generate_content.side_effect = Exception("API Quota Exceeded")
    
    # 2. Gọi hàm
    result_json_str = call_llm_api("Test prompt")
    
    # 3. Parse ra để kiểm tra
    result = json.loads(result_json_str)
    
    assert "error" in result
    assert "API Quota Exceeded" in result["error"]