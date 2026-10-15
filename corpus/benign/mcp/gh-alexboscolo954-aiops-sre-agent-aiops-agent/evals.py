"""Offline evals: run the real agent and a real LLM against recorded tool outputs.

Each scenario (evals/scenarios/*.yaml) holds an alert, the tool results recorded
from a real cluster, and what a correct triage must contain. The MCP servers are
the real ones (same tool names and schemas the model sees in production), but a
replay middleware answers every call from the recording, so no cluster is needed
and runs are repeatable.
"""

import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import jsonschema
import yaml
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools import ToolResult
from mcp.types import TextContent

from aiops_agent import agent, contracts
from aiops_agent.config import Settings
from aiops_agent.contracts import Contract
from aiops_agent.models import AlertGroup


class Replay(Middleware):
    """Answer tool calls from a recording. A recording is either one result for the
    tool, or a list of {match: {arg: value}, result: ...} tried in order.
    {"error": "..."} replays a tool error. Tools under `passthrough` prefixes
    (runbooks) run for real."""

    def __init__(self, recordings: dict[str, Any], passthrough: tuple[str, ...] = ()) -> None:
        self.recordings = recordings
        self.passthrough = passthrough

    def lookup(self, tool: str, args: dict[str, Any]) -> Any:
        rec = self.recordings.get(tool)
        if isinstance(rec, list) and rec and isinstance(rec[0], dict) and "match" in rec[0]:
            for case in rec:
                if all(args.get(k) == v for k, v in case["match"].items()):
                    return case["result"]
            return None
        return rec

    async def on_call_tool(self, context: MiddlewareContext[Any], call_next: Any) -> Any:
        if context.message.name.startswith(self.passthrough):
            return await call_next(context)
        args = context.message.arguments or {}
        # Validate as the real call would, so a missing or wrong argument (a cluster
        # outside the Contract) costs the model a turn here too.
        assert context.fastmcp_context is not None
        tool = await context.fastmcp_context.fastmcp.get_tool(context.message.name)
        try:
            jsonschema.validate(args, tool.parameters if tool else {})
        except jsonschema.ValidationError as e:
            text = f"Input validation error: {e.message}"
            return ToolResult(content=[TextContent(type="text", text=text)], is_error=True)
        found = self.lookup(context.message.name, args)
        if found is None or (isinstance(found, dict) and set(found) == {"error"}):
            text = found["error"] if found else "no recorded data for this call"
            return ToolResult(content=[TextContent(type="text", text=text)], is_error=True)
        # Same shape FastMCP produces: dicts as-is, anything else wrapped in "result".
        structured = found if isinstance(found, dict) else {"result": found}
        text = found if isinstance(found, str) else json.dumps(found)
        return ToolResult(
            content=[TextContent(type="text", text=text)], structured_content=structured
        )


EVAL_CLUSTER = "kind"  # the Scenarios were recorded on the kind demo


def scenario_contract(namespace: str, enable_actions: bool, runbooks_dir: Path) -> Contract:
    """The Contract a Scenario runs in: one cluster, its namespace, the repo's Runbooks."""
    integrations: list[dict[str, Any]] = [{"name": "kubernetes", "enable_actions": enable_actions}]
    if runbooks_dir.is_dir():
        integrations.append({"name": "runbooks"})
    cluster = {"name": EVAL_CLUSTER, "context": "replay", "namespaces": [namespace]}
    data = {"id": "eval", "name": "Eval", "clusters": [cluster], "integrations": integrations}
    return contracts.build(data, runbook_dirs=[runbooks_dir])


def replay_server(
    contract: Contract, settings: Settings, recordings: dict[str, Any]
) -> agent.Toolbox:
    """Real tool definitions and the Hub's real list; the API clients are never reached."""
    apis = {c.name: (MagicMock(), MagicMock()) for c in contract.clusters}
    toolbox = agent.build_mcp(contract, settings, apis)
    toolbox.mcp.add_middleware(Replay(recordings, passthrough=("runbooks_",)))
    return toolbox


def allowed(expect: dict[str, Any], action: dict[str, Any]) -> bool:
    """expect.allowed_actions: [{name, args?}], args matched as a subset. Empty by default."""
    return any(
        a["name"] == action["name"]
        and all(action["args"].get(k) == v for k, v in a.get("args", {}).items())
        for a in expect.get("allowed_actions", [])
    )


async def triage(
    a: Any, group: AlertGroup, thread_id: str, expect: dict[str, Any]
) -> tuple[agent.Outcome, list[dict[str, Any]]]:
    """Start a triage. Allowed proposed actions are recorded, rejected (never executed
    against the recording) and resumed so the report still gets scored. A disallowed
    one stops the run and stays pending for score() to fail."""
    outcome, proposed = await agent.start(a, group, thread_id), []
    for _ in range(3):  # ponytail: bounded re-proposals; raise if a scenario needs more
        if not outcome.pending or not all(allowed(expect, p) for p in outcome.pending):
            break
        proposed += outcome.pending
        msg = "Eval: proposal recorded, not executed. Do not retry; finish the report."
        outcome = await agent.resume(
            a, thread_id, [{"type": "reject", "message": msg} for _ in outcome.pending]
        )
    return outcome, proposed


def score(scenario: dict[str, Any], outcome: agent.Outcome) -> list[str]:
    """Return the list of failed checks (empty = pass)."""
    expect, report, failures = scenario["expect"], outcome.report, []
    bad = [p["name"] for p in outcome.pending if not allowed(expect, p)]
    if bad:
        return [f"attempted write action: {bad}"]
    if report is None:
        return ["no report"]
    if report.category not in expect["category"]:
        failures.append(f"category {report.category} not in {expect['category']}")
    text = f"{report.summary} {report.probable_root_cause}".lower()
    missing = [k for k in expect.get("keywords", []) if k.lower() not in text]
    if missing:
        failures.append(f"root cause misses {missing}")
    if len(outcome.tool_calls) > expect.get("max_tool_calls", 12):
        failures.append(f"{len(outcome.tool_calls)} tool calls > {expect['max_tool_calls']}")
    return failures


def load_scenarios(directory: Path) -> list[tuple[Path, dict[str, Any]]]:
    return [(p, yaml.safe_load(p.read_text())) for p in sorted(directory.glob("*.yaml"))]


async def run(directory: Path, settings: Settings) -> list[dict[str, Any]]:
    results = []
    for path, scenario in load_scenarios(directory):
        contract = scenario_contract(
            scenario["namespace"], scenario.get("enable_actions", False), settings.runbooks_dir
        )
        group = AlertGroup.model_validate(scenario["alert"])
        start = time.monotonic()
        try:
            async with agent.open_agent(
                settings, replay_server(contract, settings, scenario["tools"])
            ) as a:
                outcome, proposed = await triage(a, group, f"eval-{path.stem}", scenario["expect"])
            failures = score(scenario, outcome)
            calls, report = outcome.tool_calls, outcome.report
        except agent.TriageError as e:
            failures, calls, report, proposed = [str(e)], [], None, []
        results.append(
            {
                "scenario": path.stem,
                "passed": not failures,
                "failures": failures,
                "category": report.category if report else None,
                "tool_calls": len(calls),
                "seconds": round(time.monotonic() - start, 1),
                "calls": calls,
                "proposed": [p["name"] for p in proposed],
                "report": report.to_markdown() if report else None,
            }
        )
    return results


def table(results: list[dict[str, Any]]) -> str:
    rows = [f"{'scenario':32} {'result':6} {'calls':>5} {'secs':>5}  notes"]
    for r in results:
        mark = "PASS" if r["passed"] else "FAIL"
        notes = "; ".join(r["failures"]) or str(r["category"])
        rows.append(f"{r['scenario']:32} {mark:6} {r['tool_calls']:>5} {r['seconds']:>5}  {notes}")
    passed = sum(r["passed"] for r in results)
    rows.append(f"\n{passed}/{len(results)} passed")
    return "\n".join(rows)
