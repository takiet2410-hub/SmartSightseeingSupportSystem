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
from schemas import PhotoInput, TripSummaryRequest, TripSummaryResponse
from summary_service import SummaryService
from filters.lighting import LightingFilter
from filters.junk_detector import is_junk_batch, get_model as get_junk_model
from logger_config import logger
from curation_service import CurationService

# 🚀 V2: Simple in-memory cache for duplicate detection
_processed_cache = {}

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

def save_image_to_disk(img_full: Image.Image, path: str, original_bytes: bytes = None, force_reencode: bool = False):
    """
    🚀 V2.2: Save original quality for display with HEIC fix
    - Priority 1: Save original bytes (no re-encoding) IF not HEIC
    - Priority 2: Re-encode HEIC as proper JPEG
    - Priority 3: Save high-quality JPEG (95%)
    """
    try:
        # HEIC files MUST be re-encoded (browsers can't display HEIC)
        if force_reencode or not original_bytes:
            # Force RGB mode
            if img_full.mode != 'RGB':
                img_full = img_full.convert('RGB')
            
            # Save as clean JPEG
            img_full.save(path, "JPEG", quality=95, optimize=True, progressive=True)
        else:
            # Non-HEIC: Save original bytes directly (no quality loss)
            with open(path, 'wb') as f:
                f.write(original_bytes)
                
    except Exception as e:
        logger.warning(f"Save failed: {e}, falling back to re-encode")
        # Fallback: Always re-encode on error
        if img_full.mode != 'RGB':
            img_full = img_full.convert('RGB')
        img_full.save(path, "JPEG", quality=95, optimize=True)

def compute_image_hash(content: bytes) -> str:
    """🚀 V2: Fast hash for duplicate detection"""
    return hashlib.md5(content).hexdigest()

def load_and_prepare_image(content: bytes) -> Tuple[Image.Image, Image.Image, bytes, bool]:
    """
    🚀 V2.2: Load image once, return both versions + HEIC detection
    - img_full: Full resolution for display
    - img_thumb: Thumbnail for fast ML processing
    - content: Original bytes for lossless save
    - is_heic: Flag to force re-encoding
    """
    # Detect HEIC format by checking magic bytes
    is_heic = (
        content[:12].find(b'heic') != -1 or 
        content[:12].find(b'heix') != -1 or
        content[:12].find(b'mif1') != -1  # Some HEIC variants
    )
    
    img_full = Image.open(io.BytesIO(content))
    img_full.load()
    img_full = img_full.convert("RGB")
    
    # Create thumbnail for ML processing (speed optimization)
    img_thumb = img_full.copy()
    img_thumb.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
    
    return img_full, img_thumb, content, is_heic

async def process_single_photo(
    file: UploadFile,
    extractor: MetadataExtractor,
    lighting_filter: LightingFilter,
    curator: CurationService
) -> Optional[PhotoInput]:
    async with semaphore:
        try:
            content = await file.read()
            
            # 🚀 V2: Check cache for duplicates
            img_hash = compute_image_hash(content)
            if img_hash in _processed_cache:
                logger.info(f"{file.filename}: Duplicate detected (using cache)")
                cached = _processed_cache[img_hash]
                # Return cached result with new filename
                cached_copy = cached.model_copy()
                cached_copy.filename = file.filename
                cached_copy.id = file.filename
                return cached_copy
            
            safe_name = f"{uuid.uuid4()}.jpg"
            temp_path = os.path.join(PROCESSED_DIR, safe_name)
            
            loop = asyncio.get_event_loop()
            
            # 🚀 V2.1: Load once, get both full-res and thumbnail
            img_full, img_thumb, raw_content, is_heic = await loop.run_in_executor(
                executor, load_and_prepare_image, content
            )
            
            metadata_task = loop.run_in_executor(
                executor, extractor.get_metadata_from_image, img_full
            )

            # 🚀 V2.1: Save ORIGINAL quality for frontend display
            await loop.run_in_executor(
                executor, save_image_to_disk, img_full, temp_path, None if is_heic else raw_content, is_heic
            )
            
            # 🚀 V2.1: Use THUMBNAIL for all processing (faster)
            lighting_task = loop.run_in_executor(
                executor, lighting_filter.analyze_from_image, img_thumb
            )
            
            is_good_light, light_reason = await lighting_task
            meta = await metadata_task
            
            if not is_good_light:
                logger.info(f"{file.filename}: {light_reason}")
                result = PhotoInput(
                    id=file.filename,
                    filename=file.filename,
                    local_path=temp_path,
                    is_rejected=True,
                    rejected_reason=light_reason
                )
                _processed_cache[img_hash] = result
                return result
            
            # 🚀 V2.1: Calculate score using thumbnail (faster, no quality impact)
            score = await loop.run_in_executor(executor, curator.calculate_score, img_thumb)
            
            result = PhotoInput(
                id=file.filename,
                filename=file.filename,
                local_path=temp_path,
                is_rejected=False,
                score=score,
                **meta
            )
            
            # Cache for future duplicates
            _processed_cache[img_hash] = result
            
            return result
        
        except Exception as e:
            logger.error(f"Error processing {file.filename}: {e}")
            return PhotoInput(
                id=file.filename,
                filename=file.filename,
                local_path="",
                is_rejected=True,
                rejected_reason=f"Processing error: {str(e)}"
            )

@app.post("/create-album")
async def create_album(files: List[UploadFile] = File(...)):
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=413, detail=f"Too many files. Maximum: {MAX_FILES}")
    
    for file in files:
        if file.size and file.size > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"{file.filename} exceeds 50MB limit")
    
    logger.info(f"Processing {len(files)} photos...")
    
    extractor = MetadataExtractor()
    lighting_filter = LightingFilter()
    curator = CurationService()
    
    # Process all photos
    tasks = [process_single_photo(file, extractor, lighting_filter, curator) for file in files]
    photo_inputs = await asyncio.gather(*tasks, return_exceptions=True)
    
    valid_inputs = []
    for i, result in enumerate(photo_inputs):
        if isinstance(result, Exception):
            logger.error(f"Task {i} failed: {result}")
        elif result is not None:
            valid_inputs.append(result)
    
    if not valid_inputs:
        raise HTTPException(status_code=500, detail="All photos failed to process")
    
    # 🚀 V2: Only run junk detection on photos that passed lighting filter
    non_rejected = [p for p in valid_inputs if not p.is_rejected and p.local_path]
    
    if non_rejected:
        logger.info(f"Running junk detection on {len(non_rejected)} photos...")
        loop = asyncio.get_event_loop()
        paths = [p.local_path for p in non_rejected]
        junk_results = await loop.run_in_executor(executor, is_junk_batch, paths)
        
        for photo, is_junk_photo in zip(non_rejected, junk_results):
            if is_junk_photo:
                logger.info(f"{photo.filename}: Junk detected")
                photo.is_rejected = True
                photo.rejected_reason = "AI Detected Junk"
    
    try:
        albums = ClusteringService.dispatch(valid_inputs)
        
        # Add image URLs
        for album in albums:
            for photo in album.photos:
                original = next((p for p in valid_inputs if p.filename == photo.filename), None)
                if original:
                    # Add image URL
                    if original.local_path and os.path.exists(original.local_path):
                        image_filename = os.path.basename(original.local_path)
                        photo.image_url = f"/images/{image_filename}"
                    
                    # Add GPS coordinates to PhotoOutput
                    photo.lat = original.latitude
                    photo.lon = original.longitude
        
        logger.info(f"Created {len(albums)} albums")
        return {"albums": albums}
    
    except Exception as e:
        logger.error(f"Clustering failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "max_concurrent": MAX_CONCURRENT,
        "max_files": MAX_FILES,
        "max_file_size_mb": MAX_FILE_SIZE / 1024 / 1024,
        "cache_size": len(_processed_cache),
        "temp_dir": TEMP_DIR,
        "processed_dir": PROCESSED_DIR 
    }

@app.delete("/cleanup")
async def cleanup_images():
    """Delete all processed images and clear cache"""
    try:
        count = 0
        for filename in os.listdir(PROCESSED_DIR):
            file_path = os.path.join(PROCESSED_DIR, filename)
            if os.path.isfile(file_path) and filename.endswith('.jpg'):
                os.remove(file_path)
                count += 1
        
        # Clear cache
        _processed_cache.clear()
        
        return {"status": "success", "deleted": count, "cache_cleared": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/summary/create", response_model=TripSummaryResponse)
async def create_trip_summary(request: TripSummaryRequest):
    """
    Generate trip summary with map and statistics
    """
    try:
        summary_service = SummaryService()
        
        # Convert Pydantic models to dicts
        manual_locs_dict = [m.dict() for m in request.manual_locations]
        
        result = summary_service.generate_summary(
            album_data=request.album_data,
            manual_locations=manual_locs_dict
        )
        
        return result
    except Exception as e:
        logger.error(f"Trip summary generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)