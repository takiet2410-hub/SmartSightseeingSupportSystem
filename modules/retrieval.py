from core.db import get_db_collection
from schemas import HardConstraints
from typing import List, Dict, Any

def build_mongo_aggregation(hard_constraints: HardConstraints, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Xây dựng pipeline $vectorSearch cho MongoDB.
    (Đã đơn giản hóa Hard Filter)
    """
    
    # 1. Xây dựng Hard Filter stage ($match / preFilter)
    #
    filter_stage = {}
        
    if hard_constraints.tags:
        # Lọc các địa điểm có tag nằm TRONG mảng tag người dùng yêu cầu
        filter_stage["tags_array"] = {"$in": hard_constraints.tags}
        
    # (Đã xóa logic lọc budget và duration)

    # 2. Xây dựng $vectorSearch stage
    #
    vector_search_stage = {
        "$vectorSearch": {
            "index": "vector_index",  # Đảm bảo tên này khớp với tên Index trên Atlas
            "path": "v_hybrid",       
            "queryVector": query_vector,
            "numCandidates": 100,
            "limit": top_k,
            "filter": filter_stage # Áp dụng hard filter (chỉ lọc tag)
        }
    }
    
    # 3. Project stage
    project_stage = {
        "$project": {
            "_id": 0,
            "name": 1,
            "location": 1,
            "text_chunk": 1, 
            "description": 1,
            "tags_array": 1,
            "score": {"$meta": "vectorSearchScore"}
        }
    }

    pipeline = [
        vector_search_stage,
        project_stage
    ]
    
    return pipeline

def retrieve_context(hard_constraints: HardConstraints, query_vector: List[float]) -> List[Dict[str, Any]]:
    """
    Thực thi truy vấn và trả về context cho RAG.
    """
    collection = get_db_collection()
    if collection is None:
        raise Exception("Database connection not available.")

    pipeline = build_mongo_aggregation(hard_constraints, query_vector)
    
    try:
        results = list(collection.aggregate(pipeline)) 
        return results 
    except Exception as e:
        print(f"Error during MongoDB aggregation: {e}")
        return []