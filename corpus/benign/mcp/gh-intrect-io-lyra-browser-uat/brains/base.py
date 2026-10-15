"""What every brain has in common, and what a loop brain is handed.

Two kinds. A *loop brain* is a model behind an API: we own the tool-use loop
and hand it a ``BrainSession`` — the prompts, the tool surface, and ``call``,
which goes through the in-memory MCP client and so through the recorder. A
*harness brain* is an external agent (Claude Code, Codex) that owns its own
loop: we start it with ``lyra-browser --uat-run`` as its MCP server and read
the run's files afterwards. Both return a ``BrainInfo`` for the report.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mcp.types import ImageContent, TextContent

from ..report import BrainInfo
from ..spec import RunSpec

TRUNCATED = "\n...[truncated by lyra-uat: {more} more characters]"


class BrainError(RuntimeError):
    """The brain cannot go on: no credentials, a missing executable, an API that
    keeps failing. The run is reported with ``exit_reason: brain_error``."""


@dataclass(slots=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(slots=True)
class ToolOutcome:
    """One tool result as a brain sees it: the envelope, its text, any pictures."""

    payload: Any
    text: str
    images: list[bytes] = field(default_factory=list)
    is_error: bool = False

    @property
    def status(self) -> str:
        if isinstance(self.payload, dict):
            return str(self.payload.get("status") or ("error" if self.is_error else "ok"))
        return "error" if self.is_error else "ok"


class BrainSession:
    """The run from a loop brain's side."""

    def __init__(
        self,
        *,
        client: Any,
        tools: list[ToolSpec],
        system_prompt: str,
        task_prompt: str,
        max_output_chars: int,
        recorder: Any,
        spec: RunSpec,
    ) -> None:
        self.client = client
        self.tools = tools
        self.system_prompt = system_prompt
        self.task_prompt = task_prompt
        self.max_output_chars = max_output_chars
        self.recorder = recorder
        self.spec = spec

    @property
    def finished(self) -> bool:
        return bool(self.recorder.finished)

    async def call(self, name: str, args: dict[str, Any] | None = None) -> ToolOutcome:
        """Run one tool through the MCP client (and so through the recorder)."""
        result = await self.client.call_tool(name, args or {}, raise_on_error=False)
        images: list[bytes] = []
        texts: list[str] = []
        for block in result.content or []:
            if isinstance(block, ImageContent):
                try:
                    images.append(base64.b64decode(block.data))
                except ValueError:
                    continue
            elif isinstance(block, TextContent):
                texts.append(block.text)
        payload = result.structured_content if isinstance(result.structured_content, dict) else None
        text = (
            "\n".join(texts)
            if texts
            else (json.dumps(payload, ensure_ascii=False) if payload else "")
        )
        if len(text) > self.max_output_chars:
            more = len(text) - self.max_output_chars
            text = text[: self.max_output_chars] + TRUNCATED.format(more=more)
        return ToolOutcome(
            payload=payload, text=text, images=images, is_error=bool(result.is_error)
        )


class LoopBrain:
    kind = "loop"
    backend = "loop"

    async def run(self, session: BrainSession) -> BrainInfo:  # pragma: no cover - interface
        raise NotImplementedError


class HarnessBrain:
    kind = "harness"
    backend = "harness"

    async def run(
        self,
        spec: RunSpec,
        run_dir: Path,
        run_file: Path,
        *,
        system_prompt: str,
        task_prompt: str,
    ) -> BrainInfo:  # pragma: no cover - interface
        raise NotImplementedError
