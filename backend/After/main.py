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
from schemas import PhotoInput
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

def save_image_to_disk(img: Image.Image, path: str):
    try:
        if hasattr(img, 'info'):
            exif_bytes = img.info.get("exif")
            if exif_bytes:
                img.save(path, "JPEG", quality=85, exif=exif_bytes, optimize=True)
                return
        img.save(path, "JPEG", quality=85, optimize=True)
    except Exception as e:
        logger.warning(f"Save failed: {e}")

def compute_image_hash(content: bytes) -> str:
    """🚀 V2: Fast hash for duplicate detection"""
    return hashlib.md5(content).hexdigest()

def load_and_prepare_image(content: bytes) -> Tuple[Image.Image, bytes]:
    """
    🚀 V2: Load image once, return both PIL object and raw bytes
    Thumbnail immediately to save memory
    """
    img = Image.open(io.BytesIO(content))
    img.load()
    img = img.convert("RGB")
    
    # Thumbnail early to reduce memory footprint
    img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
    
    return img, content

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
                cached.filename = file.filename
                cached.id = file.filename
                return cached
            
            safe_name = f"{uuid.uuid4()}.jpg"
            temp_path = os.path.join(PROCESSED_DIR, safe_name)
            
            loop = asyncio.get_event_loop()
            
            # 🚀 V2: Load image only ONCE
            img, raw_content = await loop.run_in_executor(
                executor, load_and_prepare_image, content
            )
            
            # Save to disk (needed for some filters)
            await loop.run_in_executor(executor, save_image_to_disk, img, temp_path)
            
            # 🚀 V2: Run lighting + metadata in parallel (pass image object to avoid reload)
            lighting_task = loop.run_in_executor(
                executor, lighting_filter.analyze_from_image, img
            )
            metadata_task = loop.run_in_executor(
                executor, extractor.get_metadata, temp_path
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
            
            # 🚀 V2: Calculate score using in-memory image (no disk read)
            score = await loop.run_in_executor(executor, curator.calculate_score, img)
            
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
                if original and original.local_path and os.path.exists(original.local_path):
                    image_filename = os.path.basename(original.local_path)
                    photo.image_url = f"/images/{image_filename}"
        
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)