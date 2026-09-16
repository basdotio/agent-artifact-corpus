# Deployment Guide for Self-Hosted TTS API and LiveKit Plugin

## Overview

This guide covers deploying the self-hosted TTS API and integrating it with LiveKit voice agents in production.

---

## Architecture Options

### Option 1: All-in-One (Development)

```
┌─────────────────────────────┐
│   Single Server/Container   │
│  ┌──────────────────────┐   │
│  │   TTS API (8001)     │   │
│  └──────────────────────┘   │
│  ┌──────────────────────┐   │
│  │   LiveKit Agent      │   │
│  └──────────────────────┘   │
└─────────────────────────────┘
```

**Pros:** Simple setup, easy debugging
**Cons:** Not scalable, single point of failure

---

### Option 2: Separated Services (Recommended)

```
┌──────────────────┐     ┌──────────────────┐
│  TTS API Server  │◄────│  LiveKit Agent   │
│  (Port 8001)     │     │  (Multiple)      │
└──────────────────┘     └──────────────────┘
        ▲
        │
  ┌─────┴──────┐
  │   Load     │
  │  Balancer  │
  └────────────┘
```

**Pros:** Scalable, independent scaling, fault-tolerant
**Cons:** More complex setup

---

### Option 3: Cloud-Native (Production)

```
┌─────────────────────────────────────────┐
│           Kubernetes Cluster            │
│  ┌──────────────┐  ┌─────────────────┐ │
│  │  TTS API     │  │  LiveKit Agent  │ │
│  │  Deployment  │  │  Deployment     │ │
│  │  (Replicas)  │  │  (Replicas)     │ │
│  └──────────────┘  └─────────────────┘ │
│         ▲                               │
│         │                               │
│  ┌──────┴──────┐                       │
│  │   Service   │                       │
│  └─────────────┘                       │
└─────────────────────────────────────────┘
```

**Pros:** Highly scalable, auto-scaling, resilient
**Cons:** Complex setup, higher operational cost

---

## Deployment Method 1: Docker Compose

### Directory Structure

```
deployment/
├── docker-compose.yml
├── tts-api/
│   ├── Dockerfile
│   ├── main.py
│   ├── requirements.txt
│   └── .env
└── livekit-agent/
    ├── Dockerfile
    ├── agent.py
    ├── requirements.txt
    └── .env
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  tts-api:
    build: ./tts-api
    container_name: tts-api
    ports:
      - "8001:8001"
    environment:
      - TTS_MODEL_TYPE=parler
      - TTS_MODEL_NAME=parler-tts/parler-tts-mini-v1
      - TTS_DEVICE=cuda
    volumes:
      - tts-models:/root/.cache/huggingface
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  livekit-agent:
    build: ./livekit-agent
    container_name: livekit-agent
    depends_on:
      - tts-api
    environment:
      - LIVEKIT_URL=${LIVEKIT_URL}
      - LIVEKIT_API_KEY=${LIVEKIT_API_KEY}
      - LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET}
      - TTS_API_URL=http://tts-api:8001
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DEEPGRAM_API_KEY=${DEEPGRAM_API_KEY}
    restart: unless-stopped

volumes:
  tts-models:
```

### TTS API Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

# Run
CMD ["python", "main.py"]
```

### LiveKit Agent Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy plugin and agent code
COPY livekit-plugin-custom-tts/ ./livekit-plugin-custom-tts/
COPY agent.py .

# Install custom TTS plugin
RUN pip install -e ./livekit-plugin-custom-tts/

# Run agent
CMD ["python", "agent.py", "start"]
```

### Deployment

```bash
# Set environment variables
export LIVEKIT_URL="wss://your-livekit.cloud"
export LIVEKIT_API_KEY="your-api-key"
export LIVEKIT_API_SECRET="your-api-secret"
export OPENAI_API_KEY="your-openai-key"
export DEEPGRAM_API_KEY="your-deepgram-key"

# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## Deployment Method 2: Kubernetes

### TTS API Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tts-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: tts-api
  template:
    metadata:
      labels:
        app: tts-api
    spec:
      containers:
      - name: tts-api
        image: your-registry/tts-api:latest
        ports:
        - containerPort: 8001
        env:
        - name: TTS_MODEL_TYPE
          value: "parler"
        - name: TTS_MODEL_NAME
          value: "parler-tts/parler-tts-mini-v1"
        - name: TTS_DEVICE
          value: "cuda"
        resources:
          limits:
            nvidia.com/gpu: 1
            memory: "8Gi"
            cpu: "4"
          requests:
            nvidia.com/gpu: 1
            memory: "4Gi"
            cpu: "2"
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10
        volumeMounts:
        - name: model-cache
          mountPath: /root/.cache/huggingface
      volumes:
      - name: model-cache
        persistentVolumeClaim:
          claimName: tts-model-cache

---
apiVersion: v1
kind: Service
metadata:
  name: tts-api-service
spec:
  selector:
    app: tts-api
  ports:
  - protocol: TCP
    port: 8001
    targetPort: 8001
  type: ClusterIP

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: tts-model-cache
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

### LiveKit Agent Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: livekit-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: livekit-agent
  template:
    metadata:
      labels:
        app: livekit-agent
    spec:
      containers:
      - name: agent
        image: your-registry/livekit-agent:latest
        env:
        - name: LIVEKIT_URL
          valueFrom:
            secretKeyRef:
              name: livekit-secrets
              key: url
        - name: LIVEKIT_API_KEY
          valueFrom:
            secretKeyRef:
              name: livekit-secrets
              key: api-key
        - name: LIVEKIT_API_SECRET
          valueFrom:
            secretKeyRef:
              name: livekit-secrets
              key: api-secret
        - name: TTS_API_URL
          value: "http://tts-api-service:8001"
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: ai-secrets
              key: openai-key
        - name: DEEPGRAM_API_KEY
          valueFrom:
            secretKeyRef:
              name: ai-secrets
              key: deepgram-key
        resources:
          limits:
            memory: "2Gi"
            cpu: "2"
          requests:
            memory: "1Gi"
            cpu: "1"

---
apiVersion: v1
kind: Secret
metadata:
  name: livekit-secrets
type: Opaque
data:
  url: <base64-encoded-url>
  api-key: <base64-encoded-key>
  api-secret: <base64-encoded-secret>
```

### Deployment

```bash
# Create secrets
kubectl create secret generic livekit-secrets \
  --from-literal=url='wss://your-livekit.cloud' \
  --from-literal=api-key='your-api-key' \
  --from-literal=api-secret='your-api-secret'

kubectl create secret generic ai-secrets \
  --from-literal=openai-key='your-openai-key' \
  --from-literal=deepgram-key='your-deepgram-key'

# Deploy
kubectl apply -f tts-api-deployment.yaml
kubectl apply -f livekit-agent-deployment.yaml

# Check status
kubectl get pods
kubectl logs -f deployment/tts-api
kubectl logs -f deployment/livekit-agent
```

---

## Scaling Strategies

### Horizontal Pod Autoscaling (Kubernetes)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: tts-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: tts-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Load Balancing

For high-traffic scenarios, use a load balancer in front of TTS API:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: tts-api-lb
spec:
  type: LoadBalancer
  selector:
    app: tts-api
  ports:
  - protocol: TCP
    port: 8001
    targetPort: 8001
```

---

## Monitoring and Observability

### Prometheus Metrics

Add metrics to TTS API:

```python
from prometheus_client import Counter, Histogram, generate_latest

synthesis_requests = Counter('tts_requests_total', 'Total TTS requests')
synthesis_latency = Histogram('tts_latency_seconds', 'TTS latency')
synthesis_errors = Counter('tts_errors_total', 'Total TTS errors')

@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )
```

### Grafana Dashboard

Monitor key metrics:
- Request rate (requests/sec)
- Synthesis latency (p50, p95, p99)
- Error rate
- GPU utilization
- Memory usage

### Logging

Structured logging with JSON:

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }
        return json.dumps(log_data)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.getLogger().addHandler(handler)
```

---

## Security Best Practices

### 1. API Authentication

Require API keys for TTS API:

```python
from fastapi import Header, HTTPException

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != os.getenv("TTS_API_KEY"):
        raise HTTPException(401, "Invalid API key")

@app.post("/synthesize", dependencies=[Depends(verify_api_key)])
async def synthesize(request: TTSRequest):
    ...
```

### 2. Network Isolation

Use Kubernetes NetworkPolicies:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tts-api-policy
spec:
  podSelector:
    matchLabels:
      app: tts-api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: livekit-agent
    ports:
    - protocol: TCP
      port: 8001
```

### 3. Secrets Management

Use external secrets manager:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: tts-secrets
type: Opaque
stringData:
  api-key: ${TTS_API_KEY}  # Inject from Vault/AWS Secrets Manager
```

---

## Cost Optimization

### 1. Use CPU for Development, GPU for Production

```yaml
# Development
env:
- name: TTS_DEVICE
  value: "cpu"

# Production
env:
- name: TTS_DEVICE
  value: "cuda"
resources:
  limits:
    nvidia.com/gpu: 1
```

### 2. Implement Request Queueing

Prevent overload with request queues:

```python
from asyncio import Semaphore

MAX_CONCURRENT = 10
semaphore = Semaphore(MAX_CONCURRENT)

@app.post("/synthesize")
async def synthesize(request: TTSRequest):
    async with semaphore:
        # Limit concurrent synthesis
        return await synthesize_async(request)
```

### 3. Use Spot/Preemptible Instances

On cloud platforms, use cheaper spot instances for non-critical workloads.

---

## Backup and Disaster Recovery

### Model Caching

Persist model downloads to avoid re-downloading:

```yaml
volumes:
- name: model-cache
  persistentVolumeClaim:
    claimName: tts-model-cache
```

### Health Checks

Implement comprehensive health checks:

```python
@app.get("/health")
async def health_check():
    checks = {
        "model_loaded": model is not None,
        "device": str(device),
        "memory_available": check_memory(),
        "gpu_available": torch.cuda.is_available(),
    }

    if not all(checks.values()):
        raise HTTPException(503, detail=checks)

    return {"status": "healthy", "checks": checks}
```

---

## Troubleshooting

### Issue: OOM (Out of Memory)

**Solution:**
- Reduce model size (use mini instead of large)
- Increase memory limits
- Implement request queueing
- Use model quantization

### Issue: High Latency

**Solution:**
- Use GPU acceleration
- Increase replica count
- Implement caching for common phrases
- Optimize model (torch.compile)

### Issue: Connection Timeouts

**Solution:**
- Increase WebSocket timeout
- Implement keepalive
- Check network policies
- Monitor load balancer health

---

## Production Checklist

- [ ] GPU allocation configured
- [ ] Model cache persisted
- [ ] Health checks implemented
- [ ] Monitoring and alerting set up
- [ ] Autoscaling configured
- [ ] Secrets properly managed
- [ ] Network policies applied
- [ ] Backup strategy in place
- [ ] Load testing completed
- [ ] Documentation updated

---

## Additional Resources

- **Kubernetes Docs**: https://kubernetes.io/docs/
- **Docker Compose Docs**: https://docs.docker.com/compose/
- **LiveKit Cloud**: https://cloud.livekit.io
- **NVIDIA GPU Operator**: https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/
