import os
import tempfile

# Docker Best Practice: allow overriding via ENV var, default to system temp
# This lets you map a Volume to /app/temp if you want to inspect files later
TEMP_DIR = os.getenv("TEMP_DIR", os.path.join(tempfile.gettempdir(), "smart-album-uploads"))

os.makedirs(TEMP_DIR, exist_ok=True)