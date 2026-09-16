"""
LiveKit TTS plugin for custom self-hosted TTS API.
"""

from .tts import TTS, TTSOptions
from .version import __version__

__all__ = ["TTS", "TTSOptions", "__version__"]
