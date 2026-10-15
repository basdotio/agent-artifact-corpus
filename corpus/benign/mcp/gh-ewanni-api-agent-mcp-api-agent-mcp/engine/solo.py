import uuid
from typing import Any, Protocol

from ..budget import TokenBudget
from ..persistence.events import append_event
from ..registry import AgentProfile


class ChatClient(Protocol):
    async def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int,
        json_mode: bool = False,
        json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


async def run_solo_task(
    client: ChatClient,
    db: Any,
    profile: AgentProfile,
    task: str,
    budget: TokenBudget,
    *,
    default_model: str,
) -> dict[str, Any]:
    session_id = uuid.uuid4().hex
    model = profile.model or default_model
    await append_event(
        db,
        session_id,
        "session_started",
        {"mode": "solo", "agent": profile.name, "model": model, "task": task},
    )

    try:
        response = await client.chat(
            model=model,
            messages=[
                {"role": "system", "content": profile.system_prompt},
                {"role": "user", "content": task},
            ],
            temperature=float(profile.config.get("temperature", 0.7)),
            max_tokens=budget.max_tokens,
        )
        usage = response.get("usage", {})
        output_tokens = int(usage.get("completion_tokens", 0))
        budget.charge(output_tokens)
        result = {
            "session_id": session_id,
            "agent": profile.name,
            "model": model,
            "result": response["content"],
            "usage": usage,
            "budget_exhausted": budget.exhausted,
        }
        await append_event(db, session_id, "agent_response", result)
        return result
    except Exception as exc:
        await append_event(
            db,
            session_id,
            "session_failed",
            {"error_type": type(exc).__name__, "error": str(exc)},
        )
        raise
