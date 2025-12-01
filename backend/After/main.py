import os
import shutil
import uuid
from typing import List

import uvicorn
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from config import TEMP_DIR
from metadata import MetadataExtractor
from clustering.service import ClusteringService
from schemas import PhotoInput

app = FastAPI()

# CORS: Allow Frontend Access
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.post("/create-album")
async def create_album(files: List[UploadFile] = File(...)):
    """
    1. Uploads files to /tmp.
    2. Extracts Metadata & Runs Clustering.
    3. Deletes files immediately (Stateless).
    """

    extractor = MetadataExtractor()
    photo_inputs = []
    
    # Track paths to delete them in 'finally' block
    paths_to_clean = []

    try:
        for file in files:
            # 1. Create Unique Temp Path
            # We preserve the extension so Pillow can identify the format
            ext = file.filename.split('.')[-1] if '.' in file.filename else "jpg"
            safe_name = f"{uuid.uuid4()}.{ext}"
            temp_path = os.path.join(TEMP_DIR, safe_name)
            
            paths_to_clean.append(temp_path)
            
            # 2. Stream to Disk (Buffers RAM)
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # 3. Extract Metadata
            meta = extractor.get_metadata(temp_path)
            
            photo_inputs.append(PhotoInput(
                id=file.filename, # Key for frontend mapping
                filename=file.filename,
                local_path=temp_path, # Passed to CLIP if needed
                **meta
            ))
            
        # 4. Run The Clustering
        albums = ClusteringService.dispatch(photo_inputs)
        
        return {"albums": albums}

    finally:
        # 5. CLEANUP
        for p in paths_to_clean:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except: pass

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)