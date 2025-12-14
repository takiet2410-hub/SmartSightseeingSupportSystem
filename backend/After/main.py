import os
import warnings

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
warnings.filterwarnings('ignore')

import asyncio
import io   
import uuid
import hashlib
from typing import List, Tuple, Optional
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

from config import TEMP_DIR, PROCESSED_DIR
from metadata import MetadataExtractor
from clustering.service import ClusteringService, get_model as get_clip_model
# Import đúng các Schema mới
from schemas import PhotoInput, PhotoOutput, Album, TripSummaryRequest, TripSummaryResponse, AlbumUpdateRequest
from summary_service import SummaryService
from filters.lighting import LightingFilter
from filters.junk_detector import is_junk_batch, get_model as get_junk_model
from logger_config import logger
from curation_service import CurationService
from cloudinary_service import CloudinaryService
from deps import get_current_user_id
from db import album_collection, summary_collection
from connection_manager import ConnectionManager

# 🚀 V2: Simple in-memory cache for duplicate detection
_processed_cache = {}

# Init Cloudinary
cloud_service = CloudinaryService()
manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application...")
    logger.info("Pre-warming ML models...")
    
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=2)
    
    async def load_models():
        await asyncio.gather(
            loop.run_in_executor(executor, get_junk_model),
            loop.run_in_executor(executor, get_clip_model)
        )
    
    await load_models()
    logger.info("Models loaded and ready")
    yield
    logger.info("Shutting down...")
    executor.shutdown(wait=True)

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

app.mount("/images", StaticFiles(directory=PROCESSED_DIR), name="images")

executor = ThreadPoolExecutor(max_workers=8)
MAX_CONCURRENT = 20
semaphore = asyncio.Semaphore(MAX_CONCURRENT)
MAX_FILES = 500
MAX_FILE_SIZE = 50 * 1024 * 1024

# --- GIỮ NGUYÊN CÁC HÀM XỬ LÝ ẢNH (save_image, hash, load...) ---
def save_image_to_disk(img_full: Image.Image, path: str, original_bytes: bytes = None, force_reencode: bool = False):
    try:
        if force_reencode or not original_bytes:
            if img_full.mode != 'RGB':
                img_full = img_full.convert('RGB')
            img_full.save(path, "JPEG", quality=95, optimize=True, progressive=True)
        else:
            with open(path, 'wb') as f:
                f.write(original_bytes)
    except Exception as e:
        logger.warning(f"Save failed: {e}, falling back to re-encode")
        if img_full.mode != 'RGB': img_full = img_full.convert('RGB')
        img_full.save(path, "JPEG", quality=95, optimize=True)

def compute_image_hash(content: bytes) -> str:
    return hashlib.md5(content).hexdigest()

def load_and_prepare_image(content: bytes) -> Tuple[Image.Image, Image.Image, bytes, bool]:
    is_heic = (content[:12].find(b'heic') != -1 or content[:12].find(b'heix') != -1 or content[:12].find(b'mif1') != -1)
    img_full = Image.open(io.BytesIO(content))
    img_full.load()
    exif_raw = img_full.info.get('exif')
    img_full = img_full.convert("RGB")
    if exif_raw: img_full.info['exif'] = exif_raw
    img_thumb = img_full.copy()
    img_thumb.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
    return img_full, img_thumb, content, is_heic

def delete_local_file(filename_or_path: str):
    """
    Xóa file trong thư mục uploads (nếu tồn tại)
    """
    try:
        # Nếu input là đường dẫn đầy đủ hoặc chỉ tên file
        filename = os.path.basename(filename_or_path)
        file_path = os.path.join("uploads", filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted local file: {filename}")
    except Exception as e:
        logger.error(f"Error deleting local file: {e}")

async def process_single_photo(file: UploadFile, extractor: MetadataExtractor, lighting_filter: LightingFilter, curator: CurationService) -> Optional[PhotoInput]:
    async with semaphore:
        try:
            content = await file.read()
            img_hash = compute_image_hash(content)
            if img_hash in _processed_cache:
                cached = _processed_cache[img_hash].model_copy()
                cached.filename = file.filename
                cached.id = file.filename
                return cached
            
            safe_name = f"{uuid.uuid4()}.jpg"
            temp_path = os.path.join(PROCESSED_DIR, safe_name)
            
            loop = asyncio.get_event_loop()
            img_full, img_thumb, raw_content, is_heic = await loop.run_in_executor(executor, load_and_prepare_image, content)
            
            metadata_task = loop.run_in_executor(executor, extractor.get_metadata_from_image, img_full)
            await loop.run_in_executor(executor, save_image_to_disk, img_full, temp_path, None if is_heic else raw_content, is_heic)
            
            lighting_task = loop.run_in_executor(executor, lighting_filter.analyze_from_image, img_thumb)
            is_good_light, light_reason = await lighting_task
            meta = await metadata_task
            
            if not is_good_light:
                result = PhotoInput(id=file.filename, filename=file.filename, local_path=temp_path, is_rejected=True, rejected_reason=light_reason)
                _processed_cache[img_hash] = result
                return result
            
            score = await loop.run_in_executor(executor, curator.calculate_score, img_thumb)
            result = PhotoInput(id=file.filename, filename=file.filename, local_path=temp_path, is_rejected=False, score=score, **meta)
            _processed_cache[img_hash] = result
            return result
        except Exception as e:
            logger.error(f"Error processing {file.filename}: {e}")
            return PhotoInput(id=file.filename, filename=file.filename, local_path="", is_rejected=True, rejected_reason=str(e))

@app.post("/create-album")
async def create_album(
    files: List[UploadFile] = File(...),
    current_user_id: str = Depends(get_current_user_id)
):
    if len(files) > MAX_FILES:
        raise HTTPException(413, f"Too many files. Max: {MAX_FILES}")
    
    logger.info(f"Processing {len(files)} photos for User {current_user_id}...")
    
    # 1. Processing (Extract, Light, Score)
    extractor = MetadataExtractor()
    lighting = LightingFilter()
    curator = CurationService()
    
    tasks = [process_single_photo(f, extractor, lighting, curator) for f in files]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    valid_inputs = [p for p in results if p and not isinstance(p, Exception)]
    if not valid_inputs:
        raise HTTPException(500, "All photos failed")

    # 2. Junk Filter
    clean_photos = [p for p in valid_inputs if not p.is_rejected and p.local_path]
    if clean_photos:
        loop = asyncio.get_event_loop()
        paths = [p.local_path for p in clean_photos]
        junk_res = await loop.run_in_executor(executor, is_junk_batch, paths)
        for p, is_junk in zip(clean_photos, junk_res):
            if is_junk:
                p.is_rejected = True
                p.rejected_reason = "AI Detected Junk"

    try:
        # 3. Clustering
        raw_albums = ClusteringService.dispatch(valid_inputs)
        original_map = {p.filename: p for p in valid_inputs}
        
        # [SỬA LỖI TẠI ĐÂY] Dùng Dictionary để lưu Tag thay vì setattr
        album_tags_map = {} 
        upload_queue = []
        
        # Dùng enumerate để lấy số thứ tự (index) của album
        for index, album in enumerate(raw_albums):
            if album.method == "filters_rejected" or "Review Needed" in album.title:
                continue
            
            # Tạo tag
            safe_tag = "".join(c for c in album.title if c.isalnum() or c in ('-', '_')) + f"_{uuid.uuid4().hex[:4]}"
            
            # Lưu vào map theo index
            album_tags_map[index] = safe_tag

            for photo in album.photos:
                orig = original_map.get(photo.filename)
                if orig and orig.local_path and os.path.exists(orig.local_path):
                    upload_queue.append((orig.local_path, safe_tag))
        
        # 4. Upload Cloudinary
        uploaded_map = cloud_service.upload_batch(upload_queue)
        
        # 5. Build Response
        final_albums = []
        db_inserts = []
        
        # Lặp lại với enumerate để lấy lại đúng tag
        for index, album in enumerate(raw_albums):
            is_junk = album.method == "filters_rejected" or "Review Needed" in album.title
            
            album_id = str(uuid.uuid4())
            output_photos = []
            db_photos_dict = []
            has_cloud_photo = False
            
            for photo in album.photos:
                orig = original_map.get(photo.filename)
                if not orig: continue
                
                img_url = None
                if not is_junk and orig.local_path in uploaded_map:
                    img_url = uploaded_map[orig.local_path]
                    has_cloud_photo = True
                elif orig.local_path:
                    img_url = f"/images/{os.path.basename(orig.local_path)}"
                
                p_out = PhotoOutput(
                    id=photo.id, filename=photo.filename, timestamp=photo.timestamp,
                    score=photo.score, image_url=img_url, 
                    lat=orig.latitude, lon=orig.longitude
                )
                output_photos.append(p_out)
                
                p_dict = p_out.dict()
                if p_dict['timestamp']: p_dict['timestamp'] = p_dict['timestamp'].isoformat()
                db_photos_dict.append(p_dict)
            
            # [SỬA LỖI] Lấy tag từ map thay vì getattr
            safe_tag = album_tags_map.get(index)
            
            zip_url = None
            cover_url = None
            
            if not is_junk and has_cloud_photo and safe_tag:
                zip_url = cloud_service.create_album_zip_link(safe_tag)
                for p in output_photos:
                    if p.image_url and "cloudinary" in p.image_url:
                        cover_url = p.image_url
                        break
            
            has_gps = any(
                p.lat is not None and p.lon is not None
                for p in output_photos
            )
            
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
            
            if not is_junk:
                doc = album_out.dict()
                doc['_id'] = album_id
                db_inserts.append(doc)
        
        if db_inserts:
            album_collection.insert_many(db_inserts)
            logger.info(f"Saved {len(db_inserts)} albums to MongoDB")
            
        return {"albums": final_albums}

    except Exception as e:
        logger.error(f"Logic Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, detail=str(e))
    
@app.get("/my-albums", response_model=List[Album])
async def get_my_albums(current_user_id: str = Depends(get_current_user_id)):
    try:
        # Tìm các album có user_id tương ứng
        cursor = album_collection.find({"user_id": current_user_id}).sort("created_at", -1)
        return [doc for doc in cursor]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.delete("/cleanup")
async def cleanup_images():
    _processed_cache.clear()
    return {"status": "cleaned"}

@app.post("/swagger-login")
async def swagger_login_proxy(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    API này chỉ dành cho Swagger UI.
    Nó nhận Form Data từ Swagger -> Chuyển thành JSON -> Gọi Auth Service.
    """
    # 1. Địa chỉ của Auth Service (Port 8001)
    auth_url = "http://localhost:8001/auth/login"
    
    # 2. Chuyển đổi dữ liệu sang JSON
    payload = {
        "username": form_data.username,
        "password": form_data.password
    }
    
    try:
        # 3. Gọi sang Auth Service
        response = requests.post(auth_url, json=payload)
        
        # 4. Trả kết quả về cho Swagger
        if response.status_code == 200:
            return response.json() # Trả về Token
        else:
            # Nếu lỗi (sai pass), trả về lỗi y hệt Auth trả về
            raise HTTPException(
                status_code=response.status_code, 
                detail=response.json().get("detail", "Login failed")
            )
            
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Không kết nối được tới Auth Service (Port 8001)")
    
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive, listen for messages (optional)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

# 🚀 3. UPDATE THE CREATE ENDPOINT (Save DB + Push to WebSocket)
@app.post("/summary/create", response_model=TripSummaryResponse)
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
        summary_doc = dict(result) if isinstance(result, dict) else result
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
async def get_summary_history(user_id: str = "test_runner"):
    """
    Get a list of all past trip summaries for this user.
    """
    try:
        # Fetch all records, sorted by newest first
        cursor = summary_collection.find(
            {"user_id": user_id},
            {"_id": 0} # Exclude MongoDB ID to avoid serialization issues
        ).sort("created_at", -1)
        
        history = list(cursor)
        return history
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
 
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)