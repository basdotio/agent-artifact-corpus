import asyncio
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from pydantic import ValidationError

from ..budget import TokenBudget
from ..llm.schemas import Critique, Proposal, Verdict
from ..persistence.events import append_event
from ..registry import AgentProfile
from .blackboard import BlackboardState
from .solo import ChatClient

ProgressCallback = Callable[[str], Awaitable[None]]
MAX_PARTICIPANTS = 5
MAX_ROUNDS = 5
MAX_OUTPUT_PER_CALL = 1024


async def _notify(progress: ProgressCallback | None, message: str) -> None:
    if progress is not None:
        await progress(message)


def _parse_model_json(content: str, schema: type[Any]) -> Any:
    text = content.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```")
        text = text.removesuffix("```").strip()
    try:
        return schema.model_validate_json(text)
    except (ValidationError, ValueError) as exc:
        raise ValueError(f"model returned invalid {schema.__name__} JSON: {exc}") from exc


def _call_cap(budget: TokenBudget, participants: int, rounds: int) -> int:
    max_calls = participants * (2 * rounds) + rounds
    return min(MAX_OUTPUT_PER_CALL, max(1, budget.max_tokens // max_calls))


async def _agent_json_call(
    client: ChatClient,
    db: Any,
    budget: TokenBudget,
    session_id: str,
    profile: AgentProfile,
    *,
    phase: str,
    instruction: str,
    input_text: str,
    schema: type[Any],
    default_model: str,
    max_output_tokens: int,
) -> Any:
    reservation = budget.reserve(
        min(max_output_tokens, int(profile.config.get("max_output_tokens", max_output_tokens)))
    )
    settled = False
    model = profile.model or default_model
    try:
        response = await client.chat(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Agent name: {profile.name}. Role: {profile.role}.\n\n"
                        f"{profile.system_prompt}\n\n{instruction}"
                    ),
                },
                {"role": "user", "content": input_text},
            ],
            temperature=float(profile.config.get("temperature", 0.3)),
            max_tokens=reservation,
            json_schema=schema.model_json_schema(),
        )
        usage = response.get("usage", {})
        actual_tokens = usage.get("completion_tokens")
        budget.settle(reservation, int(actual_tokens) if actual_tokens is not None else None)
        settled = True
        result = _parse_model_json(response["content"], schema)
        if isinstance(result, (Proposal, Critique)):
            result.agent = profile.name
        await append_event(
            db,
            session_id,
            "agent_step",
            {
                "phase": phase,
                "agent": profile.name,
                "model": model,
                "completion_tokens": actual_tokens,
                "result": result.model_dump(),
            },
        )
        return result
    except BaseException:
        if not settled:
            budget.settle(reservation, None)
        raise


async def _gather_agents(
    client: ChatClient,
    db: Any,
    budget: TokenBudget,
    session_id: str,
    profiles: list[AgentProfile],
    *,
    phase: str,
    instruction: str,
    input_text: str,
    schema: type[Any],
    max_output_tokens: int,
    default_model: str,
) -> tuple[list[Any], list[dict[str, str]]]:
    async def run(profile: AgentProfile) -> tuple[AgentProfile, Any | None, Exception | None]:
        try:
            result = await _agent_json_call(
                client,
                db,
                budget,
                session_id,
                profile,
                phase=phase,
                instruction=instruction,
                input_text=input_text,
                schema=schema,
                max_output_tokens=max_output_tokens,
                default_model=default_model,
            )
            return profile, result, None
        except (httpx.HTTPError, TimeoutError, RuntimeError, ValueError) as exc:
            await append_event(
                db,
                session_id,
                "agent_step_failed",
                {
                    "phase": phase,
                    "agent": profile.name,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            return profile, None, exc

    outcomes = await asyncio.gather(*(run(profile) for profile in profiles))
    results = [result for _, result, error in outcomes if error is None and result is not None]
    failures = [
        {"agent": profile.name, "error": str(error)}
        for profile, _, error in outcomes
        if error is not None
    ]
    return results, failures


def _fallback_verdict(state: BlackboardState, reason: str) -> Verdict:
    candidate = max(state.current_proposals, key=lambda proposal: len(proposal.content))
    return Verdict(
        verdict="no_consensus",
        confidence=0.0,
        winner=candidate.agent,
        final_answer=candidate.content,
        unresolved=[reason],
        rationale="Returning the best available proposal because the judge did not produce a valid verdict.",
    )


async def run_discussion(
    client: ChatClient,
    db: Any,
    profiles: list[AgentProfile],
    task: str,
    budget: TokenBudget,
    *,
    max_rounds: int = 2,
    judge: AgentProfile | None = None,
    default_model: str = "gpt-4o-mini",
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Run independent proposals, parallel critiques, judge, then bounded revision."""
    if not task.strip():
        raise ValueError("task cannot be empty")
    if not 2 <= len(profiles) <= MAX_PARTICIPANTS:
        raise ValueError(f"discussion requires 2 to {MAX_PARTICIPANTS} participant agents")
    if len({profile.name.casefold() for profile in profiles}) != len(profiles):
        raise ValueError("participant agents must be unique")
    if not 1 <= max_rounds <= MAX_ROUNDS:
        raise ValueError(f"max_rounds must be between 1 and {MAX_ROUNDS}")
    if judge is None:
        raise ValueError("an independent judge profile is required")
    if judge.name.casefold() in {profile.name.casefold() for profile in profiles}:
        raise ValueError("judge must be a separate profile, not a discussion participant")
    minimum_calls = len(profiles) * (2 * max_rounds) + max_rounds
    if budget.max_tokens < minimum_calls * 64:
        raise ValueError("output-token budget is too small for the selected participants and rounds")

    session_id = uuid.uuid4().hex
    state = BlackboardState(task=task)
    call_cap = _call_cap(budget, len(profiles), max_rounds)
    await append_event(
        db,
        session_id,
        "session_started",
        {
            "mode": "discussion",
            "task": task,
            "participants": [profile.name for profile in profiles],
            "judge": judge.name,
            "max_rounds": max_rounds,
            "output_token_budget": budget.max_tokens,
        },
    )

    round_number = 0
    step_failures: list[dict[str, str]] = []
    try:
        await _notify(progress, "Independent proposals")
        proposals, proposal_failures = await _gather_agents(
            client,
            db,
            budget,
            session_id,
            profiles,
            phase="propose",
            instruction=(
                "Propose a solution independently without seeing other agents' work. "
                "Return only JSON matching {agent, summary, content}."
            ),
            input_text=task,
            schema=Proposal,
            max_output_tokens=call_cap,
            default_model=default_model,
        )
        state.current_proposals = proposals
        step_failures.extend({"phase": "propose", **failure} for failure in proposal_failures)
        if len(proposals) < 2:
            raise RuntimeError(
                f"fewer than two proposals succeeded ({len(proposals)}); failures: {proposal_failures}"
            )
        await append_event(db, session_id, "blackboard_updated", state.model_dump())

        final_verdict: Verdict | None = None
        for round_number in range(1, max_rounds + 1):
            await _notify(progress, f"Round {round_number}: critique")
            critiques, critique_failures = await _gather_agents(
                client,
                db,
                budget,
                session_id,
                profiles,
                phase=f"critique_{round_number}",
                instruction=(
                    "Independently critique all proposals. Be specific, test assumptions, and do not agree "
                    "without reasons. Return only JSON matching {agent, strengths, concerns, questions}."
                ),
                input_text=state.render(),
                schema=Critique,
                max_output_tokens=call_cap,
                default_model=default_model,
            )
            state.critiques = critiques
            step_failures.extend(
                {"phase": f"critique_{round_number}", **failure} for failure in critique_failures
            )
            await append_event(
                db,
                session_id,
                "blackboard_updated",
                {"round": round_number, **state.model_dump()},
            )

            await _notify(progress, f"Round {round_number}: judge verdict")
            try:
                final_verdict = await _agent_json_call(
                    client,
                    db,
                    budget,
                    session_id,
                    judge,
                    phase=f"judge_{round_number}",
                    instruction=(
                        "Judge independently. Return JSON matching {verdict, confidence, winner, "
                        "final_answer, unresolved, rationale}. Use verdict='consensus' only when "
                        "the proposals support a defensible shared answer; otherwise use 'no_consensus'. "
                        "Always provide your best final_answer."
                    ),
                    input_text=state.render(),
                    schema=Verdict,
                    max_output_tokens=call_cap,
                    default_model=default_model,
                )
            except (httpx.HTTPError, TimeoutError, RuntimeError, ValueError) as exc:
                step_failures.append(
                    {"phase": f"judge_{round_number}", "agent": judge.name, "error": str(exc)}
                )
                await append_event(
                    db,
                    session_id,
                    "judge_step_failed",
                    {"round": round_number, "error_type": type(exc).__name__, "error": str(exc)},
                )
                final_verdict = _fallback_verdict(state, "Judge did not return a valid verdict.")
                break

            if final_verdict is None:
                raise RuntimeError("judge did not return a verdict")
            verdict = final_verdict
            if verdict.verdict == "consensus" or round_number == max_rounds:
                break

            await _notify(progress, f"Round {round_number}: revision")
            state.round_summaries.append(
                f"Judge: {verdict.rationale}; unresolved: {verdict.unresolved}"
            )
            revised, revision_failures = await _gather_agents(
                client,
                db,
                budget,
                session_id,
                profiles,
                phase=f"revise_{round_number}",
                instruction=(
                    "Revise your own proposal in response to the critiques. Keep it if still best; "
                    "address valid concerns. Return only JSON matching {agent, summary, content}."
                ),
                input_text=state.render(),
                schema=Proposal,
                max_output_tokens=call_cap,
                default_model=default_model,
            )
            step_failures.extend(
                {"phase": f"revise_{round_number}", **failure} for failure in revision_failures
            )
            if revised:
                revised_by_name = {proposal.agent.casefold(): proposal for proposal in revised}
                state.current_proposals = [
                    revised_by_name.get(proposal.agent.casefold(), proposal)
                    for proposal in state.current_proposals
                ]
            state.critiques = []
            await append_event(
                db,
                session_id,
                "revision_complete",
                {"round": round_number, "revision_failures": revision_failures},
            )

        if final_verdict is None:
            raise RuntimeError("discussion ended without a judge verdict")
        result = {
            "session_id": session_id,
            "mode": "discussion",
            "verdict": final_verdict.model_dump(),
            "proposals": [proposal.model_dump() for proposal in state.current_proposals],
            "critiques": [critique.model_dump() for critique in state.critiques],
            "rounds_completed": round_number,
            "output_tokens_used": budget.used_tokens,
            "output_token_budget": budget.max_tokens,
            "budget_exhausted": budget.exhausted,
            "step_failures": step_failures,
        }
        await append_event(db, session_id, "session_completed", result)
        return result
    except (httpx.HTTPError, TimeoutError, RuntimeError, ValueError) as exc:
        await append_event(
            db,
            session_id,
            "session_failed",
            {"error_type": type(exc).__name__, "error": str(exc)},
        )
        raise
