import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Protocol, cast

from mcp.server.fastmcp import Context, FastMCP

from .budget import TokenBudget
from .engine.discussion import run_discussion as run_discussion_engine
from .engine.solo import run_solo_task
from .llm.client import LLMClient
from .persistence.db import open_db
from .registry import AgentProfile, create_profile, get_profile, list_profiles, update_profile
from .router import pick_profile


@asynccontextmanager
async def lifespan(_: FastMCP) -> AsyncIterator[dict[str, Any]]:
    db_path = Path(os.environ.get("API_AGENT_DB", "~/.api_agent_mcp/data.db")).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = await open_db(db_path)
    llm = LLMClient(
        api_key=os.environ.get("API_AGENT_API_KEY", ""),
        base_url=os.environ.get("API_AGENT_BASE_URL", "https://api.openai.com/v1"),
        timeout=float(os.environ.get("API_AGENT_TIMEOUT", "120")),
    )
    try:
        yield {"db": db, "llm": llm}
    finally:
        await llm.aclose()
        await db.close()


mcp = FastMCP("api-agent", lifespan=lifespan)


class LifespanStateContext(Protocol):
    lifespan_context: dict[str, Any]


def _state(ctx: Context) -> dict[str, Any]:
    return cast(LifespanStateContext, ctx.request_context).lifespan_context


@mcp.tool()
async def create_agent(
    ctx: Context,
    name: str,
    system_prompt: str,
    role: str = "general",
    model: str | None = None,
    tags: list[str] | None = None,
    temperature: float = 0.7,
    max_output_tokens: int = 4096,
) -> dict[str, Any]:
    """Create a reusable profile. Provider endpoint and API key are server-wide."""
    if not 0 <= temperature <= 2:
        raise ValueError("temperature must be between 0 and 2")
    if max_output_tokens < 1:
        raise ValueError("max_output_tokens must be positive")
    profile = AgentProfile(
        name=name,
        role=role,
        system_prompt=system_prompt,
        model=model,
        tags=tags or [],
        config={"temperature": temperature, "max_output_tokens": max_output_tokens},
    )
    await create_profile(_state(ctx)["db"], profile)
    return {"created": profile.name, "id": profile.id}


@mcp.tool()
async def update_agent(
    ctx: Context,
    name: str,
    system_prompt: str | None = None,
    role: str | None = None,
    model: str | None = None,
    tags: list[str] | None = None,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
) -> dict[str, Any]:
    """Update fields on an existing profile; omitted fields remain unchanged."""
    if temperature is not None and not 0 <= temperature <= 2:
        raise ValueError("temperature must be between 0 and 2")
    if max_output_tokens is not None and max_output_tokens < 1:
        raise ValueError("max_output_tokens must be positive")
    db = _state(ctx)["db"]
    profile = await get_profile(db, name)
    if profile is None:
        return {"error": f"agent {name!r} not found"}
    if system_prompt is not None:
        profile.system_prompt = system_prompt
    if role is not None:
        profile.role = role
    if model is not None:
        profile.model = model
    if tags is not None:
        profile.tags = tags
    if temperature is not None:
        profile.config["temperature"] = temperature
    if max_output_tokens is not None:
        profile.config["max_output_tokens"] = max_output_tokens
    await update_profile(db, profile)
    return {"updated": profile.name}


@mcp.tool()
async def list_agents(ctx: Context) -> list[dict[str, Any]]:
    """List profiles without exposing system prompts or secrets."""
    profiles = await list_profiles(_state(ctx)["db"])
    return [
        {"name": p.name, "role": p.role, "model": p.model, "tags": p.tags, "config": p.config}
        for p in profiles
    ]


@mcp.tool()
async def run_solo(
    ctx: Context,
    task: str,
    agent: str | None = None,
    max_output_tokens: int = 4096,
) -> dict[str, Any]:
    """Run one agent by name or route by a unique matching tag.

    `max_output_tokens` caps generated output, not total input+output usage.
    """
    if not task.strip():
        raise ValueError("task cannot be empty")
    if max_output_tokens < 1:
        raise ValueError("max_output_tokens must be positive")
    state = _state(ctx)
    db = state["db"]
    if agent:
        profile = await get_profile(db, agent)
        if profile is None:
            return {"error": f"agent {agent!r} not found"}
    else:
        profile = pick_profile(task, await list_profiles(db))
    if profile is None:
        return {
            "error": "could not select a unique agent; pass agent explicitly or add matching tags",
        }
    limit = min(max_output_tokens, int(profile.config.get("max_output_tokens", max_output_tokens)))
    return await run_solo_task(
        state["llm"],
        db,
        profile,
        task,
        TokenBudget(max_tokens=limit),
        default_model=os.environ.get("API_AGENT_MODEL", "gpt-4o-mini"),
    )


@mcp.tool()
async def run_discussion(
    ctx: Context,
    task: str,
    agents: list[str],
    judge: str | None = None,
    max_rounds: int = 2,
    max_output_tokens: int = 8192,
) -> dict[str, Any]:
    """Run a bounded multi-agent discussion with an independent judge.

    Provide at least two participant names. `judge` may be omitted when a
    profile with role `judge` exists. The token limit applies to generated
    completion tokens across the entire discussion.
    """
    if not task.strip():
        raise ValueError("task cannot be empty")
    if not 1 <= max_rounds <= 5:
        raise ValueError("max_rounds must be between 1 and 5")
    if not 64 <= max_output_tokens <= 100_000:
        raise ValueError("max_output_tokens must be between 64 and 100000")
    if len({name.casefold() for name in agents}) != len(agents):
        return {"error": "participant agent names must be unique"}
    db = _state(ctx)["db"]
    profiles: list[AgentProfile] = []
    for name in agents:
        profile = await get_profile(db, name)
        if profile is None:
            return {"error": f"participant agent {name!r} not found"}
        profiles.append(profile)

    if judge:
        judge_profile = await get_profile(db, judge)
        if judge_profile is None:
            return {"error": f"judge agent {judge!r} not found"}
    else:
        all_profiles = await list_profiles(db)
        judge_profile = next((p for p in all_profiles if p.role.casefold() == "judge"), None)
        if judge_profile is None:
            return {"error": "specify judge or register a profile with role='judge'"}

    progress_index = 0

    async def report(message: str) -> None:
        nonlocal progress_index
        progress_index += 1
        await ctx.report_progress(progress_index, message=message)

    return await run_discussion_engine(
        _state(ctx)["llm"],
        db,
        profiles,
        task,
        TokenBudget(max_tokens=max_output_tokens),
        max_rounds=max_rounds,
        judge=judge_profile,
        default_model=os.environ.get("API_AGENT_MODEL", "gpt-4o-mini"),
        progress=report,
    )


@mcp.resource("agent://profiles/{name}")
async def agent_profile_resource(name: str, ctx: Context) -> str:
    """Read a profile resource without exposing provider credentials."""
    profile = await get_profile(_state(ctx)["db"], name)
    if profile is None:
        return json.dumps({"error": f"agent {name!r} not found"})
    return profile.model_dump_json()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
