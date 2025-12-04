# Use lightweight Ubuntu image (CPU only)
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTORCH_ENABLE_MPS_FALLBACK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3-pip \
    build-essential \
    git \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.10 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Copy core folder (configuration and database setup)
COPY core/ core/

# Copy models folder (pre-trained model weights)
COPY models/ models/

# Copy main application files
COPY visual_search.py .
COPY ingest_image_data.py .

# Copy .env file (make sure it's available in the container)
# NOTE: Do NOT COPY the local `.env` into the image when deploying to
# hosted services (Hugging Face Spaces). Provide secrets / environment
# variables via the Spaces "Secrets" or repository settings instead.
# If you need a local .env for development, mount it at runtime or
# uncomment the following line for local builds only.
# COPY .env .

# Upgrade pip and install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Expose port for FastAPI
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Hugging Face Spaces BẮT BUỘC dùng port 7860
CMD ["uvicorn", "visual_search:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
