from core.db import get_db_collection
from schemas import HardConstraints
from typing import List, Dict, Any

import json 


def build_mongo_aggregation(hard_constraints: HardConstraints, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
    
    # 1. Hard Filters
    filter_conditions = {}
    if hard_constraints.budget_range:
        filter_conditions["budget_range"] = {"$eq": hard_constraints.budget_range}
    if hard_constraints.available_time:
        filter_conditions["available_time"] = {"$eq": hard_constraints.available_time}
    if hard_constraints.companion_tag:
        filter_conditions["companion_tag"] = {"$eq": hard_constraints.companion_tag}
    if hard_constraints.season_tag:
        filter_conditions["season_tag"] = {"$eq": hard_constraints.season_tag}
        
    search_filter = filter_conditions if filter_conditions else None

    # 2. Vector Search Stage
    # Chúng ta lấy số lượng kết quả nhiều hơn top_k (ví dụ gấp 4 lần)
    # để sau đó sắp xếp lại bằng rating.
    candidates_pool_size = top_k * 4 
    
    vector_search_stage = {
        "$vectorSearch": {
            "index": "vector_index", 
            "path": "v_hybrid",       
            "queryVector": query_vector,
            "numCandidates": 100, 
            "limit": candidates_pool_size, # Lấy tập ứng viên rộng hơn
        }
    }
    
    if search_filter:
        vector_search_stage["$vectorSearch"]["filter"] = search_filter
    
    # 3. Project Stage (Lấy các trường cần thiết)
    project_stage = {
        "$project": {
            "_id": 0,
            "name": 1,
            "location_province": 1, # Lấy tỉnh
            "specific_address": 1,  # Lấy địa chỉ cụ thể
            "overall_rating": 1,    # Lấy rating
            "text_chunk": 1, 
            "description": 1,
            "image_urls": 1,
            "score": {"$meta": "vectorSearchScore"} # Điểm phù hợp ngữ nghĩa
        }
    }

    # 4. Sort Stage 
    # Sắp xếp kết quả theo rating giảm dần (-1)
    # Lưu ý: Bạn có thể cân nhắc sort theo cả score và rating nếu muốn
    sort_stage = {
        "$sort": {
            "overall_rating": -1, # Ưu tiên rating cao nhất
            "score": -1           # Nếu rating bằng nhau, ưu tiên độ phù hợp
        }
    }
    
    # 5. Limit Stage (Cắt lấy top_k cuối cùng)
    limit_stage = {
        "$limit": top_k
    }

    pipeline = [
        vector_search_stage,
        project_stage,
        sort_stage,  # Sắp xếp lại danh sách ứng viên
        limit_stage  # Chỉ lấy top K
    ]
    
    return pipeline


def retrieve_context(hard_constraints: HardConstraints, query_vector: List[float]) -> List[Dict[str, Any]]:
    collection = get_db_collection()
    if collection is None:
        raise Exception("Database connection not available.")

    pipeline = build_mongo_aggregation(hard_constraints, query_vector)
    print("\n👉 [DEBUG] PIPELINE GỬI XUỐNG MONGO:")
    print(json.dumps(pipeline, indent=2, ensure_ascii=False))
    print("------------------------------------------------\n")
    # ===========================
    
    try:
        results = list(collection.aggregate(pipeline)) 
        print(f"👉 [DEBUG] Tìm thấy {len(results)} kết quả.")
        return results 
    except Exception as e:
        print(f"Error during MongoDB aggregation: {e}")
        return []
