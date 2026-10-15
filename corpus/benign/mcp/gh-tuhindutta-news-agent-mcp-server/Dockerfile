# Use a lightweight Python base image
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Install dependencies from requirements.txt
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

# CRITICAL: Ensure Python stdout/stderr is unbuffered for stdio transport
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
# Command to run the MCP server when the container starts
