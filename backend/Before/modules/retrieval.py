from core.db import get_db_collection
from schemas import HardConstraints, SortOption
from typing import List, Dict, Any, Optional
from bson import ObjectId
import math
import json

# --- Helper: Build Filter Query ---
def build_filter_query(constraints: HardConstraints) -> Dict[str, Any]:
    query = {}
    if constraints.budget_range: 
        query["budget_range"] = {"$in": constraints.budget_range}
    
    if constraints.available_time: 
        query["available_time"] = {"$in": constraints.available_time}
        
    if constraints.companion_tag: 
        query["companion_tag"] = {"$in": constraints.companion_tag}
        
    if constraints.season_tag: 
        query["season_tag"] = {"$in": constraints.season_tag}
        
    if constraints.location_province: query["location_province"] = constraints.location_province
    return query

def build_vector_search_filter(constraints: HardConstraints) -> Dict[str, Any]:
    filter_conditions = {}
    if constraints.budget_range: 
        filter_conditions["budget_range"] = {"$in": constraints.budget_range}
        
    if constraints.location_province: 
        filter_conditions["location_province"] = {"$eq": constraints.location_province}

    if constraints.available_time: 
        filter_conditions["available_time"] = {"$in": constraints.available_time}
        
    if constraints.companion_tag: 
        filter_conditions["companion_tag"] = {"$in": constraints.companion_tag}
        
    if constraints.season_tag: 
        filter_conditions["season_tag"] = {"$in": constraints.season_tag}
        
    return filter_conditions
# --- 1. GET LIST (PAGINATION) ---
def get_destinations_paginated(filters: HardConstraints, sort_option: SortOption, page: int = 1, limit: int = 10) -> Dict[str, Any]:
    collection = get_db_collection()
    query = build_filter_query(filters)

    # Đếm tổng
    total_docs = collection.count_documents(query)
    total_pages = math.ceil(total_docs / limit) if limit > 0 else 0
    
    projection = {
        "_id": 0,             
        "landmark_id": 1,     
        "name": 1, 
        "location_province": 1, 
        "image_urls": 1, 
        "overall_rating": 1
    }
    
    # 1. Xác định tiêu chí Sort
    sort_criteria = [("overall_rating", -1)] # Mặc định Rating giảm dần
    
    if sort_option == SortOption.RATING_ASC:
        sort_criteria = [("overall_rating", 1)]
    elif sort_option == SortOption.NAME_ASC:
        sort_criteria = [("name", 1)] # 1 là A-Z
    elif sort_option == SortOption.NAME_DESC:
        sort_criteria = [("name", -1)] # -1 là Z-A
    # RATING_DESC đã là mặc định ở trên
    
    # 2. Khởi tạo Cursor + Collation Tiếng Việt
    vietnamese_collation = {"locale": "vi"}

    cursor = collection.find(query, projection)
    
    # Áp dụng Collation
    cursor = cursor.collation(vietnamese_collation)
    
    # Áp dụng Sort, Skip, Limit
    cursor = cursor.sort(sort_criteria)\
                   .skip((page - 1) * limit)\
                   .limit(limit)
    
    results = []
    
    for index, doc in enumerate(cursor):
        try:
            # 1. FIX LỖI OBJECT ID
            if "_id" in doc:
                doc["_id"] = str(doc["_id"]) 
            
            # 2. Xử lý ID
            doc["id"] = str(doc.get("landmark_id", doc.get("_id", "")))

            # 3. Xử lý Rating (Chống null)
            if doc.get("overall_rating") is None:
                doc["overall_rating"] = 0.0
            
            # 4. Xử lý Image (Chống null)
            if doc.get("image_urls") is None:
                doc["image_urls"] = []

            results.append(doc)
            
        except Exception as e:
            print(f"❌ LỖI DATA TẠI ITEM #{index}: {e}")
            continue 

    return {
        "data": results,
        "total": total_docs,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }
# --- 2. GET DETAIL BY ID ---
def get_destination_details(landmark_id: str) -> Optional[Dict[str, Any]]:
    collection = get_db_collection()
    
    # 1. Tìm theo landmark_id
    doc = collection.find_one({"landmark_id": landmark_id})
    
    if doc:
        doc["id"] = str(doc["landmark_id"]) 
        if "_id" in doc:
            del doc["_id"]
            
        return doc
        
    return None

# --- 3. VECTOR SEARCH FOR AI  ---
def retrieve_context(query_vector: List[float], hard_constraints: Optional[HardConstraints] = None) -> List[Dict[str, Any]]:
    collection = get_db_collection()
    candidates_limit = 150
    threshold = 0.61

    vector_search_stage = {
        "index": "vector_index",
        "path": "v_hybrid",
        "queryVector": query_vector,
        "numCandidates": 1000,
        "limit": candidates_limit
    }

    # Gắn filter nếu có
    if hard_constraints:
        mongo_filter = build_filter_query(hard_constraints)
        if mongo_filter:
            vector_search_stage["filter"] = mongo_filter

    pipeline = [
        # Stage 1: Tìm kiếm
        {
            "$vectorSearch": vector_search_stage
        },
        # Stage 2: Lấy điểm số ra
        {
            "$project": {
                "_id": 1,
                "landmark_id": 1,
                "name": 1,
                "specific_address": 1,
                "budget_range": 1,
                "available_time": 1,
                "season_tag": 1,
                "companion_tag": 1,
                "combined_tags": 1,
                "description": 1,
                "image_urls": 1,
                "location_province": 1,
                "overall_rating": 1,
                "score": {"$meta": "vectorSearchScore"} 
            }
        },
        # Stage 3: Lọc chặn dưới
        {
            "$match": {
                "score": {"$gte": threshold}
            }
        }
    ]

    try:
        results = list(collection.aggregate(pipeline))
        
        # Xử lý làm sạch dữ liệu
        for doc in results:
            doc["_id"] = str(doc["_id"])
            doc["id"] = str(doc.get("landmark_id", doc.get("_id")))
            if doc.get("image_urls") is None: doc["image_urls"] = []
            if doc.get("overall_rating") is None: doc["overall_rating"] = 0.0

        return results
        
    except Exception as e:
        print(f"❌ Error in vector search: {e}")
        return []