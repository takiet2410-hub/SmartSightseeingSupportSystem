FROM python:3.10

WORKDIR /code

# Copy only requirements first to leverage Docker layer cache
COPY ./requirements.txt /code/requirements.txt

# Upgrade pip then install dependencies
RUN python -m pip install --no-cache-dir --upgrade pip && \
	pip install --no-cache-dir -r /code/requirements.txt

# Copy application code (a .dockerignore is recommended to avoid including secrets)
COPY . /code

# Create a non-root user for running the service
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
	PATH=/home/user/.local/bin:$PATH

# Use the PORT environment variable provided by hosting (Hugging Face Spaces)
# Fallback to 8000 locally if PORT is not set
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]