"""The brains: who plays the persona. Imported lazily so a backend's SDK is only
needed when that backend is chosen."""

from __future__ import annotations

from ..spec import BrainSpec
from .base import BrainError, BrainSession, HarnessBrain, LoopBrain, ToolOutcome, ToolSpec

__all__ = [
    "BrainError",
    "BrainSession",
    "HarnessBrain",
    "LoopBrain",
    "ToolOutcome",
    "ToolSpec",
    "make_brain",
]


def make_brain(spec: BrainSpec) -> LoopBrain | HarnessBrain:
    backend = spec.backend
    if backend == "scripted":
        from .scripted import ScriptedBrain

        return ScriptedBrain(spec)
    if backend == "anthropic":
        from .anthropic_api import AnthropicBrain

        return AnthropicBrain(spec)
    if backend in ("openrouter", "ollama", "openai-compat"):
        from .openai_compat import OpenAICompatBrain

        return OpenAICompatBrain(spec)
    if backend == "claude-code":
        from .claude_code import ClaudeCodeBrain

        return ClaudeCodeBrain(spec)
    if backend == "codex":
        from .codex import CodexBrain

        return CodexBrain(spec)
    raise BrainError(f"unknown brain backend: {backend}")
