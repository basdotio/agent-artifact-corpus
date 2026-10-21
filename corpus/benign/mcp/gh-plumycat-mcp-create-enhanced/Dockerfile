# Build stage
FROM node:20-slim AS builder

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Runtime stage
FROM node:20-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3-minimal \
    python3-pip \
    curl \
    which && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    npm install -g ts-node typescript

ENV PATH="/usr/local/bin:/usr/bin:/bin:${PATH}"
ENV NODE_PATH="/app/node_modules"
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY --from=builder /app/build ./build
COPY --from=builder /app/node_modules ./node_modules
# Copy package.json to ensure "type": "module" configuration is inherited
COPY --from=builder /app/package*.json ./

RUN chmod +x build/index.js && \
    mkdir -p /tmp/mcp-create-servers && \
    mkdir -p /app/data/servers && \
    chmod 777 /tmp/mcp-create-servers && \
    chmod 755 /app/data

# Configure proper signal handling for graceful shutdown
STOPSIGNAL SIGTERM

# Create volume mount point for persistent data
VOLUME ["/app/data"]

CMD ["node", "build/index.js"]