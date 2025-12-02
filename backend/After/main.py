import os
import warnings

# Suppress all warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # TensorFlow warnings
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'  # Hugging Face warnings
warnings.filterwarnings('ignore')  # Python warnings

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

from config import TEMP_DIR
from metadata import MetadataExtractor
from clustering.service import ClusteringService, get_model as get_clip_model
from schemas import PhotoInput
from filters.lighting import LightingFilter
from filters.junk_detector import is_junk, get_model as get_junk_model
from logger_config import logger
from curation_service import CurationService

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Pre-warm models at startup to avoid lazy loading race conditions.
    """
    logger.info("Starting application...")
    
    # Pre-load heavy models
    logger.info("Pre-warming ML models...")
    
    # Load in thread pool to avoid blocking startup
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=2)
    
    async def load_models():
        await asyncio.gather(
            loop.run_in_executor(executor, get_junk_model),
            loop.run_in_executor(executor, get_clip_model)
        )
    
    await load_models()
    logger.info("Models loaded and ready")
    
    yield  # Application runs here
    
    # Shutdown
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

# Thread pool for CPU-bound operations
executor = ThreadPoolExecutor(max_workers=4)

# Concurrency limiter
MAX_CONCURRENT = 10
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

# Input limits
MAX_FILES = 500
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def save_image_to_disk(img: Image.Image, path: str):
    """
    Helper: Saves an open PIL image to disk as JPG.
    """
    try:
        # Preserve EXIF if available
        # Check if 'info' exists (it should on a PIL Image)
        if hasattr(img, 'info'):
            exif_bytes = img.info.get("exif")
            if exif_bytes:
                img.save(path, "JPEG", quality=80, exif=exif_bytes)
                return

        # Fallback save
        img.save(path, "JPEG", quality=80)
            
    except Exception as e:
        logger.warning(f"Save failed: {e}")

async def process_single_photo(
    file: UploadFile,
    extractor: MetadataExtractor,
    lighting_filter: LightingFilter,
    curator: CurationService
) -> PhotoInput:
    """
    Process one photo with rate limiting & auto-conversion.
    """
    async with semaphore:
        # 1. FORCE .jpg extension
        safe_name = f"{uuid.uuid4()}.jpg"
        temp_path = os.path.join(TEMP_DIR, safe_name)
        
        try:
            # 2. Read file content into RAM (Async I/O)
            content = await file.read()
            
            # 3. Convert & Save in Thread Pool (CPU Bound task)
            # This prevents the "HEIC Lag" from blocking other users
            loop = asyncio.get_event_loop()

            def open_image(b):
                i = Image.open(io.BytesIO(b))
                i.load()
                return i.convert("RGB")
            
            img = await loop.run_in_executor(executor, open_image, content)

            await loop.run_in_executor(
                executor,
                save_image_to_disk, # Calls our helper
                img,
                temp_path
            )
            
            # --- The rest of your logic remains exactly the same ---
            
            # Lighting check
            is_good_light, light_reason = await loop.run_in_executor(
                executor,
                lighting_filter.analyze,
                temp_path
            )
            
            if not is_good_light:
                logger.info(f"{file.filename}: {light_reason}")
                return PhotoInput(
                    id=file.filename,
                    filename=file.filename,
                    local_path=temp_path,
                    is_rejected=True,
                    rejected_reason=light_reason
                )
            
            # Junk check
            is_junk_photo = await loop.run_in_executor(
                executor,
                is_junk,
                temp_path
            )
            
            if is_junk_photo:
                logger.info(f"{file.filename}: Junk detected")
                return PhotoInput(
                    id=file.filename,
                    filename=file.filename,
                    local_path=temp_path,
                    is_rejected=True,
                    rejected_reason="AI Detected Junk"
                )
            
            # Calculate aesthetic score
            score = await loop.run_in_executor(
                executor,
                curator.calculate_score,
                img
            )
            
            # Extract metadata
            meta = await loop.run_in_executor(
                executor,
                extractor.get_metadata,
                temp_path
            )
            
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
    """
    Create photo albums with async parallel processing.
    """
    # Validation
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=413,
            detail=f"Too many files. Maximum: {MAX_FILES}"
        )
    
    for file in files:
        if file.size and file.size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"{file.filename} exceeds 50MB limit"
            )
    
    logger.info(f"Processing {len(files)} photos...")
    
    extractor = MetadataExtractor()
    lighting_filter = LightingFilter()
    curator = CurationService()
    
    # Process all files in parallel
    tasks = [
        process_single_photo(file, extractor, lighting_filter, curator)
        for file in files
    ]
    
    # Gather with exception handling
    photo_inputs = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out exceptions
    valid_inputs = []
    for i, result in enumerate(photo_inputs):
        if isinstance(result, Exception):
            logger.error(f"Task {i} failed: {result}")
        else:
            valid_inputs.append(result)
    
    if not valid_inputs:
        raise HTTPException(
            status_code=500,
            detail="All photos failed to process"
        )
    
    # Extract paths for cleanup
    paths_to_clean = [p.local_path for p in valid_inputs]
    
    try:
        # Run clustering
        albums = ClusteringService.dispatch(valid_inputs)
        
        logger.info(f"Created {len(albums)} albums")
        return {"albums": albums}
    
    finally:
        # Cleanup
        for p in paths_to_clean:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception as e:
                    logger.warning(f"Cleanup failed for {p}: {e}")


@app.get("/health")
async def health_check():
    """Health check with system info."""
    return {
        "status": "healthy",
        "max_concurrent": MAX_CONCURRENT,
        "max_files": MAX_FILES,
        "max_file_size_mb": MAX_FILE_SIZE / 1024 / 1024,
        "temp_dir": TEMP_DIR
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)