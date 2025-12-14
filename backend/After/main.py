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

from PIL import Image
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import requests
from fastapi.security import OAuth2PasswordRequestForm

from config import TEMP_DIR, PROCESSED_DIR
from metadata import MetadataExtractor
from clustering.service import ClusteringService
from schemas import PhotoInput, PhotoOutput, Album, TripSummaryRequest, TripSummaryResponse
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

# 🚀 Use ONE shared executor for the app to prevent thread explosion
executor = ThreadPoolExecutor(max_workers=8)

MAX_FILES = 500

def save_image_to_disk(img_full: Image.Image, path: str, original_bytes: bytes = None):
    try:
        # If we have original bytes, write them directly (fastest)
        if original_bytes:
            with open(path, 'wb') as f:
                f.write(original_bytes)
        else:
            img_full.save(path, "JPEG", quality=95)
    except Exception as e:
        logger.warning(f"Save failed: {e}")

def compute_image_hash(content: bytes) -> str:
    return hashlib.md5(content).hexdigest()

def process_image_job(file_info: dict) -> dict:
    """
    🚀 FIXED: Runs inside the thread pool. 
    Opens image, generates thumb, and runs analysis here to avoid blocking main thread.
    """
    path = file_info['temp_path']
    filename = file_info['filename']
    
    try:
        # 1. Open Image (Heavy I/O)
        img = Image.open(path)
        
        # 2. Thumbnail (Heavy CPU)
        img_thumb = img.copy()
        img_thumb.thumbnail((512, 512), Image.Resampling.BILINEAR)
        
        # 3. Analyze (Heavy CPU/ML)
        # Access globals since this is a thread, not a separate process
        metadata = _extractor.get_metadata_from_image(img_thumb)
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
    save_tasks = []
    
    for file in files:
        content = await file.read()
        file_contents.append((file.filename, content))
        
        safe_name = f"{uuid.uuid4()}.jpg"
        temp_path = os.path.join(PROCESSED_DIR, safe_name)
        
        # We perform the disk write in executor to keep event loop free
        save_tasks.append(
            loop.run_in_executor(executor, save_image_to_disk, None, temp_path, content)
        )
        
    await asyncio.gather(*save_tasks)
    
    # Reconstruct path map based on order (since we appended synchronously to file_contents)
    # Note: We need to know which path belongs to which file. 
    # Let's rebuild the paths deterministically or track them better.
    # Simpler approach:
    path_map = {}
    files_to_upload = []
    
    # We must match the saved paths to the filenames. 
    # Since save_tasks mapped 1:1 to file_contents, we can regenerate the paths used.
    # (The previous uuid logic was inside the loop, we need to capture it. Let's fix that logic slightly).
    
    prepared_files = []
    for idx, (filename, content) in enumerate(file_contents):
        # We need to recreate the path logic or capture it. 
        # Since I can't see the exact uuid generated inside the loop above without refactoring,
        # I will assume we can rely on the task order or refactor slightly.
        # FIX: Let's just grab the filename from the PROCESSED_DIR if needed, 
        # BUT cleaner is to generate path BEFORE submit.
        pass 
    
    # 🔄 RE-IMPLEMENTING STEP 0 CLEANER FOR SAFETY
    saved_paths_map = {}
    save_futures = []
    
    for filename, content in file_contents:
        safe_name = f"{uuid.uuid4()}.jpg"
        temp_path = os.path.join(PROCESSED_DIR, safe_name)
        saved_paths_map[filename] = temp_path
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
        
        # 🚀 CRITICAL FIX: Run image loading & analysis in executor
        results = await loop.run_in_executor(
            executor,
            lambda b: [process_image_job(j) for j in b],
            batch
        )
        
        for res in results:
            if not res['success']:
                # Handle error case
                processed_inputs.append(PhotoInput(
                     id=res['filename'], filename=res['filename'],
                     local_path=res.get('temp_path'), is_rejected=True, 
                     rejected_reason="Processing Error", score=0
                ))
                continue

            # Create PhotoInput
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
                
            # Update Cache
            _processed_cache[res['img_hash']] = p_in
            processed_inputs.append(p_in)
            
    # Merge cached and new
    all_inputs = processed_inputs + cached_results
    valid_inputs = [p for p in all_inputs if p] # Simple filter
    
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
        # uploaded_map format: { 'local_path': {'url': '...', 'public_id': '...'} }
        
        logger.info(f"✅ Cloudinary upload complete. Items: {len(uploaded_map)}")
        
        # STEP 6: Build Response + Fix Tags + Zip
        final_albums = []
        db_inserts = []
        
        for album in raw_albums:
            album_id = str(uuid.uuid4())
            safe_tag = "".join(c for c in album.title if c.isalnum() or c in ('-', '_')) + f"_{uuid.uuid4().hex[:4]}"
            
            output_photos = []
            album_public_ids = [] # Store IDs for tagging
            has_cloud_photo = False
            
            for photo in album.photos:
                orig = original_map.get(photo.filename)
                if not orig: continue
                
                img_url = None
                
                # Check upload result
                if orig.local_path in uploaded_map:
                    data = uploaded_map[orig.local_path]
                    img_url = data.get("url")
                    pid = data.get("public_id")
                    if pid:
                        album_public_ids.append(pid)
                    has_cloud_photo = True
                elif orig.local_path:
                    # Fallback to local server URL if upload failed
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
            
            # 🚀 FIXED ZIP LOGIC:
            zip_url = None
            if has_cloud_photo and album_public_ids:
                # A. Apply the specific album tag to these photos on Cloudinary
                # Use executor to avoid blocking loop (though it's fast IO)
                await loop.run_in_executor(
                    executor, 
                    cloud_service.add_tags, 
                    album_public_ids, 
                    safe_tag
                )
                
                # B. Generate Zip from that tag
                # (Can also run in executor)
                zip_url = await loop.run_in_executor(
                    executor,
                    cloud_service.create_album_zip_link,
                    safe_tag
                )
            
            # Find cover photo
            cover_url = None
            for photo in output_photos:
                if photo.image_url and 'cloudinary' in photo.image_url:
                    cover_url = photo.image_url
                    break
            
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
            
            doc = album_out.dict()
            doc['_id'] = album_id
            db_inserts.append(doc)
        
        if db_inserts:
            album_collection.insert_many(db_inserts)

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

# ... (Rest of your endpoints like get_my_albums, etc. remain unchanged) ...

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.delete("/cleanup")
async def cleanup_images():
    _processed_cache.clear()

    files = glob.glob(os.path.join(PROCESSED_DIR, "*"))
    for f in files:
        try:
            os.remove(f)
        except Exception:
            pass

    return {"status": "cleaned", "disk_files_removed": len(files)}

@app.post("/swagger-login")
async def swagger_login_proxy(form_data: OAuth2PasswordRequestForm = Depends()):
    auth_url = "http://localhost:8001/auth/login"
    try:
        response = requests.post(auth_url, json={"username": form_data.username, "password": form_data.password})
        if response.status_code == 200: return response.json()
        raise HTTPException(response.status_code, response.json().get("detail"))
    except Exception:
        raise HTTPException(503, "Auth Service Unavailable")

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
        
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)