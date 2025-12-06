# detection_history.py
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from typing import List, Dict, Any
import shared_resources  # db, model, helpers
from auth_deps import get_current_user_id

router = APIRouter(tags=["User History"])
HISTORY_COLLECTION_NAME = "Detection_History"

def add_history_record(user_id: str, landmark_data: Dict[str, Any]):
    if shared_resources.db is None:
        print("⚠️ Database not connected. Cannot save history.")
        return

    collection = shared_resources.db[HISTORY_COLLECTION_NAME]

    record = {
        "landmark_id": landmark_data.get("landmark_id"),
        "name": landmark_data.get("landmark_info", {}).get("name", "Unknown"),
        "image_url": landmark_data.get("matched_image_url"),
        "timestamp": datetime.utcnow(),
        "similarity_score": landmark_data.get("similarity_score")
    }

    # 1. Lấy record mới nhất trong history
    existing = collection.find_one(
        {"user_id": user_id},
        {"history": {"$slice": 1}}
    )

    # 2. Nếu history tồn tại và giống hệt -> bỏ qua
    if existing and existing.get("history"):
        last = existing["history"][0]
        if (
            last["landmark_id"] == record["landmark_id"] and
            last["image_url"] == record["image_url"] and
            abs(last["similarity_score"] - record["similarity_score"]) < 1e-6
        ):
            print("⛔ Duplicate record detected. Skip saving.")
            return

    # 3. Nếu không trùng -> lưu
    collection.update_one(
        {"user_id": user_id},
        {
            "$push": {
                "history": {
                    "$each": [record],
                    "$position": 0,
                    "$slice": 50
                }
            },
            "$setOnInsert": {"user_id": user_id, "created_at": datetime.utcnow()}
        },
        upsert=True
    )

    print(f"✅ Saved history for user {user_id}: Landmark {record['landmark_id']}")