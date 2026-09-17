---
name: docker
description: Docker containerization with best practices for builds, compose, and production deployment
category: devops
triggers:
  - docker
  - dockerfile
  - container
  - docker-compose
  - image
---

# Docker

Production-grade **Docker containerization** following industry best practices. This skill covers efficient Dockerfiles, multi-stage builds, compose configurations, and deployment patterns.

## Purpose

Build and deploy containerized applications:

- Create efficient Docker images
- Implement multi-stage builds
- Configure Docker Compose
- Handle secrets securely
- Optimize for production
- Implement health checks

## Features

### 1. Multi-Stage Builds

```dockerfile
# Node.js Application
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# Create non-root user
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nodeuser

COPY --from=deps --chown=nodeuser:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=nodeuser:nodejs /app/dist ./dist
COPY --from=builder --chown=nodeuser:nodejs /app/package.json ./

USER nodeuser
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

CMD ["node", "dist/index.js"]
```

```dockerfile
# Python Application
FROM python:3.12-slim AS builder
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runner
WORKDIR /app

# Copy virtual environment
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

COPY --chown=appuser:appuser . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```dockerfile
# Go Application
FROM golang:1.22-alpine AS builder
WORKDIR /app

# Download dependencies
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o /app/server ./cmd/server

FROM scratch
COPY --from=builder /app/server /server
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

EXPOSE 8080
ENTRYPOINT ["/server"]
```

### 2. Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      target: runner
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgres://postgres:password@db:5432/myapp
      - REDIS_URL=redis://redis:6379
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    restart: unless-stopped
    networks:
      - backend
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 128M

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - backend

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - backend

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - app
    restart: unless-stopped
    networks:
      - backend

networks:
  backend:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
```

### 3. Development vs Production

```yaml
# docker-compose.override.yml (development)
version: '3.8'

services:
  app:
    build:
      target: builder
    volumes:
      - .:/app
      - /app/node_modules
    environment:
      - NODE_ENV=development
    command: npm run dev

  db:
    ports:
      - "5432:5432"

  redis:
    ports:
      - "6379:6379"

  mailhog:
    image: mailhog/mailhog
    ports:
      - "1025:1025"
      - "8025:8025"
```

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  app:
    image: myregistry/myapp:${VERSION:-latest}
    environment:
      - NODE_ENV=production
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      rollback_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3

  db:
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets:
      - db_password

secrets:
  db_password:
    external: true
```

### 4. Best Practices Dockerfile

```dockerfile
# Use specific version tags
FROM node:20.10.0-alpine3.19

# Set working directory early
WORKDIR /app

# Add metadata labels
LABEL org.opencontainers.image.source="https://github.com/org/repo" \
      org.opencontainers.image.authors="team@example.com" \
      org.opencontainers.image.version="1.0.0"

# Install dependencies first (better caching)
COPY package*.json ./
RUN npm ci --only=production \
    && npm cache clean --force

# Copy source code
COPY . .

# Create non-root user
RUN addgroup --system --gid 1001 appgroup \
    && adduser --system --uid 1001 --ingroup appgroup appuser \
    && chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD node healthcheck.js

# Use exec form for CMD
CMD ["node", "dist/index.js"]
```

### 5. .dockerignore

```
# Dependencies
node_modules
.npm

# Build artifacts
dist
build
.next
out

# Development files
.git
.gitignore
*.md
docs

# IDE
.vscode
.idea
*.swp
*.swo

# Environment
.env
.env.*
!.env.example

# Testing
coverage
.nyc_output
*.test.js
*.spec.js
__tests__

# Docker
Dockerfile*
docker-compose*
.docker

# OS
.DS_Store
Thumbs.db
```

### 6. Security Scanning

```yaml
# GitHub Actions workflow
name: Docker Security

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build image
        run: docker build -t myapp:${{ github.sha }} .

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: myapp:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload scan results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
```

### 7. Registry and Deployment

```bash
# Build and push
docker build -t myregistry/myapp:1.0.0 .
docker push myregistry/myapp:1.0.0

# Multi-platform build
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t myregistry/myapp:1.0.0 \
  --push .

# Deploy with zero downtime
docker compose -f docker-compose.prod.yml up -d --no-deps --scale app=3 app
```

## Use Cases

### Microservices Setup
```yaml
services:
  api-gateway:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf

  user-service:
    build: ./services/user
    environment:
      - DB_HOST=user-db
    depends_on:
      - user-db

  order-service:
    build: ./services/order
    environment:
      - DB_HOST=order-db
      - KAFKA_BROKERS=kafka:9092
    depends_on:
      - order-db
      - kafka

  user-db:
    image: postgres:16-alpine

  order-db:
    image: postgres:16-alpine

  kafka:
    image: confluentinc/cp-kafka:latest
```

### CI/CD Pipeline
```yaml
build:
  stage: build
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA

deploy:
  stage: deploy
  script:
    - docker stack deploy -c docker-compose.prod.yml myapp
```

## Best Practices

### Do's
- Use specific base image tags
- Implement multi-stage builds
- Run as non-root user
- Add health checks
- Use .dockerignore
- Minimize layers
- Scan for vulnerabilities

### Don'ts
- Don't use latest tag
- Don't run as root
- Don't store secrets in images
- Don't include dev dependencies
- Don't ignore build cache
- Don't skip security scans

## References

- [Docker Documentation](https://docs.docker.com/)
- [Docker Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Docker Compose](https://docs.docker.com/compose/)
- [Container Security](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
