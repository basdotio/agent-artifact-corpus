"""Command line: `aiops triage`, `aiops serve`, `aiops mcp`, `aiops eval`, `aiops contracts`."""

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Any

from aiops_agent import agent, contracts, evals
from aiops_agent.config import Settings
from aiops_agent.models import AlertGroup


def ask(action: dict[str, Any], auto_reject: bool) -> dict[str, Any]:
    print(f"\n>>> {action['description']}", file=sys.stderr)
    if auto_reject or not sys.stdin.isatty():
        print(">>> rejected (non-interactive)", file=sys.stderr)
        return {"type": "reject", "message": "No human available to approve. Report only."}
    answer = input(">>> approve? [y/N] ").strip().lower()
    if answer == "y":
        return {"type": "approve"}
    return {"type": "reject", "message": "Rejected by the on-call engineer. Do not retry."}


async def triage(group: AlertGroup, as_json: bool, auto_reject: bool) -> int:
    settings = Settings()
    toolbox = agent.build_mcp(contracts.from_settings(settings), settings)
    async with agent.open_agent(settings, toolbox) as a:
        outcome = await agent.start(a, group, thread_id=str(uuid.uuid4()))
        while outcome.pending:
            decisions = [ask(action, auto_reject) for action in outcome.pending]
            outcome = await agent.resume(a, outcome.thread_id, decisions)
    assert outcome.report is not None
    if as_json:
        report = outcome.report.model_dump(mode="json")
        print(json.dumps({**report, "executed_actions": outcome.executed_actions}, indent=2))
    else:
        print(outcome.report.to_markdown(outcome.executed_actions))
        print(f"\n_tool calls: {', '.join(outcome.tool_calls)}_", file=sys.stderr)
    return 0


def run_mcp(name: str, transport: str, host: str, port: int) -> int:
    settings = Settings()
    contract = contracts.from_settings(settings)
    by_name = {i.name: i for i in contract.integrations}
    if name not in by_name:
        print(f"{name} is not configured (see the AIOPS_* variables)", file=sys.stderr)
        return 1
    server, _ = agent.integration_server(contract, by_name[name], settings)
    if transport == "stdio":
        server.run(transport="stdio", show_banner=False)
    else:
        server.run(transport="http", host=host, port=port)
    return 0


def validate_contracts(directory: Path) -> int:
    try:
        loaded = contracts.load(directory)
    except contracts.ContractError as e:
        print("\n".join(e.problems), file=sys.stderr)
        return 1
    for c in loaded.values():
        integrations = ", ".join(i.name for i in c.integrations)
        clusters = ", ".join(cl.name for cl in c.clusters) or "-"
        secrets = len(c.secret_refs())
        print(f"{c.id}: clusters {clusters}; integrations {integrations}; secrets {secrets}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aiops", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("triage", help="triage one Alertmanager webhook payload (JSON file)")
    t.add_argument("alert", type=Path)
    t.add_argument("--json", action="store_true", help="print the report as JSON")
    t.add_argument("--auto-reject", action="store_true", help="reject every action, report only")

    s = sub.add_parser("serve", help="run the Alertmanager webhook receiver")
    s.add_argument("--host", default="0.0.0.0")  # noqa: S104 - container entrypoint
    s.add_argument("--port", type=int, default=8080)

    m = sub.add_parser("mcp", help="run one MCP server standalone (e.g. for Claude Code)")
    m.add_argument("server", choices=["kubernetes", "prometheus", "runbooks"])
    m.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    m.add_argument("--host", default="127.0.0.1")
    m.add_argument("--port", type=int, default=8765)

    e = sub.add_parser("eval", help="score the agent on recorded scenarios")
    e.add_argument("scenarios", type=Path, nargs="?", default=Path("evals/scenarios"))
    e.add_argument("--json", action="store_true")
    e.add_argument("--out", type=Path, help="write each report as markdown here")

    c = sub.add_parser("contracts", help="manage the contracts directory")
    csub = c.add_subparsers(dest="contracts_cmd", required=True)
    v = csub.add_parser("validate", help="check every Contract and decrypt its secrets")
    v.add_argument("directory", type=Path)

    args = parser.parse_args(argv)
    if args.cmd == "contracts":
        return validate_contracts(args.directory)
    if args.cmd == "triage":
        group = AlertGroup.model_validate_json(args.alert.read_text())
        return asyncio.run(triage(group, args.json, args.auto_reject))
    if args.cmd == "mcp":
        return run_mcp(args.server, args.transport, args.host, args.port)
    if args.cmd == "serve":
        import uvicorn

        uvicorn.run("aiops_agent.api:create_app", factory=True, host=args.host, port=args.port)
        return 0
    if args.cmd == "eval":
        results = asyncio.run(evals.run(args.scenarios, Settings()))
        if args.out:
            args.out.mkdir(parents=True, exist_ok=True)
            for r in results:
                calls = "\n".join(f"{i}. `{c}`" for i, c in enumerate(r["calls"], 1))
                body = f"{r['report']}\n\n**Tool calls**\n{calls}\n"
                (args.out / f"{r['scenario']}.md").write_text(body)
        print(json.dumps(results, indent=2) if args.json else evals.table(results))
        return 0 if all(r["passed"] for r in results) else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
