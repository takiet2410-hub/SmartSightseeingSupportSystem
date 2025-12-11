from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import unicodedata
import os
import requests 
from fastapi.security import OAuth2PasswordRequestForm
from schemas import SortOption
from fastapi.responses import JSONResponse

# Import modules
from schemas import (
    RecommendationRequest, RecommendationResponse, 
    PaginatedResponse, DestinationDetailResponse, HardConstraints,
    SearchRequest, SearchResponse, DestinationSummary
)
from modules.vectorizer import HybridVectorizer
from modules.retrieval import retrieve_context, get_destinations_paginated, get_destination_details
from modules.generation import build_rag_prompt, call_llm_api, parse_llm_response
from modules.weather import get_current_weather
from core.config import settings
from typing import List, Optional
import favorites

# Khởi tạo Vectorizer
vectorizer = HybridVectorizer()

def normalize_key(text: str) -> str:
    if not text: return ""
    return unicodedata.normalize('NFC', str(text)).strip().lower()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- STARTUP ---")
    if os.path.exists(settings.VECTORIZER_PATH):
        vectorizer.load_fitted_tfidf(settings.VECTORIZER_PATH)
    else:
        print("⚠️ Warning: Vectorizer not found.")
    yield
    print("--- SHUTDOWN ---")

app = FastAPI(title="Smart Tourism API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"🔥 LỖI NGHIÊM TRỌNG (500) TẠI {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )

@app.get("/", tags=["Health"])
def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "Before Module", "version": "1.0.0"}

@app.post("/login-proxy", tags=["Auth Proxy"])
def login_proxy(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    API này nhận Form Data từ Swagger UI, 
    sau đó chuyển thành JSON để gọi sang Auth Server (Port 8000).
    """
    auth_url = "http://localhost:8000/auth/login" # Đường dẫn tới Auth Server thật
    
    # Chuyển đổi dữ liệu Form -> JSON
    payload = {
        "username": form_data.username,
        "password": form_data.password
    }
    
    try:
        # Gọi sang Auth Server
        response = requests.post(auth_url, json=payload)
        
        # Nếu Auth Server báo lỗi (sai pass...), ta báo lỗi theo
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, 
                detail=response.json().get("detail", "Login failed")
            )
            
        # Trả về Token cho Swagger UI
        return response.json()
        
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Không kết nối được với Auth Server (Port 8000)")


# API này yêu cầu Token (được validate bởi deps.py trong router này)
app.include_router(favorites.router, prefix="/favorites", tags=["User Favorites"])

# ==========================================
# API 1: LẤY DANH SÁCH & FILTER (Mặc định)
# ==========================================
@app.get("/destinations", response_model=PaginatedResponse)
async def list_destinations(
    
    budget_range: Optional[List[str]] = Query(None, description="Lọc theo ngân sách"),
    available_time: Optional[List[str]] = Query(None, description="Lọc theo thời gian"),
    companion_tag: Optional[List[str]] = Query(None, description="Lọc theo người đi cùng"),
    season_tag: Optional[List[str]] = Query(None, description="Lọc theo mùa"),
    location_province: Optional[str] = Query(None, description="Lọc theo tỉnh"),
    # -----------------------
    
    sort_by: SortOption = Query(SortOption.RATING_DESC),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50)
):
    # Bước 2: Gom lại thành object HardConstraints để truyền cho hàm xử lý
    filters = HardConstraints(
        budget_range=budget_range,
        available_time=available_time,
        companion_tag=companion_tag,
        season_tag=season_tag,
        location_province=location_province
    )

    return get_destinations_paginated(filters, sort_by, page, limit)

# ==========================================
# API 2: LẤY CHI TIẾT (Khi click vào card)
# ==========================================
@app.get("/destinations/{landmark_id}", response_model=DestinationDetailResponse)
async def get_destination_detail(landmark_id: str):
    """Lấy thông tin chi tiết địa điểm + Thời tiết"""
    details = get_destination_details(landmark_id)
    
    if not details:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    # Data Enrichment: Weather
    province = details.get("location_province", "")
    if province:
        clean_province = province.replace("Tỉnh", "").replace("Thành phố", "").strip()
        try:
            weather = await get_current_weather(clean_province)
            details["weather"] = weather
        except Exception:
            details["weather"] = None
            
    return details

# ==========================================
# API 3: VIBE SEARCH (AI RECOMMENDATION)
# ==========================================
@app.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """Tìm kiếm bằng AI + Vector Search"""
    try:
        # 1. Vector Search
        query_vector = vectorizer.transform_single(request.vibe_prompt)
        retrieved_context = retrieve_context(query_vector)
        
        if not retrieved_context:
            return RecommendationResponse(status="empty", recommendations=[])

        # 2. Tạo Map để enrichment (Key: Tên chuẩn hóa -> Value: Document gốc)
        context_map = {normalize_key(doc['name']): doc for doc in retrieved_context}

        # 3. Gọi Gemini LLM
        context_str = "\n".join([f"- {doc['name']}: {doc.get('description','')[:200]}..." for doc in retrieved_context])
        prompt = build_rag_prompt(context=context_str, user_query=request.vibe_prompt)
        llm_response = parse_llm_response(call_llm_api(prompt))
        
        if "error" in llm_response:
             # Fallback nếu LLM lỗi: trả về kết quả vector search thô
             fallback_recs = []
             for doc in retrieved_context[:3]:
                 doc_copy = doc.copy()
                 doc_copy["justification_summary"] = "Gợi ý tự động (LLM Error)"
                 fallback_recs.append(doc_copy)
             return RecommendationResponse(status="fallback", recommendations=fallback_recs)

        # 4. Ghép dữ liệu (Enrichment)
        final_recs = []
        for rec in llm_response.get("recommendations", []):
            key = normalize_key(rec.get("name"))
            original = context_map.get(key)
            
            if original:
                # Merge thông tin: Lấy ID và thông tin cứng từ DB, Lấy justification từ AI
                merged_rec = original.copy() # Chứa id, image, rating...
                merged_rec["justification_summary"] = rec.get("justification_summary")
                merged_rec["suggested_activities"] = rec.get("suggested_activities", [])
                
                # Lấy thời tiết cho các địa điểm gợi ý luôn
                province = merged_rec.get("location_province", "").replace("Tỉnh", "").strip()
                try:
                    merged_rec["weather"] = await get_current_weather(province)
                except:
                    merged_rec["weather"] = None
                
                final_recs.append(merged_rec)
        
        return RecommendationResponse(status="success", recommendations=final_recs)

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# API 4: SEMANTIC SEARCH (Vector Search Only)
# ==========================================
@app.post("/search", response_model=SearchResponse)
async def semantic_search(request: SearchRequest):
    """
    Tìm kiếm thông minh dựa trên Vector (Vibe Search).
    - Tốc độ nhanh (Không dùng LLM).
    - Hiểu ngữ nghĩa (VD: "lạnh" -> tìm Đà Lạt, Sapa).
    """
    try:
        # 1. Vector hóa câu query
        query_vector = vectorizer.transform_single(request.query)
        
        # 2. Gọi hàm retrieve_context (Hàm này đã có sẵn ở retrieval.py)
        # Lưu ý: Hàm này trả về Top K kết quả gần nhất
        raw_results = retrieve_context(query_vector, hard_constraints=request.hard_constraints)
        
        # 3. Chuẩn hóa dữ liệu trả về (Mapping sang DestinationSummary)
        final_results = []
        for doc in raw_results:
            # Mapping an toàn
            item = DestinationSummary(
                id=str(doc.get("landmark_id", "")), # Map landmark_id -> id
                name=doc.get("name", "Unknown"),
                location_province=doc.get("location_province", ""),
                image_urls=doc.get("image_urls", []),
                overall_rating=doc.get("overall_rating", 0.0)
            )
            final_results.append(item)
            
        return SearchResponse(
            data=final_results,
            total_found=len(final_results)
        )

    except Exception as e:
        print(f"Search Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)