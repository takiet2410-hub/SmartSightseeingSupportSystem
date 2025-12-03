import os
import tempfile

# Temp directory for processing
TEMP_DIR = os.getenv("TEMP_DIR", os.path.join(tempfile.gettempdir(), "smart-album-uploads"))
os.makedirs(TEMP_DIR, exist_ok=True)

# Processed images directory (persisted for serving)
PROCESSED_DIR = os.getenv("PROCESSED_DIR", os.path.join(tempfile.gettempdir(), "smart-album-processed"))
os.makedirs(PROCESSED_DIR, exist_ok=True)