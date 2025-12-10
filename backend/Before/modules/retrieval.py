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
    
    mongo_sort = [("overall_rating", -1)] 
    
    if sort_option == SortOption.NAME_ASC:
        mongo_sort = [("name", 1)] # A-Z
    elif sort_option == SortOption.NAME_DESC:
        mongo_sort = [("name", -1)] # Z-A
    elif sort_option == SortOption.RATING_ASC:
        mongo_sort = [("overall_rating", 1)] # Rating thấp lên cao
    elif sort_option == SortOption.RATING_DESC:
        mongo_sort = [("overall_rating", -1)] # Rating cao xuống thấp
        
    # Áp dụng sort vào cursor
    cursor = collection.find(query, projection)\
                       .sort(mongo_sort)\
                       .skip((page - 1) * limit)\
                       .limit(limit)
    
    results = []
    for doc in cursor:
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
        search_filter = build_vector_search_filter(hard_constraints)
        if search_filter:
            vector_search_stage["$vectorSearch"]["filter"] = search_filter

    pipeline = [
        vector_search_stage,
        {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
        {"$sort": {"score": -1}}, 
        {"$limit": 20},
        {"$project": {
                "landmark_id": 1,
                "name": 1,
                "description": 1,
                "location_province": 1,
                "image_urls": 1,
                "overall_rating": 1,
                "score": 1,
                "season_tag": 1,
                "budget_range": 1,
                "available_time": 1,
                "companion_tag": 1
            }
        }
    ]
    
    try:
        results = list(collection.aggregate(pipeline))
        
        for doc in results:
            doc["id"] = str(doc.get("landmark_id", doc.get("_id", "")))
            if "_id" in doc: del doc["_id"]
            
        return results
    except Exception as e:
        print(f"Error Vector Search: {e}")
        return []