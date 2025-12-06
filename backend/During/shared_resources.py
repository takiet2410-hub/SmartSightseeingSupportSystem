# shared_resources.py
from pymongo import MongoClient
from transformers import Dinov2Model, AutoImageProcessor
import torch.nn as nn
import torch
from core.config import MONGO_URI, DB_NAME, DURING_COLLECTION, MODEL_NAME, MODEL_PATH, DEVICE
import os
from PIL import Image
from typing import Dict, Any, List

model = None
processor = None
db = None
client = None

class FineTunedDINOv2(nn.Module):
    def __init__(self):
        super(FineTunedDINOv2, self).__init__()
        self.backbone = Dinov2Model.from_pretrained(MODEL_NAME)
    def forward(self, x):
        outputs = self.backbone(x)
        cls_token = outputs.last_hidden_state[:, 0]
        return nn.functional.normalize(cls_token, p=2, dim=1)

def load_resources():
    global model, processor, db, client
    print("🚀 Starting up application...")

    # DB connect
    try:
        client = MongoClient(MONGO_URI)
        client.admin.command('ping')
        db = client[DB_NAME]
        print("✅ Đã kết nối thành công đến MongoDB Atlas.")
    except Exception as e:
        db = None
        client = None
        print(f"❌ Lỗi kết nối MongoDB: {type(e).__name__}: {e}")
        # không raise để app vẫn khởi động (endpoints kiểm tra db is None)

    # Model load
    try:
        model_instance = FineTunedDINOv2()
        if os.path.exists(MODEL_PATH):
            checkpoint = torch.load(MODEL_PATH, map_location=DEVICE)
            state_dict = checkpoint.get("model_state_dict", checkpoint)
            new_state_dict = {k.replace("module.", ""): v for k, v in state_dict.items()}
            model_instance.load_state_dict(new_state_dict, strict=False)
        model_instance.to(DEVICE)
        model_instance.eval()
        model = model_instance
        processor = AutoImageProcessor.from_pretrained(MODEL_NAME)
        print("✅ Fine-tuned DINOv2 ready!")
    except Exception as e:
        model = None
        processor = None
        print(f"❌ Model loading failed: {type(e).__name__}: {e}")

def embed_image(img: Image.Image) -> List[float]:
    if model is None:
        raise RuntimeError("Model not loaded.")
    inputs = processor(images=img, return_tensors="pt").pixel_values.to(DEVICE)
    with torch.no_grad():
        embedding = model(inputs)
    return embedding.cpu().numpy().flatten().tolist()

def search_similar_landmark(query_vector: List[float], collection_name: str, limit: int = 1):
    if db is None:
        raise RuntimeError("Database not connected.")
    during_col = db[collection_name]
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": query_vector,
                "numCandidates": 1024,
                "limit": limit
            }
        },
        {"$project": {"_id": 0, "landmark_id": 1, "image_url": 1, "score": {"$meta": "vectorSearchScore"}}}
    ]
    try:
        return list(during_col.aggregate(pipeline))
    except Exception as e:
        # Nếu index tên khác, log thông báo rõ ràng
        print(f"❌ Vector search failed: {type(e).__name__}: {e}")
        raise
