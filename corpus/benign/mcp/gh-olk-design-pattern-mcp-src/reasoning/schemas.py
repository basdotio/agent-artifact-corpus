"""
Reasoning wire schemas: the draft the ThoughtGenerator LLM produces per step
and the tool call contracts for the two reasoning MCP servers.

A draft is authored by THIS server's LLM; the reasoning tools only structure
it (phases, numbering, uncertainty bookkeeping). Tool wire shapes are fixed
by the npm packages (camelCase for shannonthinking, snake_case for
code-reasoning); the ``*_params`` helpers in this module build those payloads.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.reasoning.config import ReasoningTool


class ThoughtDraft(BaseModel):
    """One authored reasoning step before submission to a reasoning tool.

    ``phase_tag`` is normalized against PHASE_TAGS (shannonthinking's enum);
    see tools._coerce_shannon_stage for the alias map.
    """

    model_config = ConfigDict(extra="ignore")

    thought: str = Field(..., min_length=1)
    phase_tag: str = Field(...)
    assumptions: list[str] = Field(default_factory=list)
    uncertainty: float | None = Field(default=None, ge=0.0, le=1.0)

    @field_validator("phase_tag")
    @classmethod
    def _normalize_tag(cls, v: str) -> str:
        return v.strip().lower()


class ReasoningStep(BaseModel):
    """One completed tool round-trip recorded in the trace."""

    model_config = ConfigDict(extra="ignore")

    tool: str
    thought: str
    phase_tag: str
    tool_output: str = Field(default="")
    revised: bool = False
    duration_ms: int = Field(default=0, ge=0)


class ReasoningTrace(BaseModel):
    """Aggregated outcome of one pre-LLM reasoning phase call."""

    model_config = ConfigDict(extra="ignore")

    phase: str
    steps: list[ReasoningStep] = Field(default_factory=list)
    degraded: bool = False
    degradation_reason: str | None = None
    total_duration_ms: int = Field(default=0, ge=0)

    @property
    def summary(self) -> str:
        """Flat step render used in pipeline logging and user-facing traces."""
        return _render_steps(self.steps)


def _render_steps(steps: list[ReasoningStep]) -> str:
    lines: list[str] = []
    for i, step in enumerate(steps, 1):
        marker = "*" if step.revised else ">"
        lines.append(f"{i}. [{step.tool}/{step.phase_tag}] {marker} {step.thought}")
    return "\n".join(lines)


class ToolContract(BaseModel):
    """Frozen call shape of one reasoning MCP tool (see tools.py)."""

    model_config = ConfigDict(frozen=True)

    name: str
    thought_param: str
    number_param: str
    total_param: str
    next_param: str
    phase_param: str | None = None
    max_thought_length: int | None = None


# tool name and param spellings are the npm packages' wire contract (0.1.1 /
# 0.8.1); they change only with a server version bump.
SHANNON_TOOL = ToolContract(
    name="shannonthinking",
    thought_param="thought",
    number_param="thoughtNumber",
    total_param="totalThoughts",
    next_param="nextThoughtNeeded",
    phase_param="thoughtType",
    max_thought_length=None,
)
CODE_TOOL = ToolContract(
    name="code-reasoning",
    thought_param="thought",
    number_param="thought_number",
    total_param="total_thoughts",
    next_param="next_thought_needed",
    phase_param=None,
    max_thought_length=20000,
)
#: Config vocabulary (``ReasoningTool``) -> contract. Two names exist per tool and
#: they are NOT interchangeable: a strategy's ``tools`` list holds the config key
#: (``"shannon"`` / ``"code"``, ``ReasoningStrategy.tools: list[ReasoningTool]``)
#: while the MCP servers expose the wire names carried in ``ToolContract.name``
#: (``"shannonthinking"`` / ``"code-reasoning"``). Keying this map by the wire name
#: made every strategy lookup raise ``KeyError('code')`` — and because the
#: reasoning layer degrades silently per call, that surfaced only as an empty
#: trace with ``degradation_reason == "'code'"``.
TOOL_CONTRACTS: dict[ReasoningTool, ToolContract] = {
    "shannon": SHANNON_TOOL,
    "code": CODE_TOOL,
}


def draft_to_shannon_params(
    draft: ThoughtDraft, number: int, total: int, next_needed: bool = True
) -> dict[str, object]:
    """Build the shannonthinking camelCase payload (includes its enum'd phase)."""
    payload: dict[str, object] = {
        "thought": draft.thought,
        "thoughtType": draft.phase_tag,
        "thoughtNumber": number,
        "totalThoughts": total,
        "uncertainty": draft.uncertainty if draft.uncertainty is not None else 0.0,
        "dependencies": [],
        "assumptions": draft.assumptions,
        "nextThoughtNeeded": next_needed,
    }
    return payload


def draft_to_code_params(
    draft: ThoughtDraft, number: int, total: int, next_needed: bool = True
) -> dict[str, object]:
    """Build the code-reasoning snake_case payload (truncated at 20k chars)."""
    thought = draft.thought
    max_len = CODE_TOOL.max_thought_length
    if max_len is not None and len(thought) > max_len:
        thought = thought[:max_len]
    payload: dict[str, object] = {
        "thought": thought,
        "thought_number": number,
        "total_thoughts": total,
        "next_thought_needed": next_needed,
        "dependencies": [],
        "assumptions": draft.assumptions,
    }
    return payload


def draft_to_params(
    draft: ThoughtDraft,
    contract: ToolContract,
    number: int,
    total: int,
    next_needed: bool = True,
) -> dict[str, object]:
    """Dispatch on the tool name recorded in the contract."""
    if contract.name == SHANNON_TOOL.name:
        return draft_to_shannon_params(draft, number, total, next_needed)
    if contract.name == CODE_TOOL.name:
        return draft_to_code_params(draft, number, total, next_needed)
    raise ValueError(f"unknown reasoning tool contract: {contract.name}")
