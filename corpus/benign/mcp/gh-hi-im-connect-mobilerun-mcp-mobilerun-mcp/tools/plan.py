"""Plan ledger, honest finish, usage guide and web search."""

from __future__ import annotations

import httpx
from fastmcp import FastMCP

from .. import guide as guide_mod
from ..conditions import find_text
from ..errors import fail
from ..session import Runtime
from ..websearch import SearchError, search, tavily_search
from .common import Device, get_session

RESEARCH_MIN_STEPS = 3
VERIFY_GOALS = {"send_message", "send_email", "purchase", "post"}


def register(mcp: FastMCP, rt: Runtime) -> None:
    async def run_search(query: str, limit: int) -> dict:
        try:
            engine, results = await search(query, limit, rt.config.brave_api_key)
        except (httpx.HTTPError, SearchError) as exc:
            fail(
                "unsupported",
                f"web search failed: {exc}",
                "retry shortly, set BRAVE_API_KEY for a reliable engine, or proceed from the screen",
            )
        return {"query": query, "engine": engine, "results": results}

    @mcp.tool(tags={"read"})
    async def web_search(
        query: str, max_results: int | None = None, topic: str = "general", limit: int = 5
    ) -> dict:
        """Search the web for how to do something in an app ('how to <task> in <app> android').
        Returns ranked sources (title, url, snippet) and, with TAVILY_API_KEY set, a synthesized
        answer. max_results 1-10 (default 5); topic general | news. The screen overrules results."""
        count = min(max(max_results or limit, 1), 10)
        if rt.config.tavily_api_key:
            try:
                return {
                    "query": query,
                    **await tavily_search(query, count, topic, rt.config.tavily_api_key),
                }
            except (httpx.HTTPError, SearchError):
                pass  # fall back to the keyless engines
        return await run_search(query, count)

    @mcp.tool(tags={"write"})
    async def set_plan(
        steps: list[str],
        goal: str = "",
        deliverable: str = "",
        target_count: int = 0,
        search_query: str | None = None,
        device: Device = None,
    ) -> dict:
        """Start a plan checklist. target_count > 0 means 'N items must be recorded' before
        end_session(success) is allowed. With 3+ steps and a search_query, the first web search
        rides along in the reply."""
        session = get_session(rt, device)
        session.ledger.set_plan(steps, goal, deliverable, target_count)
        result = {"ok": True, "ledger": session.ledger.to_dict()}
        if search_query and len(steps) >= RESEARCH_MIN_STEPS:
            try:
                result["research"] = await run_search(search_query, 5)
            except Exception as exc:
                result["research_error"] = str(exc)
        return result

    @mcp.tool(tags={"write"})
    async def mark_step(index: int, status: str, note: str = "", device: Device = None) -> dict:
        """Update a plan step: pending | in_progress | done | skipped | failed. Put facts you read
        off the screen in note; the pixels are gone next turn."""
        session = get_session(rt, device)
        try:
            step = session.ledger.mark_step(index, status, note)
        except (ValueError, IndexError) as exc:
            fail("invalid_argument", str(exc))
        return {
            "ok": True,
            "step": {"index": index, "text": step.text, "status": step.status, "note": step.note},
        }

    @mcp.tool(tags={"write"})
    async def record_finding(item: str, quote: str, device: Device = None) -> dict:
        """Record one item you found. ``quote`` must be copied exactly from the CURRENT screen."""
        session = get_session(rt, device)
        screen = await session.capture()
        if find_text(screen, quote) is None:
            fail(
                "invalid_argument",
                "quote not found on the current screen",
                "copy the text exactly as shown",
            )
        count = session.ledger.record_finding(item, quote)
        return {
            "ok": True,
            "recorded": count,
            "target": session.ledger.target_count,
            "remaining": session.ledger.missing_findings(),
        }

    @mcp.tool(tags={"write"})
    async def end_session(
        reason: str = "agent-end",
        outcome: str = "success",
        goal_type: str | None = None,
        summary: str = "",
        device: Device = None,
    ) -> dict:
        """Mark the end of the task (the server keeps listening; the next call starts fresh).
        reason: short summary of what was done. outcome: success (goal state verified) |
        partial | failure. goal_type: play_media | send_message | send_email | purchase | post |
        open_app | search | navigate | other. For send_message, send_email, purchase and post,
        success is refused unless you looked at the screen (read_screen / perceive_screen) after
        your last action. Success is also refused while fewer findings than the plan's
        target_count are recorded. failure is never refused."""
        outcome = "failed" if outcome == "failure" else outcome
        if outcome not in ("success", "partial", "failed"):
            fail("invalid_argument", "outcome must be success, partial or failure")
        session = get_session(rt, device)
        if (
            outcome == "success"
            and goal_type in VERIFY_GOALS
            and session.last_look_at < session.last_action_at
        ):
            fail(
                "plan_incomplete",
                f"{goal_type} success needs a look at the screen after the last action",
                "call read_screen, confirm the result, then end_session again",
            )
        problem = session.ledger.end(outcome)
        if problem:
            fail("plan_incomplete", problem)
        return {
            "ok": True,
            "outcome": "failure" if outcome == "failed" else outcome,
            "reason": reason,
            "goal_type": goal_type or "other",
            "summary": summary or reason,
            "ledger": session.ledger.to_dict(),
        }

    @mcp.tool(tags={"read"})
    async def get_usage_guide(topic: str | None = None) -> dict:
        """How to use this server well. Topics: overview, shortcuts, text_entry, failures, ledger,
        browser, safety, stop, efficiency, full (AURA's names decision_tree, perception, loop,
        loading, trust, deeplinks, action_plane also work)."""
        return {"topics": [*guide_mod.TOPICS, "full"], "guide": guide_mod.guide(topic)}
