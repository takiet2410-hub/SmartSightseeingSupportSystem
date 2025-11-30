import os
import tempfile

# 1. Get the system's default temporary directory
# Windows: C:\Users\Name\AppData\Local\Temp
# Mac/Linux/Vercel: /tmp
SYSTEM_TEMP = tempfile.gettempdir()

# 2. Create a subfolder for your app to keep things organized
TEMP_DIR = os.path.join(SYSTEM_TEMP, "smart-album-uploads")

# 3. Ensure it exists
os.makedirs(TEMP_DIR, exist_ok=True)