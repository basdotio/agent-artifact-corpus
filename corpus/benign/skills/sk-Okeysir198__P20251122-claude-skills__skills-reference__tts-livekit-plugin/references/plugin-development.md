# LiveKit TTS Plugin Development Guide

## Overview

This guide explains how to build a custom TTS plugin for LiveKit Agents that connects to a self-hosted TTS API with streaming support.

---

## LiveKit TTS Plugin Architecture

### Core Components

1. **TTS Class** - Main plugin interface implementing `livekit.agents.tts.TTS`
2. **ChunkedStream** - Streaming synthesis session implementing `livekit.agents.tts.ChunkedStream`
3. **TTSCapabilities** - Declares plugin capabilities (streaming, etc.)
4. **SynthesizedAudio** - Audio output format

---

## TTS Class Implementation

### Basic Structure

```python
from livekit.agents import tts as tts_agents

class TTS(tts_agents.TTS):
    """Custom TTS plugin."""

    def __init__(
        self,
        *,
        api_url: str,
        options: TTSOptions,
        http_session: Optional[aiohttp.ClientSession] = None,
    ):
        # Define capabilities
        super().__init__(
            capabilities=tts_agents.TTSCapabilities(
                streaming=True,  # Supports streaming
            ),
            sample_rate=24000,  # Audio sample rate
            num_channels=1,     # Mono audio
        )

        self._api_url = api_url
        self._options = options
        self._session = http_session
        self._own_session = http_session is None

    def synthesize(self, text: str) -> "ChunkedStream":
        """Create a streaming synthesis session."""
        return ChunkedStream(
            tts=self,
            text=text,
            api_url=self._api_url,
            options=self._options,
        )

    async def aclose(self):
        """Clean up resources."""
        if self._own_session and self._session:
            await self._session.close()
```

### Key Methods

**`__init__`**: Initialize plugin with configuration
- Set `capabilities` to declare what the plugin supports
- Set `sample_rate` and `num_channels` for audio output
- Store API connection details

**`synthesize(text)`**: Create a streaming synthesis session
- Returns a `ChunkedStream` instance
- Called by LiveKit when agent needs to speak

**`aclose()`**: Clean up resources when plugin is destroyed
- Close HTTP sessions
- Release any held resources

---

## ChunkedStream Implementation

### Basic Structure

```python
from livekit.agents import tts as tts_agents

class ChunkedStream(tts_agents.ChunkedStream):
    """Streaming synthesis session."""

    def __init__(self, *, tts: TTS, text: str, api_url: str, options: TTSOptions):
        super().__init__(tts=tts, input_text=text)

        self._text = text
        self._api_url = api_url
        self._options = options

        # WebSocket connection
        self._ws: Optional[websockets.WebSocketClientProtocol] = None

        # Async queues for communication
        self._text_queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
        self._audio_queue: asyncio.Queue[Optional[tts_agents.SynthesizedAudio]] = asyncio.Queue()

        # State tracking
        self._closed = False
        self._segment_id = 0

    def __aiter__(self):
        """Enable async iteration."""
        return self

    async def __anext__(self) -> tts_agents.SynthesizedAudio:
        """Get next audio chunk."""
        if self._main_task is None:
            self._main_task = asyncio.create_task(self._run())

        audio = await self._audio_queue.get()
        if audio is None:
            raise StopAsyncIteration

        return audio

    async def _run(self):
        """Main execution loop."""
        # Connect to WebSocket, send text, receive audio
        ...

    async def aclose(self):
        """Close stream and cleanup."""
        ...
```

### Async Iterator Pattern

The plugin uses Python's async iterator pattern:

```python
# LiveKit will iterate over the stream
stream = tts.synthesize("Hello, world!")

async for audio_chunk in stream:
    # audio_chunk is a SynthesizedAudio object
    # LiveKit automatically plays the audio
    pass
```

**Implementation:**
1. `__aiter__()` - Returns self, starts main task
2. `__anext__()` - Returns next audio chunk or raises StopAsyncIteration
3. `_run()` - Main loop that connects to API and processes audio

---

## WebSocket Communication Pattern

### Connection Flow

```python
async def _run(self):
    """Main execution loop."""
    try:
        # 1. Build WebSocket URL
        ws_url = self._api_url.replace("http://", "ws://")
        ws_url = urljoin(ws_url, "/ws/synthesize")

        # 2. Connect
        async with websockets.connect(ws_url) as ws:
            self._ws = ws

            # 3. Send configuration
            config = {
                "voice_description": self._options.voice_description,
                "sample_rate": self._options.sample_rate,
            }
            await ws.send(json.dumps(config))

            # 4. Wait for ready
            ready_msg = await ws.recv()
            ready_data = json.loads(ready_msg)
            if ready_data.get("type") != "ready":
                raise RuntimeError("Server not ready")

            # 5. Start send/receive tasks
            self._send_task = asyncio.create_task(self._send_loop())
            self._recv_task = asyncio.create_task(self._recv_loop())

            # 6. Queue text for synthesis
            await self._text_queue.put(self._text)
            await self._text_queue.put(None)  # Signal end

            # 7. Wait for completion
            await asyncio.gather(self._send_task, self._recv_task)

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await self._audio_queue.put(None)

    finally:
        self._closed = True
        if self._ws:
            await self._ws.close()
```

### Send Loop

```python
async def _send_loop(self):
    """Send text to API for synthesis."""
    try:
        while not self._closed:
            text = await self._text_queue.get()

            if text is None:
                # Send end-of-stream
                await self._ws.send(json.dumps({"type": "end_of_stream"}))
                break

            # Send text chunk
            await self._ws.send(json.dumps({"text": text}))

    except Exception as e:
        logger.error(f"Send loop error: {e}")
```

### Receive Loop

```python
async def _recv_loop(self):
    """Receive synthesized audio from API."""
    try:
        while not self._closed and self._ws:
            message = await self._ws.recv()
            data = json.loads(message)

            if data.get("type") == "audio":
                # Decode base64 audio
                audio_b64 = data.get("data", "")
                audio_bytes = base64.b64decode(audio_b64)

                # Convert to numpy array
                audio_np = np.frombuffer(audio_bytes, dtype=np.int16)

                # Create audio frame
                frame = rtc.AudioFrame(
                    data=audio_np.tobytes(),
                    sample_rate=self._options.sample_rate,
                    num_channels=1,
                    samples_per_channel=len(audio_np),
                )

                # Create synthesized audio
                synthesized = tts_agents.SynthesizedAudio(
                    request_id="",
                    segment_id=str(self._segment_id),
                    frame=frame,
                )
                self._segment_id += 1

                await self._audio_queue.put(synthesized)

            elif data.get("type") == "complete":
                # Synthesis complete
                break

    except Exception as e:
        logger.error(f"Receive loop error: {e}")

    finally:
        await self._audio_queue.put(None)  # Signal completion
```

---

## SynthesizedAudio Format

### Structure

```python
@dataclass
class SynthesizedAudio:
    request_id: str          # Request identifier (can be empty)
    segment_id: str          # Segment identifier (incrementing)
    frame: rtc.AudioFrame    # Audio data
```

### Creating Audio Frames

```python
from livekit import rtc
import numpy as np

# Audio data as int16 PCM bytes
audio_bytes = b'...'
audio_np = np.frombuffer(audio_bytes, dtype=np.int16)

# Create frame
frame = rtc.AudioFrame(
    data=audio_np.tobytes(),
    sample_rate=24000,
    num_channels=1,
    samples_per_channel=len(audio_np),
)

# Create synthesized audio
synthesized = tts_agents.SynthesizedAudio(
    request_id="",
    segment_id="0",
    frame=frame,
)
```

---

## Keepalive Implementation

Prevent connection timeouts with periodic keepalive messages:

```python
async def _keepalive_loop(self):
    """Send periodic keepalive messages."""
    try:
        while not self._closed and self._ws:
            await asyncio.sleep(5.0)  # 5 second interval

            if self._ws and not self._ws.closed:
                try:
                    await self._ws.send(json.dumps({"type": "keepalive"}))
                except Exception as e:
                    logger.warning(f"Keepalive failed: {e}")
                    break

    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"Keepalive error: {e}")
```

Start in `_run()`:

```python
self._keepalive_task = asyncio.create_task(self._keepalive_loop())
```

---

## Error Handling Best Practices

### 1. Graceful Failures

```python
async def _recv_loop(self):
    try:
        while not self._closed:
            message = await self._ws.recv()

            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON: {message[:100]}")
                continue  # Skip invalid messages

            # Process valid messages
            ...

    except websockets.ConnectionClosed:
        logger.info("Connection closed by server")
    except Exception as e:
        logger.error(f"Receive error: {e}")
    finally:
        await self._audio_queue.put(None)  # Always signal completion
```

### 2. Resource Cleanup

```python
async def aclose(self):
    """Ensure all resources are cleaned up."""
    if self._closed:
        return

    self._closed = True

    # Cancel all tasks
    tasks = [self._main_task, self._send_task, self._recv_task, self._keepalive_task]
    for task in tasks:
        if task and not task.done():
            task.cancel()

    # Wait for cancellation
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

    # Close WebSocket
    if self._ws and not self._ws.closed:
        await self._ws.close(code=1000)
```

### 3. Timeout Handling

```python
# Add timeouts to WebSocket operations
try:
    message = await asyncio.wait_for(
        self._ws.recv(),
        timeout=30.0  # 30 second timeout
    )
except asyncio.TimeoutError:
    logger.error("Receive timeout")
    break
```

---

## Plugin Packaging

### Directory Structure

```
livekit-plugins-custom-tts/
├── livekit/
│   └── plugins/
│       └── custom_tts/
│           ├── __init__.py
│           ├── tts.py
│           └── version.py
├── examples/
│   ├── voice_agent.py
│   └── basic_usage.py
├── tests/
│   └── test_tts.py
├── pyproject.toml
├── README.md
└── LICENSE
```

### pyproject.toml

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "livekit-plugins-custom-tts"
version = "0.1.0"
description = "LiveKit TTS plugin for self-hosted API"
dependencies = [
    "livekit-agents>=0.8.0",
    "aiohttp>=3.9.0",
    "websockets>=12.0",
    "numpy>=1.24.0",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["livekit*"]
```

### Installation

```bash
# Development installation
pip install -e .

# Production installation
pip install livekit-plugins-custom-tts
```

---

## Usage in Voice Agent

```python
from livekit import agents
from livekit.agents import AgentSession
from livekit.plugins import openai, deepgram, silero
from livekit.plugins import custom_tts  # Your plugin

async def entrypoint(ctx: agents.JobContext):
    # Initialize session with custom TTS
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-2"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=custom_tts.TTS(
            api_url="http://localhost:8001",
            options=custom_tts.TTSOptions(
                voice_description="A friendly voice",
                sample_rate=24000,
            ),
        ),
    )

    await ctx.connect()
    await session.start(agent=MyAgent(), room=ctx.room)
```

---

## Testing

### Unit Tests

```python
import pytest
from livekit.plugins import custom_tts

@pytest.mark.asyncio
async def test_tts_synthesize():
    tts = custom_tts.TTS(api_url="http://localhost:8001")

    stream = tts.synthesize("Hello, world!")

    chunks = []
    async for chunk in stream:
        chunks.append(chunk)

    assert len(chunks) > 0
    assert all(isinstance(c, tts_agents.SynthesizedAudio) for c in chunks)

    await tts.aclose()
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_voice_agent_with_custom_tts():
    # Test full agent with custom TTS
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(),
        llm=openai.LLM(),
        tts=custom_tts.TTS(api_url="http://localhost:8001"),
    )

    # Simulate user input
    result = await session.run(user_input="Hello")

    # Verify TTS was used
    assert result.has_audio_output()
```

---

## Debugging Tips

### Enable Debug Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("livekit.plugins.custom_tts")
logger.setLevel(logging.DEBUG)
```

### Monitor WebSocket Messages

```python
async def _recv_loop(self):
    while not self._closed:
        message = await self._ws.recv()
        logger.debug(f"Received: {message[:200]}")  # Log first 200 chars
        ...
```

### Track Audio Chunks

```python
synthesized = tts_agents.SynthesizedAudio(...)
logger.info(f"Sending audio chunk {self._segment_id}: {len(audio_np)} samples")
```

---

## Performance Optimization

### 1. Connection Pooling

Reuse HTTP sessions:

```python
class TTS(tts_agents.TTS):
    def __init__(self, *, http_session: Optional[aiohttp.ClientSession] = None):
        self._session = http_session or aiohttp.ClientSession()
        self._own_session = http_session is None
```

### 2. Batch Multiple Sentences

When possible, send multiple sentences together:

```python
# Instead of one sentence at a time
for sentence in sentences:
    await self._text_queue.put(sentence)

# Send in batches
batch = " ".join(sentences[:3])
await self._text_queue.put(batch)
```

### 3. Reduce Base64 Overhead

For high-throughput scenarios, consider binary WebSocket messages:

```python
# Server sends binary instead of JSON
await websocket.send(audio_bytes)  # Binary frame

# Client receives
message = await websocket.recv()
if isinstance(message, bytes):
    audio_bytes = message
```

---

## Common Issues and Solutions

### Issue: Audio Choppy or Glitchy

**Cause:** Network latency or slow synthesis

**Solution:**
- Implement buffering before playback
- Increase chunk sizes
- Use faster model or GPU acceleration

### Issue: WebSocket Connection Drops

**Cause:** No keepalive, network timeout

**Solution:**
- Implement keepalive messages (5s interval)
- Add connection retry logic
- Handle reconnection gracefully

### Issue: High Memory Usage

**Cause:** Audio buffers not released

**Solution:**
- Clear buffers after sending to queue
- Limit queue sizes
- Monitor with memory profiler

---

## Additional Resources

- **LiveKit Agents Docs**: https://docs.livekit.io/agents/
- **TTS API Reference**: https://docs.livekit.io/reference/python/v1/livekit/agents/tts/
- **Example Plugins**: https://github.com/livekit/agents/tree/main/livekit-plugins
- **WebSocket Docs**: https://websockets.readthedocs.io/
