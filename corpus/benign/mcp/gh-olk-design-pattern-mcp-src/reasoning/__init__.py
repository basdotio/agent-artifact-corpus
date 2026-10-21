"""src/reasoning — server-side reasoning MCP integration.

Makes design-pattern-mcp an MCP CLIENT of two structured reasoning
scratchpads (shannonthinking, code-reasoning) and injects their traces into the
ANALYZE / WEIGHTS / GENERATE / EVALUATE / RETRY phase prompts as
``<reasoning_context>``. Silent per-call degradation + loud startup health check.

Modules:
    config: ReasoningConfig / ReasoningStrategy / ReasoningTool (REASONING_* env wiring).
    schemas: ThoughtDraft, ReasoningStep, ReasoningTrace, ToolContract.
    prompts: step prompts + <reasoning_context> renderers (incl. degraded scaffold).
    client: ReasoningClient (ThoughtGenerator loop, cache, health check).
"""

from typing import TYPE_CHECKING

from src.reasoning.config import ReasoningConfig, ReasoningStrategy, ReasoningTool
from src.reasoning.schemas import (
    CODE_TOOL,
    SHANNON_TOOL,
    TOOL_CONTRACTS,
    ReasoningStep,
    ReasoningTrace,
    ThoughtDraft,
    ToolContract,
)

if TYPE_CHECKING:
    from src.reasoning.client import ReasoningClient

__all__ = [
    "CODE_TOOL",
    "SHANNON_TOOL",
    "TOOL_CONTRACTS",
    "ReasoningClient",
    "ReasoningConfig",
    "ReasoningStep",
    "ReasoningStrategy",
    "ReasoningTool",
    "ReasoningTrace",
    "ThoughtDraft",
    "ToolContract",
]


def __getattr__(name: str) -> object:
    """Lazy ``ReasoningClient`` export (PEP 562): importing it eagerly would pull
    fastmcp's client transport into every consumer of the config schemas."""
    if name == "ReasoningClient":
        from src.reasoning import client as _client

        return getattr(_client, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
