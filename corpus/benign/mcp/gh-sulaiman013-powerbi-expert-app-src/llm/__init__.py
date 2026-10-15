"""
LLM Provider Layer

Provides a unified interface for different LLM backends:
- Ollama (local, air-gapped)
- Azure AI Foundry (private endpoints)

The key principle: schema-only interaction.
Actual data NEVER goes to the LLM.
"""

from .base_provider import BaseLLMProvider, LLMResponse, LLMConfig
from .ollama_provider import OllamaProvider
from .data_boundary import DataBoundary, SchemaInfo
from .router import LLMRouter

__all__ = [
    "BaseLLMProvider",
    "LLMResponse",
    "LLMConfig",
    "OllamaProvider",
    "DataBoundary",
    "SchemaInfo",
    "LLMRouter",
]
