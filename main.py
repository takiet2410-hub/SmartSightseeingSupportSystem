from fastapi import FastAPI, HTTPException, Depends
from schemas import RecommendationRequest, RecommendationResponse
from modules.vectorizer import HybridVectorizer
from modules.retrieval import retrieve_context
from modules.generation import build_rag_prompt, call_llm_api, parse_llm_response
from core.config import settings
from contextlib import asynccontextmanager
import unicodedata
import os

# Khởi tạo vectorizer toàn cục
vectorizer = HybridVectorizer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- STARTUP: Loading models ---")
    try:
        # Kiểm tra xem file vectorizer có tồn tại không
        if os.path.exists(settings.VECTORIZER_PATH):
            vectorizer.load_fitted_tfidf(settings.VECTORIZER_PATH)
            print("Models loaded successfully.")
        else:
            print(f"Không tìm thấy file vectorizer tại: {settings.VECTORIZER_PATH}")
            print("👉 Bạn cần chạy lệnh 'python ingest_data.py' để tạo file này trước.")
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR during startup: {e}")
    
    
    yield
    print("--- SHUTDOWN ---")
    
app = FastAPI(
    title="Smart Tourism System - 'Before' Module",
    lifespan=lifespan
)

# 2. HÀM CHUẨN HÓA INPUT (LOGIC Y HỆT BÊN INGEST)
def standardize_input(text: str) -> str:
    if not text:
        return None # Trả về None để filter bỏ qua nếu user không nhập
    text = str(text)
    text = unicodedata.normalize('NFC', text)
    text = text.replace('\u2013', '-').replace('\u2014', '-')
    return text.strip().lower()

@app.get("/")
def read_root():
    return {"message": "Welcome to the Smart Tourism 'Before' Module API"}

@app.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    try:
        # 1. Chuẩn hóa input (như đã sửa ở bước trước)
        if request.hard_constraints:
            req = request.hard_constraints
            req.available_time = standardize_input(req.available_time)
            req.budget_range = standardize_input(req.budget_range)
            req.companion_tag = standardize_input(req.companion_tag)
            req.season_tag = standardize_input(req.season_tag)
        
        print(f"Received query: {request.vibe_prompt}")
        
        # 2. Vector Search & Retrieval
        query_vector = vectorizer.transform_single(request.vibe_prompt)
        retrieved_context = retrieve_context(request.hard_constraints, query_vector)
        
        if not retrieved_context:
            return RecommendationResponse(
                status="error", 
                recommendations=[], 
                debug_info={"message": "No destinations found matching criteria."}
            )

        # 3. Tạo Dictionary để tra cứu nhanh (Name -> Full Data)
        # Mục đích: Lấy lại địa chỉ, rating chính xác từ DB mà không cần LLM sinh ra
        context_map = {doc['name']: doc for doc in retrieved_context}

        # 4. Gọi LLM để chọn và viết lời bình
        context_str = "\n\n".join([str(doc) for doc in retrieved_context])
        prompt = build_rag_prompt(context=context_str, user_query=request.vibe_prompt)
        llm_raw_response = call_llm_api(prompt)
        parsed_response = parse_llm_response(llm_raw_response)
        
        if "error" in parsed_response:
             raise HTTPException(status_code=500, detail=parsed_response["error"])

        # 5. === BƯỚC QUAN TRỌNG: GHÉP DỮ LIỆU (DATA ENRICHMENT) ===
        llm_recs = parsed_response.get("recommendations", [])
        final_recommendations = []

        for rec in llm_recs:
            # Tìm lại doc gốc trong context dựa vào tên
            original_doc = context_map.get(rec.get("name"))
            
            if original_doc:
                # Nếu tìm thấy, copy thông tin cứng từ DB sang
                rec["location_province"] = original_doc.get("location_province", "Unknown")
                rec["specific_address"] = original_doc.get("specific_address", "Unknown")
                rec["overall_rating"] = original_doc.get("overall_rating", 0.0)
                rec["image_urls"] = original_doc.get("image_urls", [])
            else:
                # Fallback: Nếu LLM bịa tên hoặc sửa tên làm không tìm thấy trong map
                # Gán giá trị mặc định để tránh lỗi 500
                rec["location_province"] = ""
                rec["specific_address"] = ""
                rec["overall_rating"] = 0.0
                rec["image_urls"] = []
            
            final_recommendations.append(rec)

        # 6. Trả về kết quả đã đầy đủ field
        return RecommendationResponse(
            status="success",
            recommendations=final_recommendations,
            debug_info={
                "retrieved_count": len(retrieved_context), 
                # Lấy score của thằng đầu tiên tìm thấy (nếu có)
                "top_match_score": retrieved_context[0].get('score') if retrieved_context else 0
            }
        )

    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    import uvicorn
    print("Run the server using: uvicorn main:app --reload")