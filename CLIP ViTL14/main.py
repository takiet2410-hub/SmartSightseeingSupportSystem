from fastapi import FastAPI, UploadFile, File, HTTPException
from sentence_transformers import SentenceTransformer
from pymongo import MongoClient
from PIL import Image
import io
from config import MONGO_URI, DB_NAME, COLLECTION_NAME, DESTINATION_NAME

# 1. Init App + DB
app = FastAPI()

try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    img_collection = db[COLLECTION_NAME]
    info_collection = db[DESTINATION_NAME]
    print("✅ Connected to MongoDB")
except Exception as e:
    print(f"❌ DB Connection Error: {e}")

# 2. Load CLIP ViT-L/14
print("⏳ Loading CLIP ViT-L/14...")
model = SentenceTransformer("clip-ViT-L-14")
print("✅ CLIP ViT-L/14 ready (768-dim embeddings).")

# --- SEARCH FUNCTION ---
def search_similar_landmark(query_vector, limit=1):
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
        {
            "$project": {
                "_id": 0,
                "landmark_id": 1,
                "image_url": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ]
    return list(img_collection.aggregate(pipeline))

# --- API ---
@app.post("/visual-search")
async def visual_search(file: UploadFile = File(...)):
    # B1: Read image
    try:
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file")

    # B2: Encode image → 768-dim vector
    query_vector = model.encode(image).tolist()

    # B3: Vector search
    results = search_similar_landmark(query_vector, limit=1)
    if not results:
        return {"message": "Không tìm thấy địa điểm tương đồng."}

    best = results[0]

    # Threshold (optional)
    if best["score"] < 0.60:
        return {
            "status": "not_found",
            "message": "Ảnh không giống địa điểm du lịch nào.",
            "similarity_score": best["score"]
        }

    # B4: Get landmark info
    landmark_id = best["landmark_id"]

    info = info_collection.find_one(
        {"landmark_id": landmark_id},
        {"_id": 0, "embedding_text": 0}
    )

    if not info:
        return {
            "message": f"Tìm thấy ảnh tương đồng nhưng không có thông tin landmark_id {landmark_id}"
        }

    # B5: Return
    return {
        "status": "success",
        "similarity_score": best["score"],
        "matched_image_url": best["image_url"],
        "data": info
    }
