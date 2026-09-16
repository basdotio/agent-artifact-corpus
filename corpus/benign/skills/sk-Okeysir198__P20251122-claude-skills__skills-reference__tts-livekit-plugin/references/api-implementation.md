# TTS API Implementation Best Practices

## Architecture Overview

A production-ready self-hosted TTS API should support:

1. **Batch synthesis** - REST endpoint for simple text-to-speech
2. **Streaming synthesis** - WebSocket for real-time incremental synthesis
3. **Model management** - Efficient loading and caching
4. **Error handling** - Graceful failures and retries
5. **Monitoring** - Health checks and metrics

---

## API Design

### REST Endpoint (Batch Synthesis)

**Endpoint:** `POST /synthesize`

**Request:**
```json
{
  "text": "Hello, world!",
  "voice_description": "A friendly, clear voice",
  "format": "wav"
}
```

**Response:**
```
Content-Type: audio/wav
X-Sample-Rate: 24000

<audio binary data>
```

**Use case:** Simple, one-off synthesis where latency is not critical

---

### WebSocket Endpoint (Streaming Synthesis)

**Endpoint:** `WS /ws/synthesize`

**Protocol:**

1. **Client connects and sends config:**
```json
{
  "voice_description": "A friendly voice",
  "sample_rate": 24000
}
```

2. **Server responds with ready:**
```json
{
  "type": "ready",
  "message": "Ready to synthesize",
  "sample_rate": 24000
}
```

3. **Client sends text (can be incremental):**
```json
{
  "text": "Hello, world!"
}
```

4. **Server responds with audio chunks:**
```json
{
  "type": "audio",
  "data": "<base64-encoded PCM>",
  "sample_rate": 24000
}
```

5. **Client signals end:**
```json
{
  "type": "end_of_stream"
}
```

6. **Server confirms completion:**
```json
{
  "type": "complete",
  "message": "Synthesis completed"
}
```

**Use case:** Real-time voice agents requiring low latency

---

## Streaming Best Practices

### 1. Sentence-Level Chunking

Split incoming text into sentences and synthesize incrementally:

```python
def split_into_sentences(text: str) -> list[str]:
    """Split text at sentence boundaries."""
    import re
    sentences = re.split(r'([.!?]+\s+)', text)

    result = []
    for i in range(0, len(sentences) - 1, 2):
        result.append(sentences[i] + sentences[i + 1])

    if len(sentences) % 2 == 1:
        result.append(sentences[-1])

    return result if result else [text]

# Usage
text_buffer = ""
async for incoming_text in websocket:
    text_buffer += incoming_text
    sentences = split_into_sentences(text_buffer)

    # Synthesize complete sentences
    for sentence in sentences[:-1]:
        audio = await synthesize(sentence)
        await websocket.send(audio)

    # Keep incomplete sentence
    text_buffer = sentences[-1]
```

**Benefits:**
- Natural prosody at sentence boundaries
- Lower perceived latency (first sentence plays while generating rest)
- Better error recovery

### 2. Keepalive Messages

Prevent connection timeout on long-running streams:

```python
async def keepalive_loop(websocket):
    """Send periodic keepalive messages."""
    while not closed:
        await asyncio.sleep(5.0)
        await websocket.send(json.dumps({"type": "keepalive"}))
```

**Industry standard:** 5-10 second intervals (based on Deepgram, Google, AWS patterns)

### 3. End-of-Stream Signaling

Explicitly signal when synthesis is complete:

```python
# Client sends
{"type": "end_of_stream"}

# Server processes remaining buffer, then responds
{"type": "complete"}
```

**Benefits:**
- Client knows when all audio is received
- Enables graceful connection closure
- Prevents data loss

### 4. Error Handling

Always handle and communicate errors:

```python
try:
    audio = await synthesize(text)
    await websocket.send_json({
        "type": "audio",
        "data": base64.b64encode(audio).decode()
    })
except Exception as e:
    logger.error(f"Synthesis error: {e}")
    await websocket.send_json({
        "type": "error",
        "message": str(e)
    })
```

---

## Model Management

### Singleton Pattern

Load model once at startup, reuse across requests:

```python
# Global model instance
model = None

@app.on_event("startup")
async def startup_event():
    global model
    model = ParlerTTSForConditionalGeneration.from_pretrained(
        "parler-tts/parler-tts-mini-v1"
    ).to("cuda")
    logger.info("Model loaded")

@app.post("/synthesize")
async def synthesize(request: TTSRequest):
    if model is None:
        raise HTTPException(503, "Model not loaded")
    # Use global model
    audio = model.generate(...)
```

**Benefits:**
- Faster response (no model loading per request)
- Lower memory usage
- Predictable latency

### Async Synthesis

Run synthesis in executor to avoid blocking event loop:

```python
async def synthesize_async(text: str) -> bytes:
    """Run synthesis in thread pool executor."""
    loop = asyncio.get_event_loop()
    audio = await loop.run_in_executor(
        None,  # Use default executor
        lambda: _synthesize_sync(text)
    )
    return audio

def _synthesize_sync(text: str) -> bytes:
    """Synchronous synthesis function."""
    # Model inference here
    generation = model.generate(...)
    return generation.cpu().numpy().tobytes()
```

**Benefits:**
- Non-blocking for other requests
- Better concurrency
- Scalable to multiple workers

---

## Audio Format Handling

### PCM Int16 (Recommended for Streaming)

```python
# Convert float32 audio to int16 PCM
audio_int16 = (audio_float32 * 32767).astype(np.int16)
audio_bytes = audio_int16.tobytes()
```

**Benefits:**
- Efficient encoding
- Universal compatibility
- Low overhead

### WAV Format (Batch Synthesis)

```python
import wave
import io

def create_wav(audio_bytes: bytes, sample_rate: int) -> bytes:
    """Create WAV file from PCM data."""
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_bytes)
    wav_io.seek(0)
    return wav_io.read()
```

### Base64 Encoding (WebSocket)

```python
import base64

# Encode binary audio for JSON transmission
audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')

await websocket.send_json({
    "type": "audio",
    "data": audio_b64
})
```

---

## Health Checks and Monitoring

### Health Endpoint

```python
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "device": str(device),
        "uptime_seconds": time.time() - start_time
    }
```

### Metrics Collection

```python
from prometheus_client import Counter, Histogram

synthesis_requests = Counter('tts_requests_total', 'Total synthesis requests')
synthesis_latency = Histogram('tts_latency_seconds', 'Synthesis latency')

@app.post("/synthesize")
async def synthesize(request: TTSRequest):
    synthesis_requests.inc()

    with synthesis_latency.time():
        audio = await synthesize_async(request.text)

    return Response(content=audio, media_type="audio/wav")
```

---

## Security Considerations

### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/synthesize")
@limiter.limit("10/minute")
async def synthesize(request: TTSRequest):
    ...
```

### Input Validation

```python
from pydantic import BaseModel, Field, validator

class TTSRequest(BaseModel):
    text: str = Field(..., max_length=5000)
    voice_description: str = Field(default="neutral voice", max_length=500)

    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError('Text cannot be empty')
        return v
```

### Authentication (Optional)

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

@app.post("/synthesize")
async def synthesize(
    request: TTSRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # Verify token
    if not verify_token(credentials.credentials):
        raise HTTPException(401, "Invalid token")
    ...
```

---

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY main.py .

# Expose port
EXPOSE 8001

# Run
CMD ["python", "main.py"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  tts-api:
    build: .
    ports:
      - "8001:8001"
    environment:
      - TTS_MODEL_TYPE=parler
      - TTS_MODEL_NAME=parler-tts/parler-tts-mini-v1
      - TTS_DEVICE=cuda
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped
```

---

## Performance Optimization

### 1. Model Optimization

```python
# Use torch.compile for faster inference (PyTorch 2.0+)
model = torch.compile(model, mode="reduce-overhead")

# Use half precision on GPU
if device == "cuda":
    model = model.half()
```

### 2. Batch Processing

```python
async def synthesize_batch(texts: list[str]) -> list[bytes]:
    """Synthesize multiple texts in parallel."""
    tasks = [synthesize_async(text) for text in texts]
    return await asyncio.gather(*tasks)
```

### 3. Response Streaming

```python
@app.post("/synthesize-stream")
async def synthesize_stream(request: TTSRequest):
    """Stream audio as it's generated."""
    async def audio_generator():
        sentences = split_into_sentences(request.text)
        for sentence in sentences:
            audio = await synthesize_async(sentence)
            yield audio

    return StreamingResponse(
        audio_generator(),
        media_type="audio/wav"
    )
```

---

## Testing

### Unit Tests

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_synthesize():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/synthesize",
            json={"text": "Hello, world!"}
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/wav"
```

### Load Testing

```bash
# Using Apache Bench
ab -n 1000 -c 10 -p request.json -T application/json \
   http://localhost:8001/synthesize

# Using Locust
locust -f load_test.py --host=http://localhost:8001
```

---

## Troubleshooting

### High Latency

**Causes:**
- Model on CPU instead of GPU
- Synchronous synthesis blocking event loop
- Large batch sizes

**Solutions:**
- Use GPU acceleration
- Use async synthesis with executor
- Implement sentence-level streaming

### Memory Issues

**Causes:**
- Model not properly cached
- Audio buffers not cleared
- Memory leaks in long-running connections

**Solutions:**
- Use global model instance
- Clear buffers after sending
- Implement connection timeouts
- Monitor memory usage

### Connection Timeouts

**Causes:**
- No keepalive messages
- Long synthesis times
- Network issues

**Solutions:**
- Implement keepalive (5s interval)
- Use timeouts on both sides
- Handle disconnections gracefully

---

## Additional Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **WebSocket Best Practices**: https://websockets.readthedocs.io/
- **Streaming Patterns**: Based on Deepgram, Google Cloud STT/TTS
- **Production Deployment**: https://fastapi.tiangolo.com/deployment/
