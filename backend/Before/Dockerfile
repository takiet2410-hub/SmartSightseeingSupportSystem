# 1. Chọn hệ điều hành Python 3.10
FROM python:3.10

# 2. Tạo thư mục làm việc trong server ảo
WORKDIR /code

# 3. Copy file requirements và cài đặt thư viện
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 4. Copy toàn bộ code dự án vào server
COPY . /code

# 5. Cấp quyền ghi cho thư mục (để tránh lỗi permission)
RUN chmod 777 /code

# 6. Lệnh khởi động Server (Lưu ý: HF bắt buộc chạy port 7860)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]