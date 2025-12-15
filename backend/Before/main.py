from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import unicodedata
import os
import requests 
from fastapi.security import OAuth2PasswordRequestForm
from schemas import SortOption
from fastapi.responses import JSONResponse
import logging

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
import locale

# Khởi tạo Vectorizer
vectorizer = HybridVectorizer()

# Biến toàn cục để kiểm tra trạng thái Locale
IS_LOCALE_READY = False

def normalize_key(text: str) -> str:
    if not text: return ""
    return unicodedata.normalize('NFC', str(text)).strip().lower()

# --- HÀM HỖ TRỢ SORT TIẾNG VIỆT (CHO /SEARCH) ---
def get_vietnamese_sort_key(item: dict) -> str:
    """
    Tạo key để sort tiếng Việt chuẩn.
    Ưu tiên dùng Locale hệ thống. Nếu không có, dùng Fallback thủ công.
    """
    text = item.get("name", "")
    if not text: return ""
    
    # Cách 1: Nếu hệ thống đã cài Locale tiếng Việt (Chuẩn nhất)
    if IS_LOCALE_READY:
        return locale.strxfrm(text)
    
    # Cách 2: Fallback (Nếu không cài Locale)
    # Xử lý vấn đề chữ Đ/đ thường bị đẩy xuống cuối bảng mã ASCII
    # và đưa các ký tự có dấu về dạng không dấu để so sánh tương đối
    text_fixed = text.replace("đ", "d").replace("Đ", "D")
    
    # Normalize về dạng NFD để tách dấu ra khỏi ký tự gốc (vd: á -> a + sắc)
    # Sau đó loại bỏ các ký tự dấu (category Mn)
    normalized = unicodedata.normalize('NFD', text_fixed)
    text_ascii = "".join(c for c in normalized if unicodedata.category(c) != 'Mn')
    
    return text_ascii.lower()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- STARTUP ---")
    global IS_LOCALE_READY
    
    # 1. Cài đặt Locale tiếng Việt cho OS
    try:
        # Thử các mã locale phổ biến cho tiếng Việt trên Linux/Mac
        locale.setlocale(locale.LC_COLLATE, 'vi_VN.UTF-8') 
        IS_LOCALE_READY = True
        print("✅ Locale set to vi_VN.UTF-8 (Sắp xếp tiếng Việt chuẩn)")
    except locale.Error:
        try:
            # Thử cho Windows
            locale.setlocale(locale.LC_COLLATE, 'vi_VN') 
            IS_LOCALE_READY = True
            print("✅ Locale set to vi_VN (Windows)")
        except locale.Error:
            IS_LOCALE_READY = False
            print("⚠️ Warning: Không thiết lập được Locale tiếng Việt hệ thống.")
            print("👉 Sẽ sử dụng chế độ 'Fallback Sort' (giả lập sắp xếp A-Z).")

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
    auth_url = "http://localhost:8000/auth/login"
    payload = {
        "username": form_data.username,
        "password": form_data.password
    }
    try:
        response = requests.post(auth_url, json=payload)
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, 
                detail=response.json().get("detail", "Login failed")
            )
        return response.json()
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Không kết nối được với Auth Server")

app.include_router(favorites.router, prefix="/favorites", tags=["User Favorites"])

# ==========================================
# API 1: LẤY DANH SÁCH & FILTER
# ==========================================
@app.get("/destinations", response_model=PaginatedResponse)
async def list_destinations(
    budget_range: Optional[List[str]] = Query(None),
    available_time: Optional[List[str]] = Query(None),
    companion_tag: Optional[List[str]] = Query(None),
    season_tag: Optional[List[str]] = Query(None),
    location_province: Optional[str] = Query(None),
    sort_by: SortOption = Query(SortOption.RATING_DESC),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50)
):
    filters = HardConstraints(
        budget_range=budget_range,
        available_time=available_time,
        companion_tag=companion_tag,
        season_tag=season_tag,
        location_province=location_province
    )

    return get_destinations_paginated(filters, sort_by, page, limit)

# ==========================================
# API 2: LẤY CHI TIẾT
# ==========================================
@app.get("/destinations/{landmark_id}", response_model=DestinationDetailResponse)
async def get_destination_detail(landmark_id: str):
    details = get_destination_details(landmark_id)
    if not details:
        raise HTTPException(status_code=404, detail="Destination not found")
    
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
    try:
        query_vector = vectorizer.transform_single(request.vibe_prompt)
        retrieved_context = retrieve_context(query_vector)
        
        if not retrieved_context:
            return RecommendationResponse(status="empty", recommendations=[])

        top_context = retrieved_context[:20]
        context_map = {normalize_key(doc.get('name', '')): doc for doc in top_context}
        
        context_str = "\n".join([
            f"- {doc.get('name')}: {doc.get('description','')[:200]}..." 
            for doc in top_context
        ])
        prompt = build_rag_prompt(context=context_str, user_query=request.vibe_prompt)
        
        llm_response = parse_llm_response(call_llm_api(prompt))
        
        if "error" in llm_response:
            print("⚠️ LLM Error, dùng Fallback.")
            fallback_recs = []
            for doc in retrieved_context[:3]:
                doc_copy = doc.copy()
                doc_copy["justification_summary"] = "Gợi ý tự động (AI bận)"
                doc_copy["suggested_activities"] = []
                doc_copy["id"] = str(doc_copy.get("landmark_id", doc_copy.get("_id", "")))
                fallback_recs.append(doc_copy)
            return RecommendationResponse(status="fallback", recommendations=fallback_recs)

        final_recs = []
        for rec in llm_response.get("recommendations", []):
            key = normalize_key(rec.get("name"))
            original = context_map.get(key)
            
            if original:
                merged_rec = original.copy()
                merged_rec["id"] = str(original.get("landmark_id", original.get("_id", "")))
                merged_rec["justification_summary"] = rec.get("justification_summary")
                merged_rec["suggested_activities"] = rec.get("suggested_activities", [])
                
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
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
# ==========================================
# API 4: SEMANTIC SEARCH
# ==========================================
@app.post("/search", response_model=PaginatedResponse) 
async def search_destinations(
    request: SearchRequest,
    sort_by: SortOption = Query(SortOption.RATING_DESC),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50)
):
    query_vector = vectorizer.transform_single(request.query)
    all_results = retrieve_context(query_vector, request.hard_constraints)
    
    # --- 2. XỬ LÝ SORT LIST (Đã cải tiến cho tiếng Việt) ---
    if sort_by == SortOption.RATING_DESC:
        all_results.sort(key=lambda x: x.get("overall_rating", 0.0), reverse=True)
    elif sort_by == SortOption.RATING_ASC:
        all_results.sort(key=lambda x: x.get("overall_rating", 0.0), reverse=False)
        
    elif sort_by == SortOption.NAME_ASC:
        # Sử dụng hàm helper get_vietnamese_sort_key
        all_results.sort(key=get_vietnamese_sort_key, reverse=False)
        
    elif sort_by == SortOption.NAME_DESC:
        all_results.sort(key=get_vietnamese_sort_key, reverse=True)
    
    total_found = len(all_results)
    total_pages = (total_found + limit - 1) // limit 
    start_index = (page - 1) * limit
    paginated_data = all_results[start_index : start_index + limit]
    
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
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)