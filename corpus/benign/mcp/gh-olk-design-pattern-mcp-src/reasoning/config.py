"""
Reasoning configuration for the server-side shannonthinking / code-reasoning
integration.

The design-pattern-mcp server acts as an MCP CLIENT of two structured
reasoning scratchpads before each LLM phase call:

  - shannonthinking  (npm: server-shannon-thinking@0.1.1, tool "shannonthinking",
    camelCase params)
  - code-reasoning   (npm: @mettamatt/code-reasoning@0.8.1, tool "code-reasoning",
    snake_case params)

Both tools are scratchpads, not reasoning engines: a caller must AUTHOR each
thought. The ReasoningClient's ThoughtGenerator loop does that with this
server's own LLM (see client.py), then submits each thought to the tool for
structuring.

Docker deployments embed both packages at /usr/local/lib/node_modules and
invoke them directly via ``node <pkg>/dist/index.js``. Outside Docker, an
auto-fallback to ``npx -y <pkg>`` kicks in when the embedded path is absent
(see client._resolve_cmd).

Env vars are flat, matching the existing EMBEDDER_*/GENERATOR_* convention,
and are wired through config.json {env:...} expansion:

    REASONING_ENABLED                        (default: true)
    REASONING_SHANNONTHINKING_CMD            (JSON list)
    REASONING_CODE_REASONING_CMD             (JSON list)
    REASONING_SPAWN_TIMEOUT_SECONDS          (default: 10)
    REASONING_STEP_TIMEOUT_SECONDS           (default: 20)
    REASONING_MAX_TOTAL_STEPS                (default: 8)
    REASONING_QUIET_STDERR                   (default: true)
    REASONING_FAIL_FAST                      (default: false)
    REASONING_<PHASE>_ENABLED                    (default: true, per phase)
    REASONING_<PHASE>_THOUGHTS                    (default: per phase, see _default_per_phase)

The five pipeline phases carrying a reasoning strategy mirror the guide's
call kinds (§3.1): ``analyze`` (decision-part decomposition, §4-§5),
``weights`` (eight-axis calibration, §7.1), ``generate`` (pattern
applications, §9-§11 item 1), ``evaluate`` (§11 item 2 rubric) and
``retry`` (§11 item 4 reselection plan).
"""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Embedded entry points baked into the production Docker image by the
# build-mcps stage (Dockerfile). Version pins verified on npm
# 2026-08-31: server-shannon-thinking@0.1.1, @mettamatt/code-reasoning@0.8.1.
SHANNON_EMBEDDED_CMD: list[str] = [
    "node",
    "/usr/local/lib/node_modules/server-shannon-thinking/dist/index.js",
]
CODE_REASONING_EMBEDDED_CMD: list[str] = [
    "node",
    "/usr/local/lib/node_modules/@mettamatt/code-reasoning/dist/index.js",
]

SHANNON_NPX_CMD: list[str] = ["npx", "-y", "server-shannon-thinking@0.1.1"]
CODE_REASONING_NPX_CMD: list[str] = ["npx", "-y", "@mettamatt/code-reasoning@0.8.1"]

ReasoningTool = Literal["shannon", "code"]


def _default_tools() -> list[ReasoningTool]:
    return ["shannon", "code"]


class ReasoningStrategy(BaseModel):
    """Per-phase reasoning strategy driving the ThoughtGenerator loop."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=True,
        description=(
            "Master switch for this phase. A disabled phase contributes an empty "
            "reasoning context: no generator call, no reasoning subprocess, no cache entry."
        ),
    )


    pre_llm_thoughts: int = Field(
        default=3, ge=1, le=20,
        description="Maximum reasoning steps before the phase's main LLM call.",
    )
    tools: list[ReasoningTool] = Field(
        default_factory=_default_tools,
        description=(
            "Reasoning tools used for this phase. Each thought is submitted to "
            "every listed tool in order (the tools alternate per step when more "
            "than one is configured)."
        ),
    )
    step_agenda: list[str] = Field(
        default_factory=list,
        description=(
            "Per-step focus prompts (one per thought). When shorter than "
            "pre_llm_thoughts, the last agenda item repeats for the remaining "
            "steps. This is the external-trace counterpart of the degraded "
            "in-prompt thinking scaffold."
        ),
    )
    system_directive: str = Field(
        default="",
        description="Phase-level directive prepended to every step prompt.",
    )

    @field_validator("tools")
    @classmethod
    def _non_empty_tools(cls, v: list[ReasoningTool]) -> list[ReasoningTool]:
        if not v:
            raise ValueError("tools must contain at least one reasoning tool")
        return v


def _default_per_phase() -> dict[str, ReasoningStrategy]:
    return {
        "analyze": ReasoningStrategy(
            pre_llm_thoughts=2,
            tools=["shannon", "code"],
            step_agenda=[
                (
                    "Quote each implementable decision in the description verbatim, name "
                    "the component or flow that owns it, and classify it into one catalog "
                    "category hypothesis with its scope (function, module, or system)."
                ),
                (
                    "Verify: is every decision owned by exactly one part, does the "
                    "decomposition cover the whole description, and which quality axes "
                    "(testability, extensibility, maintainability, simplicity, performance, "
                    "reliability, security, scalability) does each part signal? State the "
                    "final part list."
                ),
            ],
            system_directive=(
                "You are preparing a decision-part decomposition. Reason only from "
                "evidence in the description text; quote fragments verbatim; never "
                "invent components, flows, or constraints absent from the text."
            ),
        ),
        "weights": ReasoningStrategy(
            pre_llm_thoughts=2,
            tools=["shannon", "code"],
            step_agenda=[
                (
                    "List every fragment of the part statement and constraints that "
                    "signals one of the eight axes, name that axis, and anchor it on the "
                    "0.0-1.0 calibration scale (0.0 excluded, 0.1-0.2 unmentioned, 0.3-0.5 "
                    "passing mention, 0.6-0.8 concrete target, 0.9-1.0 non-negotiable); "
                    "numeric SLOs outrank vague adjectives."
                ),
                (
                    "Resolve conflicts between anchors, reserve 1.0 for at most one or "
                    "two axes, then state the final eight weights normalized so the "
                    "maximum is 1.0."
                ),
            ],
            system_directive=(
                "You are preparing a weight calibration for one decision part. Every "
                "weight must trace to a phrase actually present in the part or brief "
                "constraints; unmentioned axes stay at 0.1-0.2."
            ),
        ),
        "generate": ReasoningStrategy(
            pre_llm_thoughts=2,
            tools=["shannon", "code"],
            step_agenda=[
                (
                    "Restate each decision part's problem in the vocabulary of its "
                    "selected pattern, check the pattern's intent covers it, then map "
                    "every participant role onto a concrete entity from the brief "
                    "(component, store, or interface) and sketch the interactions "
                    "between applications."
                ),
                (
                    "Verify: does every application trace to a decision part, and does "
                    "the effective language have an implementation entry for each bound "
                    "pattern? State open gaps."
                ),
            ],
            system_directive=(
                "You are preparing a pattern-application plan. Every claim must trace "
                "to a selected pattern's documented intent and the brief's components; "
                "never invent catalog facts."
            ),
        ),
        "evaluate": ReasoningStrategy(
            pre_llm_thoughts=2,
            tools=["shannon", "code"],
            step_agenda=[
                (
                    "Enumerate which applications demonstrably satisfy their part's "
                    "weighted axes and which do not (citing application ids); check "
                    "cross-application consistency: no duplicated decision ownership, no "
                    "conflicting pattern pair, every supporting role traceable to a stated "
                    "constraint."
                ),
                (
                    "Score the design against the weighted-axes rubric and flag "
                    "selection defects (primary does not own the decision, unsolved "
                    "supporting constraint, conflicting pair) separately from quality "
                    "weaknesses."
                ),
            ],
            system_directive=(
                "You are preparing a design audit against the eight-axis rubric as "
                "weighted by the part weights. A part weighted for simplicity must not "
                "be penalized for lacking extensibility; no floating assertions."
            ),
        ),
    }


class ReasoningConfig(BaseModel):
    """Server-side reasoning MCP integration configuration.

    enabled defaults to True (opt-out): Docker images embed the reasoning
    MCP packages at build time, so the feature is self-contained there.
    Outside Docker the client auto-falls back to npx per tool.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=True,
        description="Master switch. Opt out via REASONING_ENABLED=false.",
    )
    shannonthinking_cmd: str | list[str] = Field(
        default_factory=lambda: list(SHANNON_EMBEDDED_CMD),
        description=(
            "Command list for the shannonthinking MCP server (stdio). Defaults to "
            "the Docker-embedded entry point; set to a JSON list to override "
            "(e.g. '[\"npx\", \"-y\", \"server-shannon-thinking@latest\"]')."
        ),
    )
    code_reasoning_cmd: str | list[str] = Field(
        default_factory=lambda: list(CODE_REASONING_EMBEDDED_CMD),
        description=(
            "Command list for the code-reasoning MCP server (stdio). Defaults to "
            "the Docker-embedded entry point; set to a JSON list to override."
        ),
    )
    spawn_timeout_seconds: float = Field(default=10.0, gt=0)
    step_timeout_seconds: float = Field(default=20.0, gt=0)
    max_total_steps: int = Field(default=8, ge=1, le=20)
    quiet_stderr: bool = Field(
        default=True,
        description=(
            "Route reasoning-subprocess stderr to os.devnull. The shannonthinking "
            "server prints large ASCII progress boxes and code-reasoning prints "
            "[info] startup lines on stderr — silencing them keeps docker logs "
            "clean. Tool responses remain captured in the reasoning trace; set "
            "false (REASONING_QUIET_STDERR=false) to see subprocess stderr for "
            "debugging (e.g. a Node stack trace on spawn failure)."
        ),
    )
    fail_fast: bool = Field(
        default=False,
        description=(
            "If True, server startup FAILS when a reasoning tool is unreachable. "
            "Default False: startup logs a loud ERROR and degrades to the "
            "in-prompt thinking scaffold."
        ),
    )
    per_phase: dict[str, ReasoningStrategy] = Field(default_factory=_default_per_phase)
    max_injected_chars: int | None = Field(
        default=None, ge=1,
        description=(
            "Cap on the rendered reasoning trace injected into downstream prompts "
            "(REASONING_MAX_INJECTED_CHARS). None (shipped default) = uncapped; a positive "
            "value truncates the rendered context and appends '(reasoning trace truncated at "
            "N chars)'. Per-step thoughts inside the trace stay untruncated. Latency lever: "
            "cuts input tokens on every downstream call."
        ),
    )

    @field_validator("max_injected_chars", mode="before")
    @classmethod
    def _parse_max_injected_chars(cls, v: object) -> object:
        # Empty string = env var unset ({env:REASONING_MAX_INJECTED_CHARS:-}) → None (uncapped).
        if isinstance(v, str):
            if not v.strip():
                return None
            return int(v)
        return v

    @model_validator(mode="before")
    @classmethod
    def _merge_per_phase_defaults(cls, data: object) -> object:
        """Overlay partial per-phase overrides on the shipped defaults.

        A JSON config may name only the keys it changes (typically ``enabled``,
        ``pre_llm_thoughts`` and ``tools``); the agenda and directive stay the
        shipped ones instead of silently resetting to empty. Unknown nested keys
        still fail: ``ReasoningStrategy`` forbids extras.
        """
        if not isinstance(data, dict):
            return data
        per_phase = data.get("per_phase")
        if not isinstance(per_phase, dict):
            return data
        defaults = _default_per_phase()
        merged: dict[str, object] = {}
        for phase, override in per_phase.items():
            default = defaults.get(phase)
            if default is None or not isinstance(override, dict):
                merged[phase] = override
                continue
            merged[phase] = {**default.model_dump(), **override}
        return {**data, "per_phase": merged}


    @field_validator("shannonthinking_cmd", "code_reasoning_cmd", mode="before")
    @classmethod
    def _parse_cmd(cls, v: object, info: object) -> object:
        # Empty string = env var unset ({env:REASONING_*_CMD:-}) → embedded default.
        if isinstance(v, str):
            if not v.strip():
                return list(
                    SHANNON_EMBEDDED_CMD
                    if getattr(info, "field_name", "") == "shannonthinking_cmd"
                    else CODE_REASONING_EMBEDDED_CMD
                )
            return json.loads(v)
        return v

    @field_validator("shannonthinking_cmd", "code_reasoning_cmd")
    @classmethod
    def _validate_cmd(cls, v: list[str]) -> list[str]:
        if not v or not all(isinstance(part, str) and part for part in v):
            raise ValueError("reasoning command must be a non-empty list of strings")
        return v

    def get_strategy(self, phase: str) -> ReasoningStrategy:
        """Return the strategy for a phase, falling back to the first entry."""
        strategy = self.per_phase.get(phase)
        if strategy is not None:
            return strategy
        return next(iter(self.per_phase.values()))

    def active_tools(self) -> list[ReasoningTool]:
        """Tools used by the enabled phases, in first-seen order, deduplicated.

        ``health_check`` probes exactly this set: narrowing a phase's tool list
        must not make startup require the server that phase no longer uses.
        """
        tools: list[ReasoningTool] = []
        for strategy in self.per_phase.values():
            if not strategy.enabled:
                continue
            for tool in strategy.tools:
                if tool not in tools:
                    tools.append(tool)
        return tools
