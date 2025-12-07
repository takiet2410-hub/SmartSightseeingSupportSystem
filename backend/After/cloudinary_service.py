import cloudinary
import cloudinary.uploader
import cloudinary.api
from concurrent.futures import ThreadPoolExecutor
from config import CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
from logger_config import logger

# Cấu hình Global
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

class CloudinaryService:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4) # Upload song song 4 ảnh

    def upload_photo(self, file_path: str, album_name: str) -> str:
        """
        Upload 1 ảnh lên Cloudinary và gắn tag theo tên Album.
        Trả về: URL ảnh (HTTPS).
        """
        try:
            # Tạo tag an toàn (bỏ dấu cách, ký tự lạ) để dùng cho tính năng gom nhóm
            safe_tag = "".join(c for c in album_name if c.isalnum())
            
            # Upload
            response = cloudinary.uploader.upload(
                file_path,
                folder="smart_albums", # Thư mục trên Cloud
                tags=[safe_tag],       # Gắn thẻ để sau này tạo file Zip
                resource_type="image"
            )
            
            return response.get("secure_url")
        except Exception as e:
            logger.error(f"Cloudinary upload failed for {file_path}: {e}")
            return None

    def create_album_zip_link(self, album_name: str) -> str:
        """
        Tạo file ZIP lưu trữ vĩnh viễn trên Cloudinary (Static Archive).
        Link trả về sẽ KHÔNG bao giờ hết hạn.
        """
        # Tạo tag an toàn
        safe_tag = "".join(c for c in album_name if c.isalnum())
        
        try:
            # Sử dụng uploader.create_archive thay vì utils.download_zip_url
            response = cloudinary.uploader.create_archive(
                tags=[safe_tag],
                mode="create",  # <-- Quan trọng: Tạo file thật lưu trên cloud
                target_public_id=f"{safe_tag}_album_download", # Tên file trên cloud
                resource_type="image"
            )
            
            # Trả về đường dẫn vĩnh viễn (secure_url)
            return response.get("secure_url")
            
        except Exception as e:
            logger.error(f"Failed to create static zip: {e}")
            return None # Trả về None nếu lỗi
            
    def upload_batch(self, photos_with_album: list) -> dict:
        """
        Upload hàng loạt để tiết kiệm thời gian.
        Input: List of tuples (file_path, album_name)
        Output: Dict {file_path: cloud_url}
        """
        logger.info(f"☁️ Đang upload {len(photos_with_album)} ảnh lên Cloudinary...")
        
        results = {}
        # Chạy song song (Parallel)
        futures = []
        for path, alb_name in photos_with_album:
            futures.append(self.executor.submit(self.upload_photo, path, alb_name))
            
        for (path, _), future in zip(photos_with_album, futures):
            url = future.result()
            if url:
                results[path] = url
                
        return results