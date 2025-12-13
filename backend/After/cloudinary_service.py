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
            logger.error(f"❌ Upload Failed: {e}") 
            return None

    def create_album_zip_link(self, album_name: str) -> str:
        """
        Tạo Dynamic Link Download Zip (Hết hạn sau 1 giờ).
        Không tạo file lưu trữ trên Cloudinary.
        """
        safe_tag = "".join(c for c in album_name if c.isalnum())
        try:
            # Tính toán thời gian hết hạn (hiện tại + 3600 giây)
            expiration_time = int(time.time()) + 3600
            
            # Sử dụng utils.download_zip_url để tạo link dynamic
            url = cloudinary.utils.download_zip_url(
                tags=[safe_tag],
                resource_type="image",
                # Cấu hình Token Auth để giới hạn thời gian
                auth_token={
                    'key': CLOUDINARY_API_SECRET, # Dùng Secret Key để ký token
                    'start_time': int(time.time()), 
                    'expiration': expiration_time
                }
            )
            
            logger.info(f"✅ Generated Dynamic Zip Link for tag: {safe_tag}")
            return url
            
        except Exception as e:
            logger.error(f"❌ Zip Link Generation Failed: {e}")
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
    
    def get_public_id_from_url(self, url: str) -> str:
        """
        Input: https://res.cloudinary.com/.../upload/v1234/smart_albums/abc_123.jpg
        Output: smart_albums/abc_123
        """
        try:
            if "cloudinary" not in url:
                return None
            # Tách chuỗi để lấy phần sau 'upload/'
            parts = url.split("/upload/")
            if len(parts) < 2: 
                return None
            
            # Lấy phần sau version (v12345/...)
            path_part = parts[1]
            # Bỏ version nếu có (vd: v1710000/)
            if path_part.startswith("v"):
                path_part = path_part.split("/", 1)[1]
            
            # Bỏ đuôi file (.jpg, .png)
            public_id = path_part.rsplit(".", 1)[0]
            return public_id
        except Exception:
            return None

    # --- THÊM MỚI: Hàm xóa danh sách ảnh ---
    def delete_resources(self, public_ids: list):
        if not public_ids:
            return
        
        logger.info(f"🗑️ Đang xóa {len(public_ids)} ảnh trên Cloudinary...")
        self.executor.submit(cloudinary.api.delete_resources, public_ids)