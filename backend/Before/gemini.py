import google.generativeai as genai
import os
from dotenv import load_dotenv

# 1. Load API Key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Lỗi: Chưa tìm thấy GEMINI_API_KEY trong file .env")
    # Nếu test nhanh, bạn có thể gán cứng key vào đây (nhớ xóa sau khi test):
    # api_key = "AIzaSy..." 
    exit()

# 2. Cấu hình
genai.configure(api_key=api_key)

print(f"--- ĐANG KIỂM TRA CÁC MODEL KHẢ DỤNG ---")

try:
    # 3. Gọi hàm list_models()
    found_any = False
    for m in genai.list_models():
        # Chỉ lấy model hỗ trợ tạo nội dung (Chat/Text)
        if 'generateContent' in m.supported_generation_methods:
            found_any = True
            print(f"✅ Model ID: {m.name}")
            print(f"   Mô tả: {m.description}")
            print(f"   Input Token Limit: {m.input_token_limit}")
            print("-" * 30)
            
    if not found_any:
        print("⚠️ Không tìm thấy model nào hỗ trợ generateContent. Kiểm tra lại quyền API Key.")

except Exception as e:
    print(f"❌ Lỗi khi gọi Google API: {e}")
    print("Gợi ý: Kiểm tra kết nối mạng hoặc xem API Key có bị chặn vùng (Region) không.")