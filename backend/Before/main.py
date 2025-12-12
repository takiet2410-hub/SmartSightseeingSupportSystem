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
    """Tìm kiếm bằng AI + Vector Search """
    try:
        # 1. Vector Search
        query_vector = vectorizer.transform_single(request.vibe_prompt)
        retrieved_context = retrieve_context(query_vector)
        
        if not retrieved_context:
            return RecommendationResponse(status="empty", recommendations=[])

        # 2. Tạo Map để enrichment
        # Đảm bảo hàm normalize_key đã được định nghĩa
        top_context = retrieved_context[:20]
        context_map = {normalize_key(doc.get('name', '')): doc for doc in top_context}
        # 3. Gọi Gemini LLM
        context_str = "\n".join([
            f"- {doc.get('name')}: {doc.get('description','')[:200]}..." 
            for doc in top_context
        ])
        prompt = build_rag_prompt(context=context_str, user_query=request.vibe_prompt)
        
        # Gọi hàm LLM (Đảm bảo đã fix lỗi 404 model ở bước trước)
        llm_response = parse_llm_response(call_llm_api(prompt))
        
        # --- XỬ LÝ FALLBACK (KHI LLM LỖI) ---
        if "error" in llm_response:
            print("⚠️ LLM Error, dùng Fallback.")
            fallback_recs = []
            for doc in retrieved_context[:3]:
                doc_copy = doc.copy()
                doc_copy["justification_summary"] = "Gợi ý tự động theo mức độ phù hợp (AI đang bận)"
                doc_copy["suggested_activities"] = []
                 
                # [FIX LỖI SCHEMA] Map _id sang id
                doc_copy[" id"] = str(doc_copy.get("landmark_id", doc_copy.get("_id", "")))
                 
                fallback_recs.append(doc_copy)
            return RecommendationResponse(status="fallback", recommendations=fallback_recs)

        # 4. Ghép dữ liệu (Enrichment)
        final_recs = []
        
        print("\n--- DEBUG MATCHING ---")
        # In ra danh sách các tên ĐANG CÓ trong Map (Dữ liệu gốc tìm được)
        print(f"Context Map Keys: {list(context_map.keys())}")
        
        for rec in llm_response.get("recommendations", []):
            key = normalize_key(rec.get("name"))
            normalized_ai_name = normalize_key(key)
            print(f"🤖 Gemini gợi ý: '{key}' -> Key chuẩn hóa: '{normalized_ai_name}'")
            original = context_map.get(key)
            
            if original:
                print("   ✅ MATCHED! (Tìm thấy trong DB)")
                merged_rec = original.copy()
                merged_rec["id"] = str(original.get("landmark_id", original.get("_id", "")))
                merged_rec["justification_summary"] = rec.get("justification_summary")
                merged_rec["suggested_activities"] = rec.get("suggested_activities", [])
                
                # Lấy thời tiết
                province = merged_rec.get("location_province", "").replace("Tỉnh", "").strip()
                try:
                    if province:
                        merged_rec["weather"] = await get_current_weather(province)
                except:
                    merged_rec["weather"] = None
                
                final_recs.append(merged_rec)
        
        return RecommendationResponse(status="success", recommendations=final_recs)

    except Exception as e:
        print(f"Error in /recommendations: {e}")
        import traceback
        traceback.print_exc() # In lỗi chi tiết ra terminal
        raise HTTPException(status_code=500, detail=str(e))
    
# API 4: SEMANTIC SEARCH (Vector Search Only)
# ==========================================

@app.post("/search", response_model=PaginatedResponse) 
async def search_destinations(
    request: SearchRequest, 
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50)
):
    # ... logic tìm kiếm giữ nguyên ...
    query_vector = vectorizer.transform_single(request.query)
    
    # Truyền request.hard_constraints vào hàm xử lý
    all_results = retrieve_context(query_vector, request.hard_constraints)
    
    # ... logic phân trang ...
    total_found = len(all_results)
    total_pages = (total_found + limit - 1) // limit 
    start_index = (page - 1) * limit
    paginated_data = all_results[start_index : start_index + limit]
    
    # ... mapping dữ liệu ...
    clean_results = [
        DestinationSummary(
            id=str(doc.get("landmark_id", doc.get("_id"))),
            name=doc.get("name", "Unknown"),
            location_province=doc.get("location_province", ""),
            image_urls=doc.get("image_urls", []) or [],
            overall_rating=doc.get("overall_rating", 0.0)
        ) for doc in paginated_data
    ]

    return {
        "data": clean_results,
        "total": total_found,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)