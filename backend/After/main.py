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
import uuid
from datetime import datetime

from PIL import Image
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import requests
from fastapi.security import OAuth2PasswordRequestForm

from config import TEMP_DIR, PROCESSED_DIR
from metadata import MetadataExtractor
from clustering.service import ClusteringService, get_model as get_clip_model
# Import đúng các Schema mới
from schemas import PhotoInput, PhotoOutput, Album, TripSummaryRequest, TripSummaryResponse
from summary_service import SummaryService
from filters.lighting import LightingFilter
from filters.junk_detector import is_junk_batch, get_model as get_junk_model
from logger_config import logger
from curation_service import CurationService
from cloudinary_service import CloudinaryService
from deps import get_current_user_id
from db import album_collection

# 🚀 V2: Simple in-memory cache for duplicate detection
_processed_cache = {}

# Init Cloudinary
cloud_service = CloudinaryService()

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
        
        # Lặp qua từng album
        for index, album in enumerate(raw_albums):
            is_junk = album.method == "filters_rejected" or "Review Needed" in album.title
            
            # Tạo ID mới cho mỗi album (Khắc phục lỗi duplicate key)
            album_id = str(uuid.uuid4())
            
            output_photos = []
            db_photos_dict = []
            
            # [DANH SÁCH MỚI] Gom đường dẫn file trên máy để nén Zip
            local_files_for_zip = [] 
            
            cover_url = None
            
            for photo in album.photos:
                orig = original_map.get(photo.filename)
                if not orig: continue
                
                img_url = None
                
                # Logic lấy URL ảnh
                if not is_junk and orig.local_path in uploaded_map:
                    img_url = uploaded_map[orig.local_path]
                    
                    # Lấy ảnh bìa
                    if not cover_url: cover_url = img_url
                    
                    # [QUAN TRỌNG] Thêm đường dẫn file gốc vào danh sách nén
                    if orig.local_path and os.path.exists(orig.local_path):
                        local_files_for_zip.append(orig.local_path)
                        
                elif orig.local_path:
                    img_url = f"/images/{os.path.basename(orig.local_path)}"
                
                p_out = PhotoOutput(
                    id=photo.id, filename=photo.filename, timestamp=photo.timestamp,
                    score=photo.score, image_url=img_url, 
                    lat=orig.latitude, lon=orig.longitude
                )
                output_photos.append(p_out)
                
                # Tạo dict cho DB
                p_dict = p_out.dict()
                if p_dict.get('timestamp'): 
                    p_dict['timestamp'] = p_dict['timestamp'].isoformat()
                db_photos_dict.append(p_dict)
            
            # Tạo Link Zip (Gọi hàm mới: Nén Local -> Upload Raw)
            zip_url = None
            if not is_junk and local_files_for_zip:
                zip_url = cloud_service.create_and_upload_zip(album.title, local_files_for_zip)
            
            # Tạo Object Album
            album_out = Album(
                id=album_id,
                user_id=current_user_id,
                title=album.title,
                method=album.method,
                download_zip_url=zip_url,
                cover_photo_url=cover_url,
                photos=output_photos,
                created_at=datetime.utcnow()
            )
            final_albums.append(album_out)
            
            # Insert vào DB
            if not is_junk:
                doc = album_out.dict()
                doc['_id'] = album_id
                db_inserts.append(doc)
        
        # Lưu vào MongoDB
        if db_inserts:
            album_collection.insert_many(db_inserts)
            logger.info(f"💾 Saved {len(db_inserts)} albums to MongoDB")
            
        return {"albums": final_albums}
        
        # Lưu DB
        if db_inserts:
            try:
                album_collection.insert_many(db_inserts)
                logger.info(f"💾 Saved {len(db_inserts)} albums to MongoDB")
            except Exception as db_err:
                logger.error(f"❌ DB Insert Error: {db_err}")
                # Không raise lỗi ở đây để vẫn trả về kết quả cho user xem

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

@app.post("/summary/create", response_model=TripSummaryResponse)
async def create_trip_summary(request: TripSummaryRequest):
    try:
        summary_service = SummaryService()
        manual_locs_dict = [m.dict() for m in request.manual_locations]
        
        # request.album_data giờ là Dict theo schema, truyền thẳng vào service
        result = summary_service.generate_summary(
            album_data=request.album_data,
            manual_locations=manual_locs_dict
        )
        return result
    except Exception as e:
        logger.error(f"Summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
    
 
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)