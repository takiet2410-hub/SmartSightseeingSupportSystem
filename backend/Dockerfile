# 1. Chọn Python 3.10 (Tương thích tốt nhất với TF/OpenCV)
FROM python:3.10-slim

# 2. Cài đặt thư viện hệ thống cho OpenCV (Quan trọng!)
# libgl1-mesa-glx & libglib2.0-0 bắt buộc để cv2 chạy trên Linux
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 3. Thiết lập thư mục làm việc
WORKDIR /app

# 4. Copy file requirements và cài đặt thư viện Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy toàn bộ code và model vào container
COPY . .

# 6. Mở cổng 8000
EXPOSE 8000

# 7. Lệnh chạy server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]