import os
import warnings
import glob

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
warnings.filterwarnings('ignore')

import asyncio
import io   
import uuid
import hashlib
from typing import List, Tuple, Optional, Dict
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime
from bson import ObjectId

from PIL import Image
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import requests
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Body
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from pydantic import BaseModel

from config import TEMP_DIR, PROCESSED_DIR
from metadata import MetadataExtractor
# MERGED IMPORTS: Kept ClusteringService, added AlbumUpdateRequest from friend
from clustering.service import ClusteringService
from schemas import PhotoInput, PhotoOutput, Album, TripSummaryRequest, TripSummaryResponse, AlbumUpdateRequest, OSMGeocodeRequest
from summary_service import SummaryService
from filters.lighting import LightingFilter
from filters.junk_detector import is_junk_batch, get_model as get_junk_model
from logger_config import logger
from curation_service import CurationService
from cloudinary_service import CloudinaryService
from deps import get_current_user_id
from db import album_collection, summary_collection
from connection_manager import ConnectionManager

# Simple in-memory cache
_processed_cache = {}

cloud_service = CloudinaryService()
manager = ConnectionManager()
_extractor = None
_lighting_filter = None
_curator = None
summary_service = SummaryService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _extractor, _lighting_filter, _curator
    
    logger.info("Starting application...")
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=1)
    
    await loop.run_in_executor(executor, get_junk_model)
    
    _extractor = MetadataExtractor()
    _lighting_filter = LightingFilter()
    _curator = CurationService()
    logger.info("✅ Services initialized")
    yield
    executor.shutdown(wait=True)

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

app.mount("/images", StaticFiles(directory=PROCESSED_DIR), name="images")

# 🚀 YOUR OPTIMIZATION: Use 8 workers to prevent thread explosion
executor = ThreadPoolExecutor(max_workers=8)

MAX_FILES = 500

def save_image_to_disk(img_full: Image.Image, path: str, original_bytes: bytes = None):
    try:
        if original_bytes:
            with open(path, 'wb') as f:
                f.write(original_bytes)
        else:
            img_full.save(path, "JPEG", quality=95)
    except Exception as e:
        logger.warning(f"Save failed: {e}")

def compute_image_hash(content: bytes) -> str:
    return hashlib.md5(content).hexdigest()

# 🔽 YOUR OPTIMIZED WORKER FUNCTION (KEPT TO FIX FREEZING) 🔽
def process_image_job(file_info: dict) -> dict:
    """
    🚀 FIXED: Runs inside the thread pool. 
    Opens image, generates thumb, and runs analysis.
    FIX 2.0: Extracts metadata from ORIGINAL image, not thumbnail.
    """
    path = file_info['temp_path']
    filename = file_info['filename']
    
    try:
        # 1. Open Image (Heavy I/O)
        img = Image.open(path)
        
        # 2. Thumbnail (Heavy CPU)
        img_thumb = img.copy()
        img_thumb.thumbnail((512, 512), Image.Resampling.BILINEAR)
        
        # 3. Analyze
        # 🚀 FIX: Extract metadata from the ORIGINAL image (img), not the thumbnail
        metadata = _extractor.get_metadata_from_image(img)
        
        # Lighting & Score still use thumbnail (Faster & Accurate enough)
        is_good_light, light_reason = _lighting_filter.analyze_from_image(img_thumb)
        score = 0.0
        if is_good_light:
            score = _curator.calculate_score(img_thumb)
            
        return {
            'success': True,
            'filename': filename,
            'temp_path': path,
            'img_hash': file_info['img_hash'],
            'metadata': metadata,
            'is_good_light': is_good_light,
            'light_reason': light_reason,
            'score': score
        }
    except Exception as e:
        logger.error(f"Error processing {filename}: {e}")
        return {
            'success': False,
            'filename': filename,
            'error': str(e)
        }

# 🔽 FRIEND'S HELPER (KEPT FOR DELETION FEATURES) 🔽
def delete_local_file(filename_or_path: str):
    try:
        filename = os.path.basename(filename_or_path)
        file_path = os.path.join(PROCESSED_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass

@app.post("/create-album")
async def create_album(
    files: List[UploadFile] = File(...),
    current_user_id: str = Depends(get_current_user_id)
):
    if len(files) > MAX_FILES:
        raise HTTPException(413, f"Too many files. Max: {MAX_FILES}")
    
    logger.info(f"📥 Received {len(files)} photos for User {current_user_id}")
    
    loop = asyncio.get_event_loop()
    
    # STEP 0: Save all files to disk (Essential I/O)
    logger.info("💾 Saving files to disk...")
    file_contents = []
    
    saved_paths_map = {}
    save_futures = []
    
    for file in files:
        content = await file.read()
        file_contents.append((file.filename, content))
        
        safe_name = f"{uuid.uuid4()}.jpg"
        temp_path = os.path.join(PROCESSED_DIR, safe_name)
        saved_paths_map[file.filename] = temp_path
        
        save_futures.append(
            loop.run_in_executor(executor, save_image_to_disk, None, temp_path, content)
        )
    
    await asyncio.gather(*save_futures)
    logger.info(f"✅ Saved files to disk")

    # STEP 1: START CLOUDINARY UPLOAD (parallel)
    logger.info("☁️ Starting Cloudinary upload...")
    temp_tag = f"user_{current_user_id}_{uuid.uuid4().hex[:8]}"
    
    upload_list = []
    for filename, path in saved_paths_map.items():
        upload_list.append((path, temp_tag))
        
    upload_task = loop.run_in_executor(executor, cloud_service.upload_batch, upload_list)
    
    # STEP 2: PROCESS PHOTOS (Avoid Main Thread Blocking)
    logger.info("🔄 Processing photos (metadata, lighting, scoring)...")
    
    jobs = []
    cached_results = []
    
    for filename, content in file_contents:
        temp_path = saved_paths_map.get(filename)
        img_hash = compute_image_hash(content) # Fast MD5
        
        if img_hash in _processed_cache:
            # Cache Hit
            cached_photo = _processed_cache[img_hash].model_copy()
            cached_photo.id = filename
            cached_photo.filename = filename
            cached_photo.local_path = temp_path
            cached_results.append(cached_photo)
        else:
            # New Job
            jobs.append({
                'filename': filename,
                'temp_path': temp_path,
                'img_hash': img_hash
            })
            
    # Process batches
    BATCH_SIZE = 20
    processed_inputs = []
    
    for i in range(0, len(jobs), BATCH_SIZE):
        batch = jobs[i:i+BATCH_SIZE]
        
        # 🚀 YOUR FIX: Run image loading & analysis in executor
        results = await loop.run_in_executor(
            executor,
            lambda b: [process_image_job(j) for j in b],
            batch
        )
        
        for res in results:
            if not res['success']:
                processed_inputs.append(PhotoInput(
                     id=res['filename'], filename=res['filename'],
                     local_path=res.get('temp_path'), is_rejected=True, 
                     rejected_reason="Processing Error", score=0
                ))
                continue

            if not res['is_good_light']:
                p_in = PhotoInput(
                    id=res['filename'], filename=res['filename'],
                    local_path=res['temp_path'], is_rejected=True,
                    rejected_reason=res['light_reason'], score=0.0,
                    **res['metadata']
                )
            else:
                p_in = PhotoInput(
                    id=res['filename'], filename=res['filename'],
                    local_path=res['temp_path'], is_rejected=False,
                    score=res['score'],
                    **res['metadata']
                )
            
            _processed_cache[res['img_hash']] = p_in
            processed_inputs.append(p_in)
            
    all_inputs = processed_inputs + cached_results
    valid_inputs = [p for p in all_inputs if p]
    
    # STEP 3: Junk Detection
    clean_photos = [p for p in valid_inputs if not p.is_rejected]
    if clean_photos:
        paths = [p.local_path for p in clean_photos]
        junk_res = await loop.run_in_executor(executor, is_junk_batch, paths)
        for p, is_junk in zip(clean_photos, junk_res):
            if is_junk:
                p.is_rejected = True
                p.rejected_reason = "AI Detected Junk"
                p.score = 0.0

    try:
        # STEP 4: Clustering
        logger.info("🧩 Clustering photos into albums...")
        raw_albums = ClusteringService.dispatch(valid_inputs)
        original_map = {p.filename: p for p in valid_inputs}
        
        # STEP 5: Wait for Uploads
        logger.info("⏳ Waiting for Cloudinary upload...")
        uploaded_map = await upload_task
        
        logger.info(f"✅ Cloudinary upload complete. Items: {len(uploaded_map)}")
        
        # STEP 6: Build Response + Fix Tags + Zip
        final_albums = []
        db_inserts = []
        
        for album in raw_albums:
            album_id = str(uuid.uuid4())
            safe_tag = "".join(c for c in album.title if c.isalnum() or c in ('-', '_')) + f"_{uuid.uuid4().hex[:4]}"
            
            output_photos = []
            album_public_ids = [] 
            has_cloud_photo = False
            
            for photo in album.photos:
                orig = original_map.get(photo.filename)
                if not orig: continue
                
                img_url = None
                
                if orig.local_path in uploaded_map:
                    data = uploaded_map[orig.local_path]
                    img_url = data.get("url")
                    pid = data.get("public_id")
                    if pid:
                        album_public_ids.append(pid)
                    has_cloud_photo = True
                elif orig.local_path:
                    img_url = f"/images/{os.path.basename(orig.local_path)}"
                
                p_out = PhotoOutput(
                    id=photo.id, 
                    filename=photo.filename, 
                    timestamp=photo.timestamp,
                    score=orig.score,
                    image_url=img_url, 
                    lat=orig.latitude, 
                    lon=orig.longitude
                )
                output_photos.append(p_out)
            
            # 🚀 FIXED ZIP LOGIC (USING HIS DYNAMIC LINK + YOUR TAG FIX)
            zip_url = None
            if has_cloud_photo and album_public_ids:
                # A. Apply the specific album tag
                await loop.run_in_executor(
                    executor, 
                    cloud_service.add_tags, 
                    album_public_ids, 
                    safe_tag
                )
                
                # B. Generate Dynamic Zip Link (His Feature)
                zip_url = await loop.run_in_executor(
                    executor,
                    cloud_service.create_album_zip_link,
                    safe_tag 
                )
            
            cover_url = None
            for photo in output_photos:
                if photo.image_url and 'cloudinary' in photo.image_url:
                    cover_url = photo.image_url
                    break
            
            has_gps = any(p.lat is not None and p.lon is not None for p in output_photos)

            album_out = Album(
                id=album_id,
                user_id=current_user_id,
                title=album.title,
                method=album.method,
                download_zip_url=zip_url,
                cover_photo_url=cover_url,
                photos=output_photos,
                created_at=datetime.utcnow(),
                needs_manual_location=not has_gps
            )
            final_albums.append(album_out)
            
            doc = album_out.dict()
            doc['_id'] = album_id
            db_inserts.append(doc)
        
        if db_inserts:
            album_collection.insert_many(db_inserts)
        
        # 🚀 YOUR CLEANUP LOGIC
        logger.info("🧹 Cleaning up local temp files...")
        for file_path in saved_paths_map.values():
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.warning(f"Failed to delete {file_path}: {e}")
        
        return {"albums": final_albums}

    except Exception as e:
        logger.error(f"Logic Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.delete("/cleanup")
async def cleanup_images():
    _processed_cache.clear()
    files = glob.glob(os.path.join(PROCESSED_DIR, "*"))
    count = 0
    for f in files:
        try:
            os.remove(f)
            count += 1
        except Exception:
            pass
    return {"status": "cleaned", "disk_files_removed": count}

@app.get("/my-albums", response_model=List[Album])
async def get_my_albums(current_user_id: str = Depends(get_current_user_id)):
    try:
        # Tìm các album có user_id tương ứng
        cursor = album_collection.find({"user_id": current_user_id}).sort("created_at", -1)
        return [doc for doc in cursor]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/swagger-login")
async def swagger_login_proxy(form_data: OAuth2PasswordRequestForm = Depends()):
    auth_url = "http://localhost:8001/auth/login"
    try:
        response = requests.post(auth_url, json={"username": form_data.username, "password": form_data.password})
        if response.status_code == 200: return response.json()
        raise HTTPException(response.status_code, response.json().get("detail"))
    except Exception:
        raise HTTPException(503, "Auth Service Unavailable")

# --- SUMMARY FEATURES ---
@app.post("/summary/create")
async def create_trip_summary(
    request: TripSummaryRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Generate trip summary from album data
    Supports both real user tokens and test scripts
    """
    try:
        summary_service = SummaryService()
        
        # ✅ Handle manual_locations (can be dicts or Pydantic models)
        manual_locs = []
        if request.manual_locations:
            for loc in request.manual_locations:
                if isinstance(loc, dict):
                    manual_locs.append(loc)
                elif hasattr(loc, 'model_dump'):
                    manual_locs.append(loc.model_dump())
                elif hasattr(loc, 'dict'):
                    manual_locs.append(loc.dict())

                else:
                    logger.warning(f"Unknown manual_location type: {type(loc)}")
        
        # A. Generate summary
        result = summary_service.generate_summary(
            album_data=request.album_data,
            manual_locations=manual_locs
        )
        
        # B. Save to MongoDB
        summary_doc = result.copy()
        summary_doc["created_at"] = datetime.utcnow()
        summary_doc["user_id"] = current_user_id
        
        try:
            summary_collection.insert_one(summary_doc)
            logger.info(f"✅ Saved trip summary to MongoDB")
        except Exception as e:
            logger.error(f"MongoDB save failed: {e}")
        
        # C. Push to WebSocket
        try:
            await manager.send_personal_message(result, current_user_id)
            logger.info(f"✅ Pushed to WebSocket for user: {current_user_id}")
        except Exception as e:
            logger.error(f"WebSocket push failed: {e}")
        
        return result
        
    except Exception as e:
        logger.error(f"Summary error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/summary/history")
async def get_summary_history(current_user_id: str = Depends(get_current_user_id)):
    try:
        cursor = summary_collection.find({"user_id": current_user_id}, {"_id": 0}).sort("created_at", -1)
        return list(cursor)
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return []
    
@app.delete("/albums/{album_id}")
async def delete_album(
    album_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    # 1. Tìm album trước để lấy danh sách ảnh
    album = album_collection.find_one({"_id": album_id, "user_id": current_user_id})
    
    if not album:
        raise HTTPException(status_code=404, detail="Album không tồn tại")

    # 2. Thu thập danh sách cần xóa
    cloud_public_ids = []
    
    # Duyệt qua từng ảnh trong album
    if "photos" in album:
        for photo in album["photos"]:
            img_url = photo.get("image_url")
            
            if img_url:
                # A. Nếu là ảnh Cloudinary -> Lấy Public ID
                if "cloudinary" in img_url:
                    pid = cloud_service.get_public_id_from_url(img_url)
                    if pid: cloud_public_ids.append(pid)
                
                # B. Xóa file Local (Thumbnail/Original)
                # Dù đã up lên cloud hay chưa, file gốc vẫn có thể nằm trong folder uploads
                delete_local_file(photo.get("filename")) 
                # Hoặc nếu img_url là local path (/images/abc.jpg)
                delete_local_file(img_url)

    # 3. Gửi lệnh xóa lên Cloudinary (Chạy ngầm/Async cũng được)
    if cloud_public_ids:
        cloud_service.delete_resources(cloud_public_ids)

    # 4. Xóa trong Database
    album_collection.delete_one({"_id": album_id})
    
    return {"message": f"Đã xóa album {album_id} và dọn dẹp {len(cloud_public_ids)} ảnh trên cloud"}

# 2. ĐỔI TÊN ALBUM
@app.patch("/albums/{album_id}/rename")
async def rename_album(
    album_id: str,
    request: AlbumUpdateRequest, # Body JSON: {"title": "Tên Mới"}
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Đổi tên Album.
    """
    if not request.title.strip():
        raise HTTPException(status_code=400, detail="Tên album không được để trống")

    result = album_collection.update_one(
        {"_id": album_id, "user_id": current_user_id},
        {"$set": {"title": request.title}} # Lệnh update của MongoDB
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Album không tìm thấy")

    return {"message": "Đổi tên thành công", "new_title": request.title}

# 3. XÓA 1 ẢNH KHỎI ALBUM
@app.delete("/albums/{album_id}/photos/{photo_id}")
async def delete_photo_from_album(
    album_id: str,
    photo_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    # 1. Tìm album
    album = album_collection.find_one({"_id": album_id, "user_id": current_user_id})
    if not album:
        raise HTTPException(status_code=404, detail="Album không tìm thấy")
    
    # 2. Tìm ảnh trong mảng photos
    target_photo = None
    for p in album.get("photos", []):
        if p.get("id") == photo_id:
            target_photo = p
            break
            
    if not target_photo:
        raise HTTPException(404, "Ảnh không tồn tại trong album")

    # 3. Xử lý xóa file vật lý
    img_url = target_photo.get("image_url")
    if img_url:
        # Xóa trên Cloudinary
        if "cloudinary" in img_url:
            pid = cloud_service.get_public_id_from_url(img_url)
            if pid:
                cloud_service.delete_resources([pid]) # Xóa 1 cái
        
        # Xóa dưới Local
        delete_local_file(target_photo.get("filename"))
        delete_local_file(img_url)

    # 4. Xóa khỏi Database (MongoDB $pull)
    result = album_collection.update_one(
        {"_id": album_id},
        {"$pull": {"photos": {"id": photo_id}}} 
    )

    return {"message": f"Đã xóa ảnh {photo_id} vĩnh viễn"}

# --- [SHARE ALBUM FEATURE] ---

# 1. API: TẠO LINK CHIA SẺ (Chỉ chủ album mới được gọi)
@app.post("/albums/{album_id}/share")
async def create_share_link(
    album_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Sinh ra một URL công khai cho album.
    """
    # Tìm album
    album = album_collection.find_one({"_id": album_id, "user_id": current_user_id})
    if not album:
        raise HTTPException(404, "Album không tìm thấy")
    
    # Kiểm tra xem đã có token chưa, nếu chưa thì tạo mới
    share_token = album.get("share_token")
    if not share_token:
        share_token = str(uuid.uuid4()) # Sinh mã ngẫu nhiên duy nhất
        
        # Cập nhật vào DB
        album_collection.update_one(
            {"_id": album_id},
            {
                "$set": {
                    "share_token": share_token,
                    "is_public": True
                }
            }
        )
    
    # Trả về đường dẫn (Frontend sẽ ghép thêm domain của web vào)
    # Ví dụ Frontend sẽ hiển thị: https://my-app.com/shared/abc-xyz-123
    return {
        "message": "Đã tạo link chia sẻ",
        "share_token": share_token,
        "full_url_hint": f"/shared-albums/{share_token}"
    }


# 2. API: TẮT CHIA SẺ (Revoke Link)
@app.delete("/albums/{album_id}/share")
async def revoke_share_link(
    album_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Hủy bỏ link chia sẻ. Người ngoài sẽ không xem được nữa.
    """
    result = album_collection.update_one(
        {"_id": album_id, "user_id": current_user_id},
        {
            "$unset": {"share_token": ""}, # Xóa trường token
            "$set": {"is_public": False}
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(404, "Album không tìm thấy")
        
    return {"message": "Đã tắt tính năng chia sẻ cho album này"}


# 3. API: XEM ALBUM CÔNG KHAI (KHÔNG CẦN LOGIN)
# Lưu ý: Không có 'Depends(get_current_user_id)' ở đây
@app.get("/shared-albums/{share_token}")
async def view_shared_album(share_token: str):
    """
    API dành cho người lạ (Guest). 
    Chỉ cần có share_token là xem được ảnh.
    """
    # Tìm album dựa vào token và cờ is_public
    album = album_collection.find_one({
        "share_token": share_token,
        "is_public": True
    })
    
    if not album:
        raise HTTPException(404, "Album không tồn tại hoặc link đã hết hạn")
    
    # Chuẩn hóa dữ liệu trả về (Ẩn thông tin nhạy cảm nếu cần)
    # Ở đây ta trả về giống hệt cấu trúc Album bình thường
    
    # Chuyển đổi timestamp sang string nếu cần thiết cho frontend
    photos = album.get("photos", [])
    
    return {
        "title": album.get("title"),
        "cover_photo_url": album.get("cover_photo_url"),
        "download_zip_url": album.get("download_zip_url"),
        "photos": photos,
        "owner_id": album.get("user_id") # (Tùy chọn) Cho biết ai là chủ
    }

@app.delete("/summary/{summary_id}")
async def delete_trip_summary(
    summary_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    try:
        result = summary_collection.delete_one({
            "_id": ObjectId(summary_id),
            "user_id": current_user_id
        })

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail="Trip summary không tồn tại hoặc không có quyền xóa"
            )

        return {
            "message": "Đã xóa trip summary",
            "summary_id": summary_id
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@app.post("/geocode/osm")
async def geocode_osm(
    payload: OSMGeocodeRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    address = payload.address.strip()
    if not address:
        raise HTTPException(400, "Address is required")

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": address,
        "format": "json",
        "limit": 5,
        "countrycodes": "vn",
        "accept-language": "vi"
    }

    headers = {
        # ⚠️ bắt buộc theo rule OSM
        "User-Agent": "photo-trip-app/1.0 (contact@yourdomain.com)"
    }

    resp = requests.get(url, params=params, headers=headers, timeout=5)
    results = resp.json()

    if not results:
        raise HTTPException(404, "Address not found")

    return [
        {
            "lat": float(r["lat"]),
            "lon": float(r["lon"]),
            "display_name": r["display_name"]
        }
        for r in results
    ]

 
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8003)
