"""
Text-to-Speech plugin for LiveKit using custom self-hosted TTS API.
"""

import asyncio
import logging
import json
import base64
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin

import aiohttp
import websockets
import numpy as np
from livekit import agents, rtc
from livekit.agents import tts as tts_agents, utils

logger = logging.getLogger(__name__)


@dataclass
class TTSOptions:
    """Configuration options for the custom TTS service."""

    voice_description: str = "A neutral, clear voice with moderate pace."
    """Description of the voice characteristics."""

    sample_rate: int = 24000
    """Audio sample rate in Hz."""

    format: str = "wav"
    """Audio format: wav, mp3, or raw."""


class TTS(tts_agents.TTS):
    """
    Text-to-Speech implementation for custom self-hosted TTS API.

    This plugin connects to a self-hosted FastAPI service running
    HuggingFace TTS models (Parler-TTS, F5-TTS, XTTS-v2) for synthesis.
    """

    def __init__(
        self,
        *,
        api_url: str = "http://localhost:8001",
        options: Optional[TTSOptions] = None,
        http_session: Optional[aiohttp.ClientSession] = None,
    ):
        """
        Initialize the TTS plugin.

        Args:
            api_url: Base URL of the self-hosted TTS API
            options: Configuration options for synthesis
            http_session: Optional aiohttp session for connection pooling
        """
        super().__init__(
            capabilities=tts_agents.TTSCapabilities(
                streaming=True,
            ),
            sample_rate=options.sample_rate if options else 24000,
            num_channels=1,
        )

        self._api_url = api_url.rstrip("/")
        self._options = options or TTSOptions()
        self._session = http_session
        self._own_session = http_session is None

    def synthesize(
        self,
        text: str,
    ) -> "ChunkedStream":
        """
        Synthesize speech from text using streaming.

        Args:
            text: Text to synthesize

        Returns:
            ChunkedStream for real-time audio output
        """
        return ChunkedStream(
            tts=self,
            text=text,
            api_url=self._api_url,
            options=self._options,
        )

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure HTTP session exists."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def aclose(self):
        """Clean up resources."""
        if self._own_session and self._session is not None:
            await self._session.close()
            self._session = None


class ChunkedStream(tts_agents.ChunkedStream):
    """
    Streaming synthesis session using WebSocket.

    This implements sentence-level streaming where the TTS synthesizes
    text incrementally as it's received, providing low-latency audio output.
    """

    def __init__(
        self,
        *,
        tts: TTS,
        text: str,
        api_url: str,
        options: TTSOptions,
    ):
        super().__init__(tts=tts, input_text=text)

        self._tts = tts
        self._text = text
        self._api_url = api_url
        self._options = options

        # WebSocket connection
        self._ws: Optional[websockets.WebSocketClientProtocol] = None

        # Tasks for managing the stream
        self._send_task: Optional[asyncio.Task] = None
        self._recv_task: Optional[asyncio.Task] = None

        # Text queue for sending
        self._text_queue: asyncio.Queue[Optional[str]] = asyncio.Queue()

        # Audio queue for receiving synthesized audio
        self._audio_queue: asyncio.Queue[Optional[tts_agents.SynthesizedAudio]] = asyncio.Queue()

        # State tracking
        self._closed = False
        self._input_ended = False
        self._main_task: Optional[asyncio.Task] = None

        # Keepalive for long connections
        self._keepalive_task: Optional[asyncio.Task] = None

        # Segment ID tracking
        self._segment_id = 0

    def __aiter__(self):
        """Initialize async iteration and start the main task."""
        return self

    async def __anext__(self) -> tts_agents.SynthesizedAudio:
        """Get the next synthesized audio chunk."""
        # Start the main task on first iteration
        if self._main_task is None:
            self._main_task = asyncio.create_task(self._run())

        audio = await self._audio_queue.get()

        if audio is None:
            raise StopAsyncIteration

        return audio

    async def _run(self):
        """Main execution loop for the stream."""
        try:
            # Build WebSocket URL
            ws_url = self._api_url.replace("http://", "ws://").replace("https://", "wss://")
            ws_url = urljoin(ws_url, "/ws/synthesize")

            # Connect to WebSocket
            async with websockets.connect(ws_url) as ws:
                self._ws = ws
                logger.info(f"Connected to TTS WebSocket: {ws_url}")

                # Send configuration
                config = {
                    "voice_description": self._options.voice_description,
                    "sample_rate": self._options.sample_rate,
                }
                await ws.send(json.dumps(config))

                # Wait for ready message
                ready_msg = await ws.recv()
                ready_data = json.loads(ready_msg)
                if ready_data.get("type") != "ready":
                    raise RuntimeError(f"Unexpected response: {ready_data}")

                logger.info("TTS WebSocket ready")

                # Start send, receive, and keepalive tasks
                self._send_task = asyncio.create_task(self._send_loop())
                self._recv_task = asyncio.create_task(self._recv_loop())
                self._keepalive_task = asyncio.create_task(self._keepalive_loop())

                # Queue the input text for synthesis
                await self._text_queue.put(self._text)
                await self._text_queue.put(None)  # Signal end

                # Wait for tasks to complete
                await asyncio.gather(self._send_task, self._recv_task, self._keepalive_task)

        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await self._audio_queue.put(None)

        finally:
            self._closed = True
            if self._ws:
                await self._ws.close()

    async def _send_loop(self):
        """Send text to the WebSocket for synthesis."""
        try:
            while not self._closed:
                text = await self._text_queue.get()

                if text is None:
                    # Send end-of-stream message
                    if self._ws and not self._ws.closed:
                        try:
                            await self._ws.send(json.dumps({"type": "end_of_stream"}))
                            logger.info("Sent end_of_stream message to server")
                        except Exception as e:
                            logger.warning(f"Failed to send end_of_stream: {e}")
                    break

                if self._ws and not self._ws.closed:
                    # Send text for synthesis
                    await self._ws.send(json.dumps({"text": text}))

        except asyncio.CancelledError:
            logger.debug("Send loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Send loop error: {e}")

    async def _recv_loop(self):
        """Receive synthesized audio from the WebSocket."""
        try:
            while not self._closed and self._ws:
                message = await self._ws.recv()

                # Parse JSON response
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    logger.warning(f"Received non-JSON message: {message[:100]}")
                    continue

                event_type = data.get("type")

                if event_type == "audio":
                    # Decode base64 audio data
                    audio_b64 = data.get("data", "")
                    audio_bytes = base64.b64decode(audio_b64)

                    # Convert to numpy array (int16 PCM)
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
                        request_id="",  # Not used in streaming
                        segment_id=str(self._segment_id),
                        frame=frame,
                    )
                    self._segment_id += 1

                    await self._audio_queue.put(synthesized)

                elif event_type == "complete":
                    # Synthesis complete
                    logger.info("Synthesis completed")
                    break

                elif event_type == "error":
                    logger.error(f"TTS error: {data.get('message')}")
                    break

        except asyncio.CancelledError:
            logger.debug("Receive loop cancelled")
            raise
        except websockets.ConnectionClosed:
            logger.info("WebSocket connection closed by server")
        except Exception as e:
            logger.error(f"Receive loop error: {e}")

        finally:
            # Signal completion
            await self._audio_queue.put(None)

    async def _keepalive_loop(self):
        """
        Send periodic keepalive messages.
        Prevents connection timeout on long-running streams.
        """
        try:
            while not self._closed and self._ws:
                await asyncio.sleep(5.0)  # 5 second interval

                if self._ws and not self._ws.closed and not self._input_ended:
                    try:
                        await self._ws.send(json.dumps({"type": "keepalive"}))
                        logger.debug("Sent keepalive")
                    except Exception as e:
                        logger.warning(f"Keepalive failed: {e}")
                        break

        except asyncio.CancelledError:
            logger.debug("Keepalive loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Keepalive loop error: {e}")

    async def aclose(self):
        """Close the stream and clean up resources."""
        if self._closed:
            return

        self._closed = True
        logger.debug("aclose() called")

        # Send end sentinel if not already sent
        if not self._input_ended:
            self._input_ended = True
            try:
                await asyncio.wait_for(
                    self._text_queue.put(None),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                logger.warning("Timeout queuing end sentinel")

        # Cancel all tasks gracefully
        tasks_to_cancel = []
        if self._main_task and not self._main_task.done():
            tasks_to_cancel.append(self._main_task)
        if self._send_task and not self._send_task.done():
            tasks_to_cancel.append(self._send_task)
        if self._recv_task and not self._recv_task.done():
            tasks_to_cancel.append(self._recv_task)
        if self._keepalive_task and not self._keepalive_task.done():
            tasks_to_cancel.append(self._keepalive_task)

        for task in tasks_to_cancel:
            task.cancel()

        # Wait for cancellation to complete
        if tasks_to_cancel:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)

        # Close WebSocket with proper close code
        if self._ws and not self._ws.closed:
            try:
                await self._ws.close(code=1000)
                logger.debug("WebSocket closed normally")
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")
