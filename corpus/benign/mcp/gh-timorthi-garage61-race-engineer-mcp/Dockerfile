FROM python:3.13-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files and install
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

# Copy source
COPY . .

EXPOSE 8000

CMD ["uv", "run", "fastmcp", "run", "main.py", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
