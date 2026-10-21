FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /build
COPY requirements.txt .
RUN uv pip install --system --no-cache --prefix=/install -r requirements.txt

FROM python:3.12-slim
COPY --from=builder /install /usr/local
RUN python -m compileall -q /usr/local/lib/python3.12
WORKDIR /app
COPY main.py server.py ./
RUN python -m compileall -q /app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
USER 1001
EXPOSE 8080
CMD ["python", "main.py"]
