FROM python:3.11-slim AS builder

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py ./

FROM python:3.11-slim AS release

WORKDIR /app

# Copy installed packages and application from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app .

ENV PYTHONPATH=/app
ENV PORT=3000

EXPOSE 3000

CMD ["python", "main.py"]
