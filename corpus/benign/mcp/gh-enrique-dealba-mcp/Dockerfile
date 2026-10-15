FROM vllm/vllm-openai

# Install system dependencies, including curl for the uv installer
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh -o /tmp/install-uv.sh \
    && chmod +x /tmp/install-uv.sh \
    && /tmp/install-uv.sh -y \
    && mv /root/.cargo/bin/uv /usr/local/bin/uv \
    && rm /tmp/install-uv.sh \
    && rmdir -p /root/.cargo/bin > /dev/null 2>&1 || true \
    && rmdir /root/.cargo > /dev/null 2>&1 || true

WORKDIR /app

COPY . .

RUN uv pip install --system -r requirements.txt \
    pytest \
    pytest-cov \
    jupyterlab \
    notebook \
    fastmcp

EXPOSE 8888
# For MCP server.py
EXPOSE 8000

# Clear any entrypoint inherited from the base image
ENTRYPOINT []


CMD ["sh", "-c", "uv run --with fastmcp server.py --server_type=sse & \
     jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token=''"]