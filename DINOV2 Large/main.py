from fastapi import FastAPI, UploadFile, File, HTTPException
from pymongo import MongoClient
from PIL import Image
import io
import timm
import torch
import numpy as np

from config import MONGO_URI, DB_NAME, COLLECTION_NAME, DESTINATION_NAME

# ------------------------------
# CONFIGURATION & DEVICE SETUP
# ------------------------------
# 1. Define device for GPU/CPU usage
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 2. Define the new model name
MODEL_NAME = "vit_large_patch14_dinov2"

# ------------------------------
# INIT APP + MONGO
# ------------------------------
app = FastAPI(
    title="DINOv2 Large Sightseeing Recognition API",
    description="Upload an image → DinoV2 Large embedding (1024-dim) → MongoDB similarity search → Return landmark info.",
    version="1.0.0"
)

try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    during_col = db[COLLECTION_NAME]       # During (DINOv2 embeddings)
    before_col = db[DESTINATION_NAME]      # Before (metadata only)
    print("✅ MongoDB connected")
except Exception as e:
    print(f"❌ DB connection failed: {e}")

# ------------------------------
# LOAD DINOv2 LARGE (with Optimization)
# ------------------------------
print(f"⏳ Loading DINOv2 Large ({MODEL_NAME}) on {device}...")

# 1. Load the Large model, move to device, and remove classification head (num_classes=0)
model = timm.create_model(MODEL_NAME, pretrained=True, num_classes=0)
model.to(device)

# 2. VRAM Optimization: Convert model weights to Half Precision (FP16)
# This is critical for running the Large model on 4GB VRAM
if device.type == 'cuda':
    model = model.half()

model.eval()
print("✅ DINOv2 Large (1024-dim) ready!")

# Preprocessing for DINOv2 (Remains the same, timm handles config changes)
transform = timm.data.create_transform(
    input_size=model.default_cfg["input_size"],
    mean=model.default_cfg["mean"],
    std=model.default_cfg["std"],
    crop_pct=model.default_cfg["crop_pct"],
)

# ------------------------------
# EMBEDDING FUNCTION
# ------------------------------
def embed_image(img: Image.Image):
    # 1. Prepare tensor and move to device
    tensor = transform(img).unsqueeze(0).to(device)
    
    # 2. Convert input tensor to half-precision to match the model
    if device.type == 'cuda':
        tensor = tensor.half()
        
    with torch.no_grad():
        # The model now directly outputs the 1024-dim pooled embedding
        emb = model(tensor)
        
    # 3. Convert back to standard float32 and move to CPU before converting to list
    return emb.squeeze(0).float().cpu().numpy().astype(np.float32).tolist()

# ------------------------------
# VECTOR SEARCH (MongoDB Atlas)
# ------------------------------
def search_similar_landmark(query_vector, limit=1):
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": query_vector,
                "numCandidates": 1024, # Optimized value
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
# API ENDPOINT
# ------------------------------
@app.post("/visual-search", tags=["Sightseeing Recognition"])
async def visual_search(file: UploadFile = File(...)):
    # 1) Read image
    try:
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image")

    # 2) Embed image using DINOv2 Large
    query_vector = embed_image(image)

    # 3) Search in During collection
    search_results = search_similar_landmark(query_vector, limit=1)
    if not search_results:
        return {"status": "not_found", "message": "No similar landmark found."}

    best_match = search_results[0]

    # 4) Similarity threshold
    if best_match["score"] < 0.6:
        return {
            "status": "not_found",
            "message": "Image does not match any known landmark.",
            "similarity_score": best_match["score"]
        }

    # 5) Lookup metadata in Before by landmark_id
    landmark_id = best_match["landmark_id"]
    landmark_info = before_col.find_one(
        {"landmark_id": landmark_id},
        {"_id": 0}  # hide Mongo _id
    )

    if not landmark_info:
        return {
            "status": "missing_info",
            "message": f"No metadata found for landmark_id {landmark_id}",
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