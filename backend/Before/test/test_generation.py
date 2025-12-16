from unittest.mock import patch
import json

def test_search_semantic(client):
    """Test API /search"""
    # 1. Mock Vectorizer ra vector giả
    with patch("main.vectorizer.transform_single", return_value=[0.1, 0.2]), \
         patch("main.retrieve_context") as mock_retrieval:
         
        mock_retrieval.return_value = [{"landmark_id": "lm_1", "name": "Biển", "_id": "1"}]
        
        response = client.post("/search", json={"query": "biển đẹp"})
        assert response.status_code == 200
        assert response.json()["data"][0]["name"] == "Biển"

def test_recommendations_success(client):
    """Test API /recommendations (RAG Flow)"""
    mock_llm_res = {
        "recommendations": [
            {"rank": 1, "name": "Đà Lạt", "justification_summary": "Lạnh", "suggested_activities": []}
        ]
    }
    
    with patch("main.vectorizer.transform_single"), \
         patch("main.retrieve_context", return_value=[{"landmark_id": "1", "name": "Đà Lạt"}]), \
         patch("main.call_llm_api", return_value=json.dumps(mock_llm_res)):
         
        response = client.post("/recommendations", json={"vibe_prompt": "thích lạnh"})
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["recommendations"][0]["name"] == "Đà Lạt"