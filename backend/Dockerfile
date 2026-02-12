# Backend Dockerfile
FROM python:3.11-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System dependencies: ffmpeg for pydub, espeak-ng for pyttsx3 fallback
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt /app/requirements.txt

# Stage 1: Core application dependencies
# We install pytorch cpu version first to keep image size small
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu --prefer-binary \
    "torch==2.1.2" "torchvision==0.16.2"

# Install remaining dependencies from requirements.txt
# Upgrade pip first
RUN pip install --no-cache-dir --upgrade pip

# Install requirements
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend source
COPY backend /app

ENV HOST=0.0.0.0 \
    PORT=8000 \
    LOG_LEVEL=INFO

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
