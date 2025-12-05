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

from PIL import Image
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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

# --- API CREATE ALBUM (ĐÃ SỬA THEO SCHEMA MỚI) ---
@app.post("/create-album")
async def create_album(files: List[UploadFile] = File(...)):
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=413, detail=f"Too many files. Max: {MAX_FILES}")
    
    logger.info(f"Processing {len(files)} photos...")
    extractor = MetadataExtractor()
    lighting_filter = LightingFilter()
    curator = CurationService()
    
    tasks = [process_single_photo(file, extractor, lighting_filter, curator) for file in files]
    photo_inputs = await asyncio.gather(*tasks, return_exceptions=True)
    
    valid_inputs = [p for p in photo_inputs if p is not None and not isinstance(p, Exception)]
    if not valid_inputs:
        raise HTTPException(status_code=500, detail="All photos failed to process")

    # Junk Filter
    non_rejected = [p for p in valid_inputs if not p.is_rejected and p.local_path]
    if non_rejected:
        loop = asyncio.get_event_loop()
        paths = [p.local_path for p in non_rejected]
        junk_results = await loop.run_in_executor(executor, is_junk_batch, paths)
        for photo, is_junk in zip(non_rejected, junk_results):
            if is_junk:
                photo.is_rejected = True
                photo.rejected_reason = "AI Detected Junk"

    try:
        # 1. Gom cụm (Clustering)
        # Lưu ý: ClusteringService trả về list các Album nội bộ, ta sẽ convert lại ở bước cuối
        raw_albums = ClusteringService.dispatch(valid_inputs)
        
        # Map nhanh để tra cứu dữ liệu gốc (lấy lat/lon, local_path)
        original_map = {p.filename: p for p in valid_inputs}
        
        # 2. Upload Cloudinary
        upload_queue = []
        for album in raw_albums:
            if album.method == "filters_rejected" or "Review Needed" in album.title:
                continue
            safe_tag = "".join(c for c in album.title if c.isalnum() or c in ('-', '_'))
            for photo in album.photos:
                original = original_map.get(photo.filename)
                if original and original.local_path and os.path.exists(original.local_path):
                    upload_queue.append((original.local_path, safe_tag))

        uploaded_map = cloud_service.upload_batch(upload_queue)
        
        # 3. Xây dựng Response chuẩn theo Schema Mới
        final_albums_response = []

        for album in raw_albums:
            is_junk = album.method == "filters_rejected" or "Review Needed" in album.title
            safe_tag = "".join(c for c in album.title if c.isalnum() or c in ('-', '_'))
            
            # Xử lý danh sách ảnh output chuẩn schema PhotoOutput
            output_photos = []
            has_cloud_photo = False

            for photo in album.photos:
                original = original_map.get(photo.filename)
                if not original: continue

                # Xác định URL
                img_url = None
                if not is_junk and original.local_path in uploaded_map:
                    img_url = uploaded_map[original.local_path]
                    has_cloud_photo = True
                elif original.local_path:
                    img_url = f"/images/{os.path.basename(original.local_path)}"

                # Mapping sang PhotoOutput (CHÚ Ý: latitude -> lat, longitude -> lon)
                p_out = PhotoOutput(
                    id=photo.id,
                    filename=photo.filename,
                    timestamp=photo.timestamp,
                    score=photo.score,
                    image_url=img_url,
                    lat=original.latitude,  # <--- Map field này
                    lon=original.longitude  # <--- Map field này
                )
                output_photos.append(p_out)
            
            # Tạo link Zip (chỉ nếu album sạch và có ảnh trên cloud)
            zip_url = None
            if not is_junk and has_cloud_photo:
                zip_url = cloud_service.create_album_zip_link(safe_tag)

            # Tạo Album Output (KHÔNG có cover_photo_url theo schema mới)
            album_out = Album(
                title=album.title,
                method=album.method,
                download_zip_url=zip_url,
                photos=output_photos
            )
            final_albums_response.append(album_out)

        logger.info(f"Created {len(final_albums_response)} albums")
        return {"albums": final_albums_response}
    
    except Exception as e:
        logger.error(f"Clustering error: {e}")
        import traceback
        traceback.print_exc()
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)