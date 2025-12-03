import os
import warnings

# Suppress all warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
warnings.filterwarnings('ignore')

import asyncio
import io
import uuid
from typing import List
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

# Lifespan context manager for startup/shutdown
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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Mount static files directory for serving images
app.mount("/images", StaticFiles(directory=PROCESSED_DIR), name="images")

# Thread pool for CPU-bound operations - INCREASED for better parallelism
executor = ThreadPoolExecutor(max_workers=8)

# Concurrency limiter
MAX_CONCURRENT = 20  # Increased from 10
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

# Input limits
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

async def process_single_photo(
    file: UploadFile,
    extractor: MetadataExtractor,
    lighting_filter: LightingFilter,
    curator: CurationService
) -> PhotoInput:
    async with semaphore:
        safe_name = f"{uuid.uuid4()}.jpg"
        temp_path = os.path.join(PROCESSED_DIR, safe_name) 
        
        try:
            content = await file.read()
            loop = asyncio.get_event_loop()

            def open_image(b):
                i = Image.open(io.BytesIO(b))
                i.load()
                return i.convert("RGB")
            
            img = await loop.run_in_executor(executor, open_image, content)
            
            # 🚀 OPTIMIZATION: Thumbnail for faster processing
            img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            
            await loop.run_in_executor(executor, save_image_to_disk, img, temp_path)
            
            # 🚀 OPTIMIZATION: Run filters in parallel
            filter_results = await asyncio.gather(
                loop.run_in_executor(executor, lighting_filter.analyze, temp_path),
                loop.run_in_executor(executor, extractor.get_metadata, temp_path),
                return_exceptions=True
            )
            
            is_good_light, light_reason = filter_results[0]
            meta = filter_results[1]
            
            if not is_good_light:
                logger.info(f"{file.filename}: {light_reason}")
                return PhotoInput(
                    id=file.filename,
                    filename=file.filename,
                    local_path=temp_path,
                    is_rejected=True,
                    rejected_reason=light_reason
                )
            
            # 🚀 Calculate aesthetic score (using already-loaded image)
            score = await loop.run_in_executor(executor, curator.calculate_score, img)
            
            return PhotoInput(
                id=file.filename,
                filename=file.filename,
                local_path=temp_path,
                is_rejected=False,
                score=score,
                **meta
            )
        
        except Exception as e:
            logger.error(f"Error processing {file.filename}: {e}")
            return PhotoInput(
                id=file.filename,
                filename=file.filename,
                local_path=temp_path,
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
        else:
            valid_inputs.append(result)
    
    if not valid_inputs:
        raise HTTPException(status_code=500, detail="All photos failed to process")
    
    # 🚀 OPTIMIZATION: Batch junk detection
    non_rejected = [p for p in valid_inputs if not p.is_rejected]
    
    if non_rejected:
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
        
        # Add image URLs to photos
        for album in albums:
            for photo in album.photos:
                original = next((p for p in valid_inputs if p.filename == photo.filename), None)
                if original and os.path.exists(original.local_path):
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
        "temp_dir": TEMP_DIR,
        "processed_dir": PROCESSED_DIR 
    }

@app.delete("/cleanup")
async def cleanup_images():
    """Delete all processed images to free up space"""
    try:
        count = 0
        for filename in os.listdir(PROCESSED_DIR):
            file_path = os.path.join(PROCESSED_DIR, filename)
            if os.path.isfile(file_path) and filename.endswith('.jpg'):
                os.remove(file_path)
                count += 1
        return {"status": "success", "deleted": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)