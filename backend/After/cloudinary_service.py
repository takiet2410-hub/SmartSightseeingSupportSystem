import time
import cloudinary
import cloudinary.uploader
import cloudinary.api
import cloudinary.utils
from concurrent.futures import ThreadPoolExecutor
from config import CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
from logger_config import logger

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

class CloudinaryService:
    def __init__(self):
        # 🚀 YOURS: Use 8 workers (Stable)
        self.executor = ThreadPoolExecutor(max_workers=8)

    def upload_photo(self, file_path: str, temp_tag: str) -> dict:
        try:
            # Upload with the temporary tag first
            response = cloudinary.uploader.upload(
                file_path,
                folder="smart_albums",
                tags=[temp_tag],
                resource_type="image"
            )
            # 🚀 YOURS: Return public_id (Critical for tagging)
            return {
                "url": response.get("secure_url"),
                "public_id": response.get("public_id")
            }
        except Exception as e:
            logger.error(f"❌ Upload Failed for {file_path}: {e}") 
            return None

    def add_tags(self, public_ids: list, new_tag: str):
        """
        🚀 YOURS: Apply the tag so the Zip finds the photos
        """
        try:
            if not public_ids:
                return
            cloudinary.uploader.add_tag(new_tag, public_ids)
            logger.info(f"🏷️ Added tag '{new_tag}' to {len(public_ids)} photos")
        except Exception as e:
            logger.error(f"❌ Failed to add tags: {e}")

    def create_album_zip_link(self, album_tag: str) -> str:
        """
        ✅ HIS FEATURE (RESTORED): Dynamic Link Generation
        Changed input from 'album_name' to 'album_tag' so it matches the UUID tag we created.
        """
        try:
            # Expiration: Now + 1 hour
            expiration_time = int(time.time()) + 3600
            
            # Generate Dynamic URL (No storage used!)
            url = cloudinary.utils.download_zip_url(
                tags=[album_tag],
                resource_type="image",
                auth_token={
                    'key': CLOUDINARY_API_SECRET,
                    'start_time': int(time.time()), 
                    'expiration': expiration_time
                }
            )
            
            logger.info(f"✅ Generated Dynamic Zip Link for tag: {album_tag}")
            return url
            
        except Exception as e:
            logger.error(f"❌ Zip Link Generation Failed: {e}")
            return None
            
    def upload_batch(self, photos_with_tags: list) -> dict:
        """
        🚀 YOURS: Parallel upload returning public_ids
        """
        total = len(photos_with_tags)
        logger.info(f"☁️ Uploading {total} photos to Cloudinary...")
        
        results = {}
        futures = []
        
        for path, tag in photos_with_tags:
            future = self.executor.submit(self.upload_photo, path, tag)
            futures.append((future, path))
        
        completed = 0
        for future, path in futures:
            data = future.result()
            if data:
                results[path] = data
            completed += 1
            
            if completed % max(1, total // 5) == 0:
                logger.info(f"📤 Upload progress: {completed}/{total}")
        
        return results

    # 🔽 HIS HELPER METHODS (KEPT) 🔽
    
    def get_public_id_from_url(self, url: str) -> str:
        try:
            if "cloudinary" not in url: return None
            parts = url.split("/upload/")
            if len(parts) < 2: return None
            path_part = parts[1]
            if path_part.startswith("v"):
                path_part = path_part.split("/", 1)[1]
            return path_part.rsplit(".", 1)[0]
        except Exception:
            return None

    def delete_resources(self, public_ids: list):
        if not public_ids: return
        self.executor.submit(cloudinary.api.delete_resources, public_ids)