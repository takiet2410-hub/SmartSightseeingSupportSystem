FROM python:3.10

# 1. Tạo user trước để tránh lỗi permission sau này
RUN useradd -m -u 1000 user

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN python -m pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /code/requirements.txt

# 2. Quan trọng: Copy code và chuyển quyền sở hữu cho 'user' luôn
# Nếu không có --chown=user, file sẽ thuộc về root và user thường không đọc/ghi được
COPY --chown=user . /code

USER user

# Thiết lập biến môi trường cần thiết
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# 3. QUAN TRỌNG NHẤT: Hugging Face Spaces BẮT BUỘC chạy ở port 7860
# Bạn phải set cứng port 7860 thì nó mới chuyển sang trạng thái "Running"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]