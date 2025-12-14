import cloudinary
import cloudinary.uploader
import cloudinary.api
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
        # 🚀 OPTIMIZATION: Use 4-8 workers. 16 is too many for Python's GIL + Image processing.
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
            return {
                "url": response.get("secure_url"),
                "public_id": response.get("public_id")
            }
        except Exception as e:
            logger.error(f"❌ Upload Failed for {file_path}: {e}") 
            return None

    def add_tags(self, public_ids: list, new_tag: str):
        """
        🚀 NEW: Assign the specific album tag to a list of photos
        so the Zip file generation works correctly.
        """
        try:
            if not public_ids:
                return
            # Cloudinary allows updating tags for multiple IDs at once
            cloudinary.uploader.add_tag(new_tag, public_ids)
            logger.info(f"🏷️ Added tag '{new_tag}' to {len(public_ids)} photos")
        except Exception as e:
            logger.error(f"❌ Failed to add tags: {e}")

    def create_album_zip_link(self, album_tag: str) -> str:
        try:
            logger.info(f"📦 Generating zip for tag: {album_tag}")
            response = cloudinary.uploader.create_archive(
                tags=[album_tag],
                mode="create", 
                target_public_id=f"{album_tag}_download",
                resource_type="image"
            )
            return response.get("secure_url")
        except Exception as e:
            logger.error(f"❌ Zip Failed: {e}")
            return None
            
    def upload_batch(self, photos_with_tags: list) -> dict:
        """
        Uploads photos in parallel and returns a map of local_path -> {url, public_id}
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
            data = future.result() # Wait for result
            if data:
                results[path] = data # Store the whole dict (url + public_id)
            completed += 1
            
            if completed % max(1, total // 5) == 0:
                logger.info(f"📤 Upload progress: {completed}/{total}")
        
        return results