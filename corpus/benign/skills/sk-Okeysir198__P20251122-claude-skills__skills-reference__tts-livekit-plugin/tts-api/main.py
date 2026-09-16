"""
Self-hosted TTS API using HuggingFace models and FastAPI.
Provides both batch synthesis and real-time streaming via WebSocket.
Supports Parler-TTS, F5-TTS, and XTTS-v2 models.
"""

import asyncio
import json
import logging
import os
from typing import Optional, Literal
from io import BytesIO
import base64

import numpy as np
import torch
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Self-Hosted TTS API",
    description="Text-to-Speech API using HuggingFace models with streaming support",
    version="1.0.0"
)

# Global model instance
model = None
tokenizer = None
feature_extractor = None

# Configuration
MODEL_TYPE = os.getenv("TTS_MODEL_TYPE", "parler")  # parler, f5, xtts
MODEL_NAME = os.getenv("TTS_MODEL_NAME", "parler-tts/parler-tts-mini-v1")
DEVICE = os.getenv("TTS_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
SAMPLE_RATE = 24000  # Standard for most TTS models


class TTSRequest(BaseModel):
    """Request model for batch TTS synthesis."""
    text: str
    voice_description: Optional[str] = "A neutral, clear voice with moderate pace."
    format: Literal["wav", "mp3", "raw"] = "wav"


def load_model():
    """Load the TTS model on startup."""
    global model, tokenizer, feature_extractor

    logger.info(f"Loading TTS model: {MODEL_NAME} ({MODEL_TYPE}) on {DEVICE}")

    if MODEL_TYPE == "parler":
        from parler_tts import ParlerTTSForConditionalGeneration
        from transformers import AutoTokenizer

        model = ParlerTTSForConditionalGeneration.from_pretrained(MODEL_NAME).to(DEVICE)
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    elif MODEL_TYPE == "f5":
        from f5_tts import F5TTS
        model = F5TTS(MODEL_NAME, device=DEVICE)

    elif MODEL_TYPE == "xtts":
        from TTS.api import TTS
        model = TTS(MODEL_NAME).to(DEVICE)

    else:
        raise ValueError(f"Unknown model type: {MODEL_TYPE}")

    logger.info("Model loaded successfully")


@app.on_event("startup")
async def startup_event():
    """Initialize model on startup."""
    load_model()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model_type": MODEL_TYPE,
        "model_name": MODEL_NAME,
        "device": DEVICE,
        "sample_rate": SAMPLE_RATE
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "model_loaded": model is not None}


@app.post("/synthesize")
async def synthesize_speech(request: TTSRequest):
    """
    Synthesize speech from text.

    Args:
        request: TTS request with text and voice description

    Returns:
        Audio file in requested format
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        logger.info(f"Synthesizing: '{request.text[:50]}...'")

        # Generate speech based on model type
        if MODEL_TYPE == "parler":
            # Tokenize text and voice description
            input_ids = tokenizer(request.voice_description, return_tensors="pt").input_ids.to(DEVICE)
            prompt_input_ids = tokenizer(request.text, return_tensors="pt").input_ids.to(DEVICE)

            # Generate audio
            generation = model.generate(
                input_ids=input_ids,
                prompt_input_ids=prompt_input_ids,
                do_sample=True,
                temperature=1.0
            )
            audio_arr = generation.cpu().numpy().squeeze()

        elif MODEL_TYPE == "f5":
            audio_arr = model.sample(
                text=request.text,
                target_sample_rate=SAMPLE_RATE
            )

        elif MODEL_TYPE == "xtts":
            audio_arr = model.tts(text=request.text)

        # Convert to bytes
        audio_bytes = (audio_arr * 32767).astype(np.int16).tobytes()

        # Return based on format
        if request.format == "raw":
            return Response(
                content=audio_bytes,
                media_type="application/octet-stream",
                headers={"X-Sample-Rate": str(SAMPLE_RATE)}
            )

        elif request.format == "wav":
            import io
            import wave

            wav_io = io.BytesIO()
            with wave.open(wav_io, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(SAMPLE_RATE)
                wav_file.writeframes(audio_bytes)

            wav_io.seek(0)
            return Response(
                content=wav_io.read(),
                media_type="audio/wav"
            )

        elif request.format == "mp3":
            # Convert to MP3 using pydub
            from pydub import AudioSegment
            import io

            audio_segment = AudioSegment(
                data=audio_bytes,
                sample_width=2,
                frame_rate=SAMPLE_RATE,
                channels=1
            )

            mp3_io = io.BytesIO()
            audio_segment.export(mp3_io, format="mp3", bitrate="192k")
            mp3_io.seek(0)

            return Response(
                content=mp3_io.read(),
                media_type="audio/mpeg"
            )

    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/synthesize")
async def websocket_synthesize(websocket: WebSocket):
    """
    WebSocket endpoint for real-time streaming TTS.

    Protocol:
    - Client connects and sends configuration:
      {"voice_description": "clear voice", "sample_rate": 24000}
    - Client sends text chunks:
      {"text": "Hello world"}
    - Server responds with audio chunks:
      {"type": "audio", "data": "<base64>", "sample_rate": 24000}
      {"type": "complete"}
    """
    await websocket.accept()
    logger.info("WebSocket client connected")

    if model is None:
        await websocket.send_json({"type": "error", "message": "Model not loaded"})
        await websocket.close()
        return

    try:
        # Receive configuration
        config_msg = await websocket.receive_text()
        config = json.loads(config_msg)

        voice_description = config.get("voice_description", "A neutral, clear voice.")
        requested_sample_rate = config.get("sample_rate", SAMPLE_RATE)

        logger.info(f"WebSocket config: voice='{voice_description}', sr={requested_sample_rate}")

        # Send acknowledgment
        await websocket.send_json({
            "type": "ready",
            "message": "Ready to synthesize",
            "sample_rate": SAMPLE_RATE
        })

        # Text buffer for sentence-level synthesis
        text_buffer = ""

        while True:
            try:
                message = await websocket.receive()

                # Handle text messages (synthesis requests and control)
                if "text" in message:
                    try:
                        msg_data = json.loads(message["text"])
                        msg_type = msg_data.get("type")

                        if msg_type == "keepalive":
                            logger.debug("Received keepalive from client")
                            continue

                        elif msg_type == "end_of_stream":
                            logger.info("Received end_of_stream from client")

                            # Synthesize any remaining text
                            if text_buffer.strip():
                                audio_chunk = await synthesize_chunk(
                                    text_buffer.strip(),
                                    voice_description
                                )

                                if audio_chunk is not None:
                                    # Send audio data as base64
                                    audio_b64 = base64.b64encode(audio_chunk).decode('utf-8')
                                    await websocket.send_json({
                                        "type": "audio",
                                        "data": audio_b64,
                                        "sample_rate": SAMPLE_RATE
                                    })

                            # Send completion message
                            await websocket.send_json({
                                "type": "complete",
                                "message": "Synthesis completed"
                            })

                            logger.info("Session ended gracefully")
                            break

                        # Handle text synthesis request
                        elif "text" in msg_data:
                            text = msg_data["text"]
                            text_buffer += text

                            # Check for sentence boundaries
                            sentences = split_into_sentences(text_buffer)

                            # Synthesize complete sentences
                            for sentence in sentences[:-1]:  # All but last (may be incomplete)
                                if sentence.strip():
                                    audio_chunk = await synthesize_chunk(
                                        sentence.strip(),
                                        voice_description
                                    )

                                    if audio_chunk is not None:
                                        # Send audio data as base64
                                        audio_b64 = base64.b64encode(audio_chunk).decode('utf-8')
                                        await websocket.send_json({
                                            "type": "audio",
                                            "data": audio_b64,
                                            "sample_rate": SAMPLE_RATE
                                        })

                            # Keep incomplete sentence in buffer
                            text_buffer = sentences[-1] if sentences else ""

                        else:
                            logger.warning(f"Unknown message type: {msg_type}")

                    except json.JSONDecodeError:
                        logger.warning(f"Received invalid JSON: {message['text'][:100]}")
                        continue

                else:
                    logger.warning(f"Received unknown message type: {list(message.keys())}")

            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected")
                break
            except Exception as e:
                logger.error(f"WebSocket processing error: {e}")
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
                except:
                    pass

    except Exception as e:
        logger.error(f"WebSocket error: {e}")

    finally:
        try:
            await websocket.close(code=1000)
            logger.info("WebSocket closed")
        except Exception as e:
            logger.debug(f"Error closing websocket: {e}")


async def synthesize_chunk(text: str, voice_description: str) -> Optional[bytes]:
    """
    Synthesize a chunk of text asynchronously.

    Args:
        text: Text to synthesize
        voice_description: Voice characteristics

    Returns:
        Audio data as bytes (int16 PCM)
    """
    try:
        if MODEL_TYPE == "parler":
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            audio_arr = await loop.run_in_executor(
                None,
                lambda: _synthesize_parler(text, voice_description)
            )

        elif MODEL_TYPE == "f5":
            audio_arr = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: model.sample(text=text, target_sample_rate=SAMPLE_RATE)
            )

        elif MODEL_TYPE == "xtts":
            audio_arr = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: model.tts(text=text)
            )

        # Convert to int16 bytes
        audio_bytes = (audio_arr * 32767).astype(np.int16).tobytes()
        return audio_bytes

    except Exception as e:
        logger.error(f"Chunk synthesis error: {e}")
        return None


def _synthesize_parler(text: str, voice_description: str) -> np.ndarray:
    """Synchronous Parler-TTS synthesis."""
    input_ids = tokenizer(voice_description, return_tensors="pt").input_ids.to(DEVICE)
    prompt_input_ids = tokenizer(text, return_tensors="pt").input_ids.to(DEVICE)

    generation = model.generate(
        input_ids=input_ids,
        prompt_input_ids=prompt_input_ids,
        do_sample=True,
        temperature=1.0
    )

    return generation.cpu().numpy().squeeze()


def split_into_sentences(text: str) -> list[str]:
    """
    Split text into sentences for streaming synthesis.

    Args:
        text: Input text

    Returns:
        List of sentences
    """
    import re

    # Simple sentence splitting on common terminators
    sentences = re.split(r'([.!?]+\s+)', text)

    # Recombine sentences with their terminators
    result = []
    for i in range(0, len(sentences) - 1, 2):
        result.append(sentences[i] + sentences[i + 1])

    # Add any remaining text
    if len(sentences) % 2 == 1:
        result.append(sentences[-1])

    return result if result else [text]


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,  # Use 8001 to avoid conflict with STT on 8000
        reload=False,
        log_level="info"
    )
