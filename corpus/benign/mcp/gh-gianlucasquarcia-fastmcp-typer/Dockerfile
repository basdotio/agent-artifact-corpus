FROM python:3.12-slim

# Install uv (used for dependency management, matching the committed uv.lock)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Install dependencies first to leverage Docker layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev

# Copy the application source
COPY mcp_server.py mcp_server_cli.py mcp_server_tools.py mcp_server_resources.py mcp_server_prompts.py settings.py ./
COPY .env.template ./

ENV PATH="/app/.venv/bin:${PATH}" \
    MCP_SERVER_DEFAULT_TRANSPORT=streamable-http \
    MCP_SERVER_DEFAULT_PORT=8000 \
    FASTMCP_HOST=0.0.0.0

EXPOSE 8000

ENTRYPOINT ["python", "mcp_server_cli.py", "run"]

