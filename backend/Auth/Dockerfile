FROM python:3.10

# 1. Create a non-root user early to use with --chown
RUN useradd -m -u 1000 user

WORKDIR /code

# 2. Copy only requirements first to leverage Docker layer cache
COPY ./requirements.txt /code/requirements.txt

# 3. Upgrade pip then install dependencies
RUN python -m pip install --no-cache-dir --upgrade pip && \
	pip install --no-cache-dir -r /code/requirements.txt

# 4. Copy application code and set ownership to 'user' for security/permissions
# A .dockerignore is recommended to exclude unnecessary files (like .git, secrets)
COPY --chown=user . /code

# 5. Switch to the non-root user
USER user

# 6. Set environment variables
ENV HOME=/home/user \
	PATH=/home/user/.local/bin:$PATH

# 7. IMPORTANT: Use port 7860 for Hugging Face Spaces
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]