FROM python:3.12-slim

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create a non-root user
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Expose port for GraphQL API
EXPOSE 8000

# Default command (to be updated with actual app entrypoint)
CMD ["python", "main.py"]
