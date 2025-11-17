from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from core.config import settings
from typing import List, Dict, Any

def build_rag_prompt(context: str, user_query: str) -> str:
    """
    Xây dựng prompt cho LLM
    """
    template = """
    Bạn là một trợ lý du lịch AI. Dựa vào bối cảnh (context) được cung cấp và yêu cầu của người dùng, 
    hãy chọn ra 3 địa điểm phù hợp nhất và viết một lời giải thích (justification summary) cho mỗi địa điểm.
    
    Yêu cầu của người dùng: "{user_query}"
    
    Bối cảnh (Context) - (Thông tin các địa điểm đã được lọc):
    ---
    {context}
    ---
    
    Trả lời hoàn toàn chỉ bằng Tiếng Việt, không bằng ngôn ngữ nào khác.
    Chỉ chọn từ bối cảnh, không bịa thêm.
    Đầu ra mong muốn (chỉ trả về JSON, không có text gì khác):
    {{
        "recommendations": [
            {{
                "rank": 1,
                "name": "Tên địa điểm 1",
                "justification_summary": "Giải thích ngắn gọn (dưới 150 từ) tại sao phù hợp...",
                "estimated_budget": "...",
                "suggested_activities": ["...", "..."]
            }},
            {{
                "rank": 2,
                "name": "Tên địa điểm 2",
                "justification_summary": "...",
                "estimated_budget": "...",
                "suggested_activities": ["...", "..."]
            }},
            {{
                "rank": 3,
                "name": "Tên địa điểm 3",
                "justification_summary": "...",
                "estimated_budget": "...",
                "suggested_activities": ["...", "..."]
            }}
        ]
    }}
    """
    return template.format(user_query=user_query, context=context)

def call_llm_api(prompt: str) -> str:
    """
    Gọi LLM (Ollama Llama 3) và nhận kết quả.
    """
    try:
        llm = OllamaLLM(base_url=settings.OLLAMA_BASE_URL, model=settings.LLM_MODEL_NAME)
        
        # Đơn giản là gọi LLM
        response = llm.invoke(prompt)
        return response
        
    except Exception as e:
        print(f"Error calling LLM: {e}")
        return f'{{"error": "Failed to call LLM: {e}"}}'

def parse_llm_response(response_str: str) -> Dict[str, Any]:
    """
    Phân tích chuỗi JSON trả về từ LLM.
    """
    import json
    try:
        # Xử lý trường hợp LLM trả về text rác
        json_str = response_str[response_str.find('{') : response_str.rfind('}')+1]
        data = json.loads(json_str)
        return data
    except json.JSONDecodeError:
        print(f"Error: Failed to parse LLM response: {response_str}")
        return {"error": "LLM response was not valid JSON."}