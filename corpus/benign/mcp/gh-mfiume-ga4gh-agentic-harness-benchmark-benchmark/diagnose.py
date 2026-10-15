"""Attribute failed turns to causes, and causes to the component that would fix them.

    python -m benchmark.diagnose runs/exp/root/dev-low [--json]

Each failed, code-graded turn gets an outcome (timeout, no submission, declared guess, wrong
answer) and the error signatures of the tool calls it made, read from the head of each result.
A signature maps to a component: the MCP server's service lookup, its Beacon tool, search, TRS
listing, or the model. A cause's ceiling is the number of failed turns it touches: the most a
fix to that component could recover. The inner loop works the largest ceiling first.

Only the dev split should be diagnosed; the held-out split stays unseen until it is reported.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .report import graded_turns
from .tasks import ROOT, load
from .validate import TrsValidator

# (signature, component, pattern over the result head); first match wins.
SIGNATURES: list[tuple[str, str, re.Pattern[str]]] = [
    ("service id not found", "mcp: service lookup",
     re.compile(r"no registered service with id|resource not found: |SERVICE_NOT_FOUND.{0,80}resource not found")),
    ("argument validation error", "mcp: argument errors", re.compile(r"validation error for \w+Arguments")),
    ("beacon HTTP 404", "mcp: beacon query", re.compile(r"upstream returned HTTP 404")),
    ("endpoint HTTP 404", "mcp: generic endpoint", re.compile(r"upstream call failed \(404\)")),
    ("upstream unreachable", "services", re.compile(r"unreachable_dns|nodename nor servname|ConnectError|blocked")),
    ("upstream other HTTP error", "services", re.compile(r"upstream (returned HTTP|call failed \()\s*\d{3}")),
    ("POST disabled", "mcp: generic endpoint", re.compile(r"POST is disabled")),
    ("unknown tool", "model: tool names", re.compile(r"there is no tool named")),
    ("not recorded", "framework", re.compile(r"cannot be replayed|not recorded")),
]
_EMPTY_SEARCH = re.compile(r'"count":\s*0\b')
SEARCH_TOOLS = {"search_services", "ga4gh_service_search"}
LISTING_TOOLS = {"trs_list_tools"}


def call_signatures(call: dict[str, Any]) -> list[tuple[str, str]]:
    head = call.get("head") or call.get("error") or ""
    found = []
    for name, component, pattern in SIGNATURES:
        if pattern.search(head):
            found.append((name, component))
            break
    else:
        if call.get("is_error"):
            found.append((f"error from {call['tool']}", "mcp: argument errors"))
    if call["tool"] in SEARCH_TOOLS and _EMPTY_SEARCH.search(head):
        found.append(("search found nothing", "mcp: search"))
    if call.get("truncated"):
        component = "mcp: trs listing" if call["tool"] in LISTING_TOOLS else "mcp: result size"
        found.append((f"result truncated ({call['tool']})", component))
    return found


def outcome(turn: dict[str, Any], verdict: dict[str, Any]) -> str:
    if verdict.get("timeout"):
        return "timeout"
    if turn.get("stopped") == "malformed_tool_calls":
        return "malformed tool calls"
    if not turn.get("submitted"):
        return "out of steps, nothing submitted" if turn.get("stopped") == "max_steps" else "no submission"
    if turn["submitted"].get("determined") is False:
        return "declared guess"
    if not turn.get("tool_calls"):
        return "wrong, no tool used"
    return "wrong answer"


def diagnose(run: Path) -> dict[str, Any]:
    tasks, _ = load()
    by_id = {t["id"]: t for t in tasks}
    validator = TrsValidator(ROOT / "cassettes" / "trs-validation.json")
    outcomes: Counter[str] = Counter()
    clusters: dict[tuple[str, str], set[str]] = defaultdict(set)
    components: dict[str, set[str]] = defaultdict(set)
    calls_by_signature: Counter[str] = Counter()
    failed = graded = 0
    for item in graded_turns(run, validator, by_id):
        if item["verdict"] not in ("pass", "fail"):
            continue
        graded += 1
        turn = item["turn"] or {}
        for call in turn.get("tool_calls") or []:
            for name, _ in call_signatures(call):
                calls_by_signature[name] += 1
        if item["verdict"] == "pass":
            continue
        failed += 1
        label = f"{item['task_id']}#{item['repeat']}.{item['turn_index']}"
        outcomes[outcome(turn, item)] += 1
        seen = set()
        for call in turn.get("tool_calls") or []:
            for name, component in call_signatures(call):
                if (name, component) not in seen:
                    seen.add((name, component))
                    clusters[(name, component)].add(label)
                    components[component].add(label)
    return {
        "run": str(run), "graded_turns": graded, "failed_turns": failed,
        "outcomes": dict(outcomes.most_common()),
        "components": sorted(({"component": c, "ceiling": len(t)} for c, t in components.items()),
                             key=lambda x: -x["ceiling"]),
        "causes": sorted(({"signature": n, "component": c, "ceiling": len(t), "calls": calls_by_signature[n],
                           "turns": sorted(t)} for (n, c), t in clusters.items()), key=lambda x: -x["ceiling"]),
    }


def render(d: dict[str, Any]) -> str:
    lines = [f"# Failure attribution: {d['run']}", "",
             f"{d['failed_turns']} of {d['graded_turns']} code-graded turns failed.", "",
             "| Outcome | Turns |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in d["outcomes"].items()]
    lines += ["", "A failed turn can touch several causes, so ceilings overlap.", "",
              "| Component | Ceiling (failed turns touched) |", "|---|---|"]
    lines += [f"| {c['component']} | {c['ceiling']} |" for c in d["components"]]
    lines += ["", "| Signature | Component | Ceiling | Calls (all turns) |", "|---|---|---|---|"]
    lines += [f"| {c['signature']} | {c['component']} | {c['ceiling']} | {c['calls']} |" for c in d["causes"]]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    d = diagnose(args.run)
    print(json.dumps(d, indent=1) if args.json else render(d))


if __name__ == "__main__":
    main()
