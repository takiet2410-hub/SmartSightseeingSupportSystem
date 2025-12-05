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
        Tạo đường link tải xuống file ZIP chứa tất cả ảnh của Album đó.
        Cloudinary sẽ tự động gom các ảnh có cùng Tag và nén lại.
        """
        safe_tag = "".join(c for c in album_name if c.isalnum())
        
        try:
            # Tạo URL download zip dựa trên Tag
            download_url = cloudinary.utils.download_zip_url(
                tags=[safe_tag],
                target_public_id=f"{safe_tag}_album_download", # Tên file zip
                resource_type="image"
            )
            return download_url
        except Exception as e:
            logger.error(f"Failed to generate zip link: {e}")
            return ""
            
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