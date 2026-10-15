FROM python:3.10-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download Spacy model
RUN python -m spacy download ru_core_news_lg

# Copy code
COPY . .

# Expose HTTP port
EXPOSE 8000

# Default command: Run HTTP API
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
