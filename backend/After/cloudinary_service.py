import os
import zipfile
import cloudinary
import cloudinary.uploader
import cloudinary.utils
from concurrent.futures import ThreadPoolExecutor
from config import CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET, TEMP_DIR
from logger_config import logger

# Cấu hình Global
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True
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

    def create_and_upload_zip(self, album_name: str, local_file_paths: list) -> str:
        if not local_file_paths: return None
            
        safe_name = "".join(c for c in album_name if c.isalnum())
        zip_filename = f"{safe_name}_{os.urandom(4).hex()}.zip"
        zip_path = os.path.join(TEMP_DIR, zip_filename)

        try:
            # 1. Nén file
            valid_files = [f for f in local_file_paths if os.path.exists(f)]
            if not valid_files: return None

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in valid_files:
                    zipf.write(file_path, arcname=os.path.basename(file_path))
            
            if os.path.getsize(zip_path) < 50: return None
            logger.info(f"⬆️ Uploading Zip ({os.path.getsize(zip_path)} bytes)...")

            # 2. Upload lên Cloudinary (RAW)
            # Dùng tên file zip làm public_id luôn để tránh nhầm lẫn
            public_id = f"smart_albums_archives/{safe_name}_archive_{os.urandom(4).hex()}.zip"
            
            response = cloudinary.uploader.upload(
                zip_path,
                resource_type="raw",     
                public_id=public_id, 
                unique_filename=False,
                overwrite=True
            )
            
            # 3. Tạo link tải xuống bằng SDK (Cách chuẩn nhất)
            # public_id đã có đuôi .zip, nên ta không cần format
            download_url, options = cloudinary.utils.cloudinary_url(
                response['public_id'],   
                resource_type="raw",
                flags="attachment" # Chỉ dùng flag đơn giản, không đổi tên file
            )
            
            # 4. Fallback (Dự phòng)
            # Nếu link trên vẫn lỗi, trả về link gốc (secure_url)
            # Người dùng vẫn tải được, chỉ là trình duyệt sẽ hỏi "Save as" hay không thôi
            logger.info(f"✅ Zip Link: {download_url}")
            
            # Kiểm tra nhanh: Nếu URL trông có vẻ sai (thiếu extension), trả về secure_url gốc
            if not download_url.endswith(".zip"):
                logger.warning("⚠️ URL generated thiếu đuôi zip, dùng link gốc.")
                return response['secure_url']

            return download_url

        except Exception as e:
            logger.error(f"❌ Lỗi tạo/upload Zip: {e}")
            return None
        finally:
            if os.path.exists(zip_path):
                try: os.remove(zip_path)
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