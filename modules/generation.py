import google.generativeai as genai
from core.config import settings
from typing import Dict, Any
import json

# 1. Cấu hình Gemini ngay khi load file
try:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    # Cấu hình model với chế độ JSON cưỡng ép
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL_NAME,
        generation_config={
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
            "response_mime_type": "application/json", # <--- TÍNH NĂNG QUAN TRỌNG NHẤT
        }
    )
except Exception as e:
    print(f"⚠️ Cảnh báo: Không thể cấu hình Gemini. Kiểm tra API KEY. Lỗi: {e}")

def build_rag_prompt(context: str, user_query: str) -> str:
    template = """
    Bạn là trợ lý du lịch AI chuyên về Việt Nam.
    
    Nhiệm vụ: Dựa vào danh sách địa điểm trong phần "Context", hãy chọn ra 3 địa điểm phù hợp nhất với "User Query".

    User Query: "{user_query}"
    
    Context (Dữ liệu DB):
    ---
    {context}
    ---
    
    QUY TẮC BẮT BUỘC:
    1. NGÔN NGỮ: 100% Tiếng Việt. Nếu Context có từ tiếng Anh (ví dụ: "Hiking"), PHẢI DỊCH sang tiếng Việt ("Leo núi").
    2. TRUNG THỰC VỚI DỮ LIỆU:
       - Tên địa điểm ("name") phải COPY Y NGUYÊN từ Context (kể cả viết hoa/thường). KHÔNG được sửa tên.
    3. OUTPUT FORMAT: Bạn đang chạy ở chế độ JSON Output, hãy trả về JSON khớp với Schema sau:
    
    {{
        "recommendations": [
            {{
                "rank": 1,
                "name": "Tên y hệt trong Context",
                "justification_summary": "Giải thích lý do chọn địa điểm này dựa trên context bằng tiếng Việt",
                "suggested_activities": ["Hoạt động 1 (Tiếng Việt)", "Hoạt động 2"]
            }},
             {{
                "rank": 2,
                "name": "Tên y hệt trong Context",
                "justification_summary": "Giải thích lý do chọn địa điểm này dựa trên context bằng tiếng Việt",
                "suggested_activities": ["Hoạt động 1 (Tiếng Việt)", "Hoạt động 2"]
            }},
             {{
                "rank": 3,
                "name": "Tên y hệt trong Context",
                "justification_summary": "Giải thích lý do chọn địa điểm này dựa trên context bằng tiếng Việt",
                "suggested_activities": ["Hoạt động 1 (Tiếng Việt)", "Hoạt động 2"]
            }}
        ]
    }}
    """
    return template.format(user_query=user_query, context=context)

def call_llm_api(prompt: str) -> str:
    """
    Gọi Gemini API
    """
    try:
        # Gemini chat session hoặc generate_content
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        # Trả về JSON rỗng báo lỗi để hàm parse xử lý
        return json.dumps({"error": f"Gemini API Error: {str(e)}"})

def parse_llm_response(response_str: str) -> Dict[str, Any]:
    """
    Parse kết quả từ Gemini.
    Vì Gemini đã bật 'response_mime_type': 'application/json', 
    nó đảm bảo 99.99% trả về JSON chuẩn, không cần cắt gọt chuỗi phức tạp.
    """
    try:
        # Gemini đôi khi trả về dư khoảng trắng, strip cho chắc
        clean_str = response_str.strip()
        return json.loads(clean_str)
    except json.JSONDecodeError:
        print(f"JSON Error. Raw response: {response_str}")
        return {"error": "Invalid JSON from Gemini", "raw_response": response_str}
    except Exception as e:
        return {"error": f"Parse Error: {str(e)}"}