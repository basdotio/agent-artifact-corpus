FROM ghcr.io/astral-sh/uv:0.6.6-python3.12-bookworm

# Install Oracle Instant Client dependencies
RUN apt-get update && apt-get install -y \
    libaio1 \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Download and install Oracle Instant Client based on architecture
WORKDIR /opt/oracle

# Set up architecture-specific variables
ARG TARGETARCH
RUN if [ "$TARGETARCH" = "amd64" ]; then \
        ORACLE_CLIENT_URL="https://download.oracle.com/otn_software/linux/instantclient/2370000/instantclient-basic-linux.x64-23.7.0.25.01.zip"; \
    elif [ "$TARGETARCH" = "arm64" ]; then \
        ORACLE_CLIENT_URL="https://download.oracle.com/otn_software/linux/instantclient/2370000/instantclient-basic-linux.arm64-23.7.0.25.01.zip"; \
    else \
        echo "Unsupported architecture: $TARGETARCH" && exit 1; \
    fi && \
    echo "Downloading Oracle Instant Client 23.7 for $TARGETARCH" && \
    curl -o instantclient.zip $ORACLE_CLIENT_URL && \
    unzip instantclient.zip && \
    rm instantclient.zip && \
    cd instantclient* && \
    echo /opt/oracle/instantclient_23_7 > /etc/ld.so.conf.d/oracle-instantclient.conf && \
    ldconfig

# Set Oracle environment variables
ENV LD_LIBRARY_PATH=/opt/oracle/instantclient_23_7:$LD_LIBRARY_PATH
ENV ORACLE_HOME=/opt/oracle/instantclient_23_7
ENV DPI_DEBUG_LEVEL=64

# Copy the project into the image
ADD . /app

# Sync the project into a new environment, using the frozen lockfile
WORKDIR /app
RUN uv sync --frozen

# Set environment for MCP communication
ENV PYTHONUNBUFFERED=1

# Install package with UV (using --system flag)
RUN uv pip install --system -e .

CMD ["uv", "run", "main.py"]