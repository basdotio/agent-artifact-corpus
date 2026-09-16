"""
Example LiveKit voice agent using custom self-hosted TTS plugin.
"""

import asyncio
import logging
from livekit import agents, rtc
from livekit.agents import AgentSession, JobContext, WorkerOptions, cli
from livekit.plugins import openai, deepgram, silero

# Import custom TTS plugin
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from livekit.plugins import custom_tts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def prewarm(proc: agents.JobProcess):
    """Load static resources before sessions start."""
    # Load VAD model once and reuse across sessions
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    """Main agent entry point with custom TTS."""
    logger.info("Starting voice agent with custom TTS")

    # Get prewarmed VAD
    vad = ctx.proc.userdata["vad"]

    # Initialize session with custom TTS plugin
    session = AgentSession(
        vad=vad,
        stt=deepgram.STT(model="nova-2-general"),
        llm=openai.LLM(model="gpt-4o-mini"),
        # Use custom self-hosted TTS instead of cloud provider
        tts=custom_tts.TTS(
            api_url="http://localhost:8001",  # Your TTS API URL
            options=custom_tts.TTSOptions(
                voice_description="A friendly, conversational voice with moderate pace.",
                sample_rate=24000,
            ),
        ),
    )

    # Connect to room
    await ctx.connect()

    # Simple voice agent that echoes user input
    from livekit.agents import Agent

    class EchoAgent(Agent):
        """Simple agent that uses custom TTS."""

        def __init__(self):
            super().__init__(
                instructions="""You are a helpful voice assistant.

Your role:
1. Greet users warmly
2. Answer their questions clearly and concisely
3. Maintain a friendly, conversational tone

Be natural and engaging in your responses."""
            )

    # Create and start agent
    agent = EchoAgent()
    await session.start(agent=agent, room=ctx.room)


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        )
    )
