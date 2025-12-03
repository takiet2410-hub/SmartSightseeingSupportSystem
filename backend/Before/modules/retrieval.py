from core.db import get_db_collection
from schemas import HardConstraints
from typing import List, Dict, Any, Optional
from bson import ObjectId
import math
import json

# --- Helper: Build Filter Query ---
def build_filter_query(constraints: HardConstraints) -> Dict[str, Any]:
    query = {}
    if constraints.budget_range: query["budget_range"] = constraints.budget_range
    if constraints.available_time: query["available_time"] = constraints.available_time
    if constraints.companion_tag: query["companion_tag"] = constraints.companion_tag
    if constraints.season_tag: query["season_tag"] = constraints.season_tag
    if constraints.location_province: query["location_province"] = constraints.location_province
    return query

# --- 1. GET LIST (PAGINATION) ---
def get_destinations_paginated(filters: HardConstraints, page: int = 1, limit: int = 10) -> Dict[str, Any]:
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
    
    cursor = collection.find(query, projection)\
                       .sort("overall_rating", -1)\
                       .skip((page - 1) * limit)\
                       .limit(limit)
    
    results = []
    for doc in cursor:
        # 2. MAPPING DỮ LIỆU: Gán landmark_id vào id cho đúng Schema
        # Dùng str() để chắc chắn nó là string, và .get() để tránh lỗi nếu null
        doc["id"] = str(doc.get("landmark_id", "")) 
        
        results.append(doc)
        
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
    
    # Chỉ thực hiện Vector Search thuần túy
    vector_search_stage = {
        "$vectorSearch": {
            "index": "vector_index", 
            "path": "v_hybrid",       
            "queryVector": query_vector,
            "numCandidates": 100, 
            "limit": 20, 
        }
    }
    
    if hard_constraints:
        search_filter = build_filter_query(hard_constraints)
        if search_filter:
            vector_search_stage["$vectorSearch"]["filter"] = search_filter

    pipeline = [
        vector_search_stage,
        {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
        {"$sort": {"score": -1}}, 
        {"$limit": 20} 
    ]
    
    try:
        results = list(collection.aggregate(pipeline))
        
        # Mapping ID (quan trọng)
        for doc in results:
            doc["id"] = str(doc.get("landmark_id", doc.get("_id", "")))
            if "_id" in doc: del doc["_id"]
            
        return results
    except Exception as e:
        print(f"Error Vector Search: {e}")
        return []