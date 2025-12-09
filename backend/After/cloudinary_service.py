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
        self.executor = ThreadPoolExecutor(max_workers=4)

    def upload_photo(self, file_path: str, album_name: str) -> str:
        try:
            safe_tag = "".join(c for c in album_name if c.isalnum())
            response = cloudinary.uploader.upload(
                file_path,
                folder="smart_albums",
                tags=[safe_tag],
                resource_type="image"
            )
            return response.get("secure_url")
        except Exception as e:
            # [QUAN TRỌNG] In lỗi rõ ràng ra console để bạn biết tại sao fail
            logger.error(f"❌ Upload Failed: {e}") 
            return None

    def create_album_zip_link(self, album_name: str) -> str:
        safe_tag = "".join(c for c in album_name if c.isalnum())
        try:
            # Dùng mode="create" để tạo file zip vĩnh viễn
            response = cloudinary.uploader.create_archive(
                tags=[safe_tag],
                mode="create", 
                target_public_id=f"{safe_tag}_album_download",
                resource_type="image"
            )
            return response.get("secure_url")
        except Exception as e:
            logger.error(f"❌ Zip Failed: {e}")
            return None
            
    def upload_batch(self, photos_with_album: list) -> dict:
        logger.info(f"☁️ Đang upload {len(photos_with_album)} ảnh lên Cloudinary...")
        results = {}
        futures = []
        for path, alb_name in photos_with_album:
            futures.append(self.executor.submit(self.upload_photo, path, alb_name))
            
        for (path, _), future in zip(photos_with_album, futures):
            url = future.result()
            if url:
                results[path] = url
        
        logger.info(f"✅ Upload thành công: {len(results)}/{len(photos_with_album)} ảnh")
        return results