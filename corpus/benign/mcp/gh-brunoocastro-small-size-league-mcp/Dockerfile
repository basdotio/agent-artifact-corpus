# Python 3.12 image with uv
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy
ENV PORT=8888

LABEL org.opencontainers.image.source=https://github.com/brunoocastro/small-size-league-mcp
LABEL org.opencontainers.image.description="Small Size League MCP - A MCP Server for SSL Knowledge Base"
LABEL org.opencontainers.image.licenses=MIT

# Set work directory
WORKDIR /app

# Copy project files
COPY . .

# Sync the project into a new environment, asserting the lockfile is up to date
RUN uv sync --locked

EXPOSE 8888

# Start the application
ENTRYPOINT ["uv", "run", "mcp_server.py"] 