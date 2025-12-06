# 1. Sử dụng Python 3.10 slim
FROM python:3.10-slim

# 2. Thiết lập biến môi trường
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# 3. Tạo thư mục làm việc
WORKDIR /app

# 4. Cài đặt thư viện hệ thống (Sửa lỗi libgl1)
RUN apt-get update && apt-get install -y \
    git \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 5. Tạo user 'user' (UID 1000) - Bắt buộc cho HF Spaces
RUN useradd -m -u 1000 user

# 6. Copy requirements.txt (nằm ngay cạnh Dockerfile)
COPY --chown=user requirements.txt .

# 7. Cài đặt dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 8. Copy TOÀN BỘ file trong thư mục hiện tại vào container
# (Bao gồm main.py, folder core, folder models...)
COPY --chown=user . .

# 9. Chuyển quyền sang user thường
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# 10. Mở port 7860
EXPOSE 7860

# 11. Chạy server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]