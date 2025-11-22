from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from schemas import RecommendationRequest, RecommendationResponse
from modules.vectorizer import HybridVectorizer
from modules.retrieval import retrieve_context
from modules.generation import build_rag_prompt, call_llm_api, parse_llm_response
from modules.weather import get_current_weather
from core.config import settings
from contextlib import asynccontextmanager
import unicodedata
import os

# Khởi tạo vectorizer toàn cục
vectorizer = HybridVectorizer()

# --- Helper: Chuẩn hóa chuỗi để so sánh tên (Khắc phục lỗi hoa/thường) ---
def normalize_key(text: str) -> str:
    """
    Chuyển về chữ thường, bỏ khoảng trắng thừa, chuẩn hóa Unicode.
    Dùng để làm key trong Map tra cứu.
    """
    if not text: return ""
    return unicodedata.normalize('NFC', str(text)).strip().lower()

def standardize_input(text: str) -> str:
    if not text:
        return None 
    text = str(text)
    text = unicodedata.normalize('NFC', text)
    text = text.replace('\u2013', '-').replace('\u2014', '-')
    return text.strip().lower()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- STARTUP: Loading models ---")
    try:
        if os.path.exists(settings.VECTORIZER_PATH):
            vectorizer.load_fitted_tfidf(settings.VECTORIZER_PATH)
            print("Models loaded successfully.")
        else:
            print(f"WARNING: Không tìm thấy file vectorizer tại: {settings.VECTORIZER_PATH}")
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR during startup: {e}")
    yield
    print("--- SHUTDOWN ---")
    
app = FastAPI(title="Smart Tourism System", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Cho phép mọi nguồn (Frontend) truy cập
    allow_credentials=True,
    allow_methods=["*"], # Cho phép mọi phương thức (POST, GET...)
    allow_headers=["*"], # Cho phép mọi header
)
@app.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    try:
        # 1. Chuẩn hóa input
        if request.hard_constraints:
            req = request.hard_constraints
            req.available_time = standardize_input(req.available_time)
            req.budget_range = standardize_input(req.budget_range)
            req.companion_tag = standardize_input(req.companion_tag)
            req.season_tag = standardize_input(req.season_tag)
        
        print(f"Received query: {request.vibe_prompt}")
        
        # 2. Retrieval
        query_vector = vectorizer.transform_single(request.vibe_prompt)
        retrieved_context = retrieve_context(request.hard_constraints, query_vector)
        
        if not retrieved_context:
            return RecommendationResponse(
                status="error", 
                recommendations=[], 
                debug_info={"message": "No destinations found matching criteria."}
            )

        # 3. TẠO MAP TRA CỨU THÔNG MINH (QUAN TRỌNG)
        # Key của map sẽ là tên đã chuẩn hóa (lowercase). 
        # Ví dụ: "vinwonders nha trang" -> Document Gốc
        context_map = {normalize_key(doc['name']): doc for doc in retrieved_context}
        print(context_map)
        # 4. Gọi LLM
        context_str = "\n\n".join([str(doc) for doc in retrieved_context])
        prompt = build_rag_prompt(context=context_str, user_query=request.vibe_prompt)
        llm_raw_response = call_llm_api(prompt)
        parsed_response = parse_llm_response(llm_raw_response)
        
        if "error" in parsed_response:
             # Fallback: Nếu LLM lỗi JSON, trả về top 3 từ DB luôn
             print("LLM Error, using fallback.")
             parsed_response["recommendations"] = [{"name": doc["name"], "rank": i+1, "justification_summary": "Gợi ý tự động."} for i, doc in enumerate(retrieved_context[:3])]

        # 5. === DATA ENRICHMENT (GHÉP DỮ LIỆU CHÍNH XÁC TỪ DB) ===
        llm_recs = parsed_response.get("recommendations", [])
        final_recommendations = []

        for rec in llm_recs:
            # Lấy tên do LLM sinh ra
            llm_name = rec.get("name", "")
            # Chuẩn hóa tên đó (lowercase) để tìm trong Map
            lookup_key = normalize_key(llm_name)
            
            # Tra cứu vào dữ liệu gốc
            original_doc = context_map.get(lookup_key)
            
            if original_doc:
                # Ghi đè lại tên bằng tên chuẩn trong DB (để sửa lỗi hoa/thường của LLM)
                rec["name"] = original_doc["name"] 
                rec["location_province"] = original_doc.get("location_province", "Unknown")
                rec["specific_address"] = original_doc.get("specific_address", "Unknown")
                rec["overall_rating"] = float(original_doc.get("overall_rating", 0.0))
                rec["image_urls"] = original_doc.get("image_urls", [])
                rec["description"] = original_doc.get("description","Unknown")
                
                #Gọi API OpenWeather
                province = original_doc.get("location_province", "")
                clean_province = province.replace("Tỉnh", "").replace("Thành phố", "").strip()
                weather_data = await get_current_weather(clean_province)
                rec["weather"] = weather_data
                
                final_recommendations.append(rec)
            else:
                print(f"⚠️ Mismatch: LLM generated '{llm_name}' but DB keys are: {list(context_map.keys())}")
                # Chỉ thêm vào nếu thực sự cần thiết, hoặc bỏ qua
                # Ở đây ta chọn bỏ qua để tránh hiển thị dữ liệu rác
                continue

        return RecommendationResponse(
            status="success",
            recommendations=final_recommendations,
            debug_info={
                "retrieved_count": len(retrieved_context), 
                "top_match_score": retrieved_context[0].get('score') if retrieved_context else 0
            }
        )

    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    import uvicorn
    print("Run the server using: uvicorn main:app --reload")