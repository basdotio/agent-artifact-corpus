# ビルドステージ
FROM node:20-slim AS builder

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# 実行ステージ
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
# package.jsonをコピーして"type": "module"設定を確実に継承
COPY --from=builder /app/package*.json ./

RUN chmod +x build/index.js && \
    mkdir -p /tmp/mcp-create-servers && \
    chmod 777 /tmp/mcp-create-servers

CMD ["node", "build/index.js"]