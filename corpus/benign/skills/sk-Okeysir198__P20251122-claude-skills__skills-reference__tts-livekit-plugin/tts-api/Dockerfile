FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Expose port
EXPOSE 8001

# Environment variables
ENV TTS_MODEL_TYPE=parler
ENV TTS_MODEL_NAME=parler-tts/parler-tts-mini-v1
ENV TTS_DEVICE=cpu

# Run the application
CMD ["python", "main.py"]
