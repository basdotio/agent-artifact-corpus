"""A brain that replays a fixed list of tool calls.

No model. It exists so the runner, the recorder, the guards and the report can
be exercised end to end — in the unit suite on a fake page and in the real
browser gate — with a path that is the same every time.

Script entries: ``{"tool": "click", "args": {...}, "expect": "ok"}``. ``expect``
is optional; when the status differs the brain stops with ``BrainError`` so a
gate fails loudly instead of running on. ``{"stop_if_finished": true}`` ends
the script early once ``finish`` has been called.
"""

from __future__ import annotations

from ..report import BrainInfo
from ..spec import BrainSpec
from .base import BrainError, BrainSession, LoopBrain


class ScriptedBrain(LoopBrain):
    backend = "scripted"

    def __init__(self, spec: BrainSpec) -> None:
        self.script = list(spec.script)
        self.model = spec.model

    async def run(self, session: BrainSession) -> BrainInfo:
        turns = 0
        for entry in self.script:
            if entry.get("stop_if_finished") and session.finished:
                break
            tool = entry.get("tool")
            if not tool:
                continue
            outcome = await session.call(str(tool), dict(entry.get("args") or {}))
            turns += 1
            expected = entry.get("expect")
            if expected is not None and outcome.status != expected:
                raise BrainError(
                    f"scripted step {turns} ({tool}): expected status {expected!r}, "
                    f"got {outcome.status!r}: {outcome.text[:300]}"
                )
        return BrainInfo(backend=self.backend, model=self.model, turns=turns)
