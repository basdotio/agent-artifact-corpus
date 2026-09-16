"""
Basic usage example of the custom TTS plugin.
Demonstrates how to use the plugin standalone.
"""

import asyncio
import logging
import sys
import os

# Add parent directory to path to import the plugin
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from livekit.plugins import custom_tts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate basic TTS usage."""

    # Initialize TTS plugin
    tts = custom_tts.TTS(
        api_url="http://localhost:8001",  # Your TTS API URL
        options=custom_tts.TTSOptions(
            voice_description="A clear, professional voice.",
            sample_rate=24000,
        ),
    )

    # Text to synthesize
    text = "Hello! This is a test of the self-hosted text-to-speech system."

    logger.info(f"Synthesizing: {text}")

    # Synthesize text
    stream = tts.synthesize(text)

    # Collect audio frames
    audio_frames = []
    async for audio_chunk in stream:
        logger.info(f"Received audio chunk: segment_id={audio_chunk.segment_id}")
        audio_frames.append(audio_chunk.frame)

    logger.info(f"Synthesis complete! Received {len(audio_frames)} audio chunks")

    # Save to WAV file (optional)
    if audio_frames:
        import wave
        import numpy as np

        # Combine all frames
        all_data = b''.join(frame.data for frame in audio_frames)

        with wave.open("output.wav", "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(24000)
            wav_file.writeframes(all_data)

        logger.info("Audio saved to output.wav")

    # Clean up
    await tts.aclose()


if __name__ == "__main__":
    asyncio.run(main())
