"""
Prompt construction for the ThoughtGenerator (the LLM that authors thoughts
before the reasoning tools structure them).

Separate module per APM structure; content re-authored for the design-pattern
pipeline's five phases.
"""

from __future__ import annotations

from src.reasoning.schemas import ReasoningTrace

REASONING_STEP_SYSTEM_PROMPT = """\
You are the reasoning driver for a design-pattern selection pipeline.
Your job: produce ONE thinking step that grounds a downstream \
design-pattern-phase LLM call.

The caller parses your reply as a JSON object, so return exactly that object \
with these keys — "thought" is required and must be non-empty:
- "thought": the step text, one focused paragraph.
- "phase_tag": the reasoning stage this step belongs to — one of \
problem_definition, constraints, model, proof, implementation. Never use a \
pipeline phase name (analyze, weights, generate, evaluate, retry) here.
- "assumptions": the explicit assumptions this step rests on (list of strings; \
may be empty).
- "uncertainty": how much this step is guesswork, a number in [0.0, 1.0] \
(0.0 = the evidence settles it, 1.0 = pure conjecture).

Rules:
- Ground every statement in the supplied context (description, brief, part, \
patterns, prior evaluation). Never invent catalog patterns, qualities, or \
constraints.
- Be concise: one focused paragraph per step. No preamble, no meta commentary.
- Prefer quoting or tightly paraphrasing evidence over generalizing.
- If evidence conflicts, surface the conflict instead of silently resolving it.
- Reply with the JSON object only — no prose, no code fences, no commentary.
"""


def build_step_user_prompt(
    *,
    phase: str,
    step_number: int,
    total_steps: int,
    agenda: str,
    system_directive: str,
    context: str,
) -> str:
    """Compose the per-step user prompt."""
    parts: list[str] = [
        f"## Reasoning phase: {phase}",
        f"Step {step_number} of {total_steps}",
    ]
    if system_directive:
        parts.append(f"## Phase directive\n{system_directive}")
    parts.append(f"## This step's focus\n{agenda}")
    parts.append(f"## Context\n{context}")
    parts.append("Write the single thinking step now.")
    return "\n\n".join(parts)


def render_reasoning_context(trace: ReasoningTrace, *, max_chars: int | None = None) -> str:
    """Render completed tool steps for injection into the phase's main call.

    ``max_chars`` (§4 rule 1a knob ``REASONING_MAX_INJECTED_CHARS``): when the rendered context
    exceeds the cap, it is cut at the cap and a truncation marker appended — per-step thoughts
    inside the trace stay whole, only the downstream injection is capped. ``None`` = uncapped.
    """
    if not trace.steps:
        return ""
    lines: list[str] = ["Structured reasoning steps:"]
    for i, step in enumerate(trace.steps, 1):
        lines.append(f"{i}. [{step.tool}/{step.phase_tag}] {step.thought}")
        if step.tool_output:
            lines.append(f"   tool: {step.tool_output}")
    rendered = "\n".join(lines)
    if max_chars is not None and max_chars >= 1 and len(rendered) > max_chars:
        return rendered[:max_chars] + f"\n(reasoning trace truncated at {max_chars} chars)"
    return rendered


def render_degraded_context(trace: ReasoningTrace) -> str:
    """Render the degraded-mode context (reasoning unavailable)."""
    reason = trace.degradation_reason or "reasoning tools unavailable"
    lines: list[str] = [
        (
            "Structured reasoning was unavailable for this phase; the step summaries "
            f"below come from the in-prompt scaffold ({reason})."
        ),
    ]
    if trace.steps:
        lines.append(trace.summary)
    return "\n".join(lines)


_PHASE_GUIDANCE: dict[str, str] = {
    "analyze": (
        "Decompose strictly along the trace's part boundaries; classify every "
        "quoted fragment as reasoned in the trace."
    ),
    "weights": (
        "Calibrate each of the eight axes to the anchors the trace resolved; "
        "numeric SLO evidence outranks adjectives exactly as reasoned."
    ),
    "generate": (
        "Commit to the participant mappings the trace sketched; justify every "
        "application in overview.reasoning as grounded in the trace."
    ),
    "evaluate": (
        "Flag the ambiguities and near-ties the trace raised as explicit "
        "findings; apply the trace's defect/weakness separation."
    ),
    "retry": (
        "Address the trace's most critical sub-problem first; keep the "
        "strengths the trace verified intact."
    ),
}

_DEGRADED_SCAFFOLD: dict[str, str] = {
    "analyze": (
        "quote each implementable decision verbatim → classify per catalog "
        "category → resolve conflicts by evidence strength → verify single "
        "decision ownership"
    ),
    "weights": (
        "quote the axis-signaling fragments → calibrate against the 0.0-1.0 "
        "anchors → let numeric SLOs dominate → max-normalize → verify the peak "
        "axis is the part's dominant concern"
    ),
    "generate": (
        "restate each part in its pattern's vocabulary → map participant roles "
        "to concrete entities → check language bindings → verify traceability"
    ),
    "evaluate": (
        "enumerate per-part axis satisfaction → check cross-application "
        "consistency → score against the weighted rubric → separate selection "
        "defects from quality weaknesses"
    ),
    "retry": (
        "identify the most critical selection defect → promote the next-ranked "
        "candidate with the exclusion sticky → preserve praised strengths"
    ),
}

_UNKNOWN_SCAFFOLD = (
    "state the phase goal → gather the relevant evidence → decide → verify "
    "against the constraints"
)

_CACHEABLE_PHASES = frozenset({"analyze", "generate"})
_CACHE_MAX_ENTRIES = 64


def phase_guidance(phase: str) -> str:
    """Binding guidance injected into the phase's main system prompt."""
    return _PHASE_GUIDANCE.get(phase, "")


def degraded_scaffold(phase: str) -> str:
    """Arrow-chained thinking scaffold used when tools are unavailable."""
    return _DEGRADED_SCAFFOLD.get(phase, _UNKNOWN_SCAFFOLD)


def cacheable(phase: str) -> bool:
    """Whether a phase's reasoning trace is cacheable (pure decomposition / \
planning over immutable inputs)."""
    return phase in _CACHEABLE_PHASES
