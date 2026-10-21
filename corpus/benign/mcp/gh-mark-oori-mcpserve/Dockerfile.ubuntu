FROM ubuntu:24.04

# Install Python 3 and pip
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    git \
    tmux \
    jq \
    gh \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /mcp

# Set env variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip3 install --upgrade pip \
    && pip3 install uv \
    && uv pip install -v --system --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port the app runs on
EXPOSE 8005

# Run the application
CMD ["python3", "main.py"]