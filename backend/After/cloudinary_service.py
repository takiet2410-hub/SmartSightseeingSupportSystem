import os
import zipfile
import cloudinary
import cloudinary.uploader
import cloudinary.api
from concurrent.futures import ThreadPoolExecutor
# Import thêm TEMP_DIR để lưu file zip tạm
from config import CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET, TEMP_DIR
from logger_config import logger

# Cấu hình Global
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
            logger.error(f"❌ Upload Photo Failed: {e}")
            return None

    # [HÀM MỚI QUAN TRỌNG] Nén Local -> Upload Raw
    def create_and_upload_zip(self, album_name: str, local_file_paths: list) -> str:
        """
        Nén file tại server rồi upload lên Cloudinary dạng RAW.
        Khắc phục lỗi NULL và lỗi giới hạn 10MB.
        """
        if not local_file_paths:
            return None
            
        safe_name = "".join(c for c in album_name if c.isalnum())
        # Tạo tên file zip ngẫu nhiên để không trùng
        zip_filename = f"{safe_name}_{os.urandom(4).hex()}.zip"
        zip_path = os.path.join(TEMP_DIR, zip_filename)

        try:
            logger.info(f"📦 Đang nén {len(local_file_paths)} ảnh thành {zip_filename}...")
            
            # 1. Nén file tại Local (Server)
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in local_file_paths:
                    if os.path.exists(file_path):
                        # arcname: chỉ lấy tên file, không lấy đường dẫn thư mục dài dòng
                        zipf.write(file_path, arcname=os.path.basename(file_path))
            
            # 2. Upload file Zip lên Cloudinary (Dạng RAW)
            logger.info(f"⬆️ Đang upload Zip lên Cloudinary...")
            response = cloudinary.uploader.upload(
                zip_path,
                folder="smart_albums_archives", # Thư mục riêng cho zip
                resource_type="raw",            # [QUAN TRỌNG] Upload dạng file thô
                public_id=f"{safe_name}_archive_{os.urandom(4).hex()}"
            )
            
            final_url = response.get("secure_url")
            logger.info(f"✅ Zip Link vĩnh viễn: {final_url}")
            return final_url

        except Exception as e:
            logger.error(f"❌ Lỗi tạo/upload Zip: {e}")
            return None
        finally:
            # 3. Dọn dẹp file zip tạm trên server để tiết kiệm ổ cứng
            if os.path.exists(zip_path):
                try:
                    os.remove(zip_path)
                except: pass

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