from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from PIL import Image
import io
import torch
import torch.nn as nn
from transformers import Dinov2Model, AutoImageProcessor
import numpy as np
import os
from typing import Dict, Any

from core.config import MONGO_URI, DB_NAME, DURING_COLLECTION, BEFORE_COLLECTION

# --- CONFIGURATION FOR FINE-TUNED MODEL ---
MODEL_NAME = "facebook/dinov2-base"
MODEL_PATH = "backend/during/models/dinov2_hf_finetuned_ep30.pth" 
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"🚀 Using device: {DEVICE}")

# ------------------------------
# 1. FINE-TUNED DINOv2 ARCHITECTURE
# ------------------------------
class FineTunedDINOv2(nn.Module):
    """
    Defines the DINOv2 model architecture used for fine-tuning.
    Note: L2 normalization is crucial for vector search similarity.
    """
    def __init__(self):
        super(FineTunedDINOv2, self).__init__()
        # Use the Hugging Face Dinov2Model
        self.backbone = Dinov2Model.from_pretrained(MODEL_NAME)

    def forward(self, x):
        outputs = self.backbone(x)
        # We use the CLS token (the first token) as the image embedding
        cls_token = outputs.last_hidden_state[:, 0]
        # L2 normalization for vector search
        return nn.functional.normalize(cls_token, p=2, dim=1)

def load_finetuned_model() -> tuple[nn.Module, AutoImageProcessor]:
    """Loads the fine-tuned DINOv2 model and its associated image processor."""
    print(f"⏳ Loading fine-tuned model from {MODEL_PATH}...")
    model = FineTunedDINOv2()
    
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"❌ Could not find model file at {MODEL_PATH}")

    try:
        # Load weights
        checkpoint = torch.load(MODEL_PATH, map_location=DEVICE, weights_only=False)
        
        # Extract state_dict (handling checkpoint dict vs. raw weights)
        if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
            state_dict = checkpoint["model_state_dict"]
        else:
            state_dict = checkpoint

        # Remove prefix "module." if present (often from DataParallel training)
        new_state_dict = {}
        for k, v in state_dict.items():
            if k.startswith("module."):
                new_state_dict[k[7:]] = v
            else:
                new_state_dict[k] = v
        
        # Load weights into model
        try:
            model.load_state_dict(new_state_dict)
            print("✅ Successfully loaded weights!")
        except RuntimeError as e:
            # Fallback for key mismatch
            print(f"⚠️ Warning: Key mismatch detected. Attempting to load with strict=False...")
            model.load_state_dict(new_state_dict, strict=False)
            print("⚠️ Loaded (forced) successfully.")

    except Exception as e:
        raise Exception(f"❌ Failed to load model weights: {e}")
    
    model.to(DEVICE)
    model.eval() 
    
    # Load the official image processor for DINOv2
    processor = AutoImageProcessor.from_pretrained(MODEL_NAME)
    return model, processor

# ------------------------------
# 2. INIT APP + MONGO + MODEL
# ------------------------------
app = FastAPI(
    title="DINOv2 Sightseeing Recognition API",
    description="Upload an image → Fine-tuned DinoV2 embedding → MongoDB similarity search → Return landmark info.",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Cho phép mọi nguồn (Frontend) truy cập
    allow_credentials=True,
    allow_methods=["*"], # Cho phép mọi phương thức (POST, GET...)
    allow_headers=["*"], # Cho phép mọi header
)

@app.get("/")
def read_root():
    return {"status": "Running", "message": "Welcome to Smart Tourism API. Go to /docs for API documentation."}

try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    during_col = db[DURING_COLLECTION]       # During (DINOv2 embeddings)
    before_col = db[BEFORE_COLLECTION]      # Before (metadata only)
    print("✅ MongoDB connected")
except Exception as e:
    print(f"❌ DB connection failed: {e}")

try:
    # Load the fine-tuned model and processor globally
    model, processor = load_finetuned_model()
    print("✅ Fine-tuned DINOv2 ready!")
except Exception as e:
    # Exit or handle error if model load fails
    print(f"❌ Model loading failed: {e}")
    model = None # Set to None to prevent usage

# ------------------------------
# 3. EMBEDDING FUNCTION
# ------------------------------
def embed_image(img: Image.Image) -> list[float]:
    """Generates the vector embedding for an image using the fine-tuned model."""
    if model is None:
        raise RuntimeError("Model is not loaded.")
        
    # Preprocessing using the Hugging Face AutoImageProcessor
    inputs = processor(images=img, return_tensors="pt").pixel_values.to(DEVICE)

    with torch.no_grad():
        # The model's forward method returns the L2-normalized CLS token
        embedding_tensor = model(inputs)
    
    # Convert the embedding tensor to a standard Python list of floats
    # This should be a 768-dimensional vector for dinov2-base
    return embedding_tensor.cpu().numpy().flatten().tolist()

# ------------------------------
# 4. VECTOR SEARCH (MongoDB Atlas)
# ------------------------------
def search_similar_landmark(query_vector: list[float], limit: int = 1) -> list[Dict[str, Any]]:
    """Performs a vector search in the MongoDB Atlas 'during_col' collection."""
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index", # Ensure this matches your Atlas Search index name
                "path": "embedding",
                "queryVector": query_vector,
                "numCandidates": 1024,
                "limit": limit
            }
        },
        {
            "$project": {
                "_id": 0,
                "landmark_id": 1,
                "image_url": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ]
    return list(during_col.aggregate(pipeline))

# ------------------------------
# 5. API ENDPOINT
# ------------------------------
@app.post("/visual-search", tags=["Sightseeing Recognition"])
async def visual_search(file: UploadFile = File(...)):
    if model is None:
        raise HTTPException(status_code=503, detail="Model service is currently unavailable.")

    # 1) Read image
    try:
        image_data = await file.read()
        # Ensure image is in RGB format for DINOv2 processing
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file format or corruption.")

    # 2) Embed image using fine-tuned DINOv2
    try:
        query_vector = embed_image(image)
    except Exception as e:
        # Catch potential embedding errors (e.g., model not loaded correctly)
        raise HTTPException(status_code=500, detail=f"Embedding failed: {e}")

    # 3) Search in During collection
    search_results = search_similar_landmark(query_vector, limit=1)
    if not search_results:
        return {"status": "not_found", "message": "No similar landmark found in the database."}

    best_match = search_results[0]

    # 4) Similarity threshold (Adjust this score as needed for your fine-tuned model)
    # Cosine similarity score ranges from -1 (opposite) to 1 (identical).
    # 0.6 is a common starting point for a positive match.
    if best_match["score"] < 0.6:
        return {
            "status": "not_found",
            "message": "Image does not match any known landmark with high confidence.",
            "similarity_score": best_match["score"]
        }

    # 5) Lookup metadata in Before by landmark_id
    landmark_id = best_match["landmark_id"]

    landmark_info = before_col.find_one(
        {"landmark_id": landmark_id}, # Điều kiện tìm kiếm
        {
            "_id": 0,                  # Luôn ẩn ID mặc định của Mongo
            "text_chunk": 0,           # Ẩn dữ liệu text thô
            "v_hybrid": 0,             # QUAN TRỌNG: Ẩn vector này giúp response nhanh hơn rất nhiều
            "combined_tags_array": 0,  # Ẩn mảng tags
            "overall_rating": 0,
            "budget_range": 0,
            "season_tag": 0,           # Lưu ý: Trong ảnh tên là 'season_tag' (số ít)
            "available_time": 0,
            "companion_tag": 0
            # Bạn có thể thêm bất kỳ trường nào muốn ẩn vào đây với giá trị 0
        } 
    )

    if not landmark_info:
        return {
            "status": "missing_info",
            "message": f"No metadata found for landmark_id {landmark_id} in 'before' collection.",
            "similarity_score": best_match["score"]
        }

    # 6) Return result
    return {
        "status": "success",
        "similarity_score": best_match["score"],
        "landmark_id": landmark_id,
        "matched_image_url": best_match.get("image_url"),
        "landmark_info": landmark_info
    }

if __name__ == "__main__":
    # Chạy server (Dev mode)
    import uvicorn