import os
import tempfile
from dotenv import load_dotenv

load_dotenv()

# Temp directory for processing
TEMP_DIR = os.getenv("TEMP_DIR", os.path.join(tempfile.gettempdir(), "smart-album-uploads"))
os.makedirs(TEMP_DIR, exist_ok=True)

# Processed images directory (persisted for serving)
PROCESSED_DIR = os.getenv("PROCESSED_DIR", os.path.join(tempfile.gettempdir(), "smart-album-processed"))
os.makedirs(PROCESSED_DIR, exist_ok=True)

GOONG_API_KEY = os.getenv("GOONG_API_KEY")

CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")