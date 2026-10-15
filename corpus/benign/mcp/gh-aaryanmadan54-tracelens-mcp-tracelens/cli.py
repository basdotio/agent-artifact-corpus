import argparse
import asyncio
import json
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import Client

from .agent import investigate
from .fixture import PLAN
from .server import create_server


async def inspect_tools(call):
    async with Client(create_server()) as client:
        if call:
            name, args = next((n, a) for n, a in PLAN if n == call)
            result = await client.call_tool(name, args)
            print(json.dumps(result.data, indent=2))
        else:
            print(json.dumps([t.model_dump() for t in await client.list_tools()], indent=2))


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="TraceLens — SYNTHETIC telemetry investigation")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("investigate", help="Investigate the bundled checkout incident; same directory resumes progress")
    run.add_argument("--mode", choices=["fixture", "live"], default="fixture")
    run.add_argument("--scenario", choices=["normal", "transient"], default="normal")
    run.add_argument("--run-dir", type=Path, default=Path("runs/demo"))
    run.add_argument("--model", default=os.getenv("TRACELENS_MODEL", "gpt-4.1-mini"))
    inspect = commands.add_parser("tools", help="Inspect MCP schemas or query real fixture tools")
    inspect.add_argument("--call", choices=["query_logs", "get_service_metrics", "get_traces"])
    commands.add_parser("server", help="Run the read-only MCP server over stdio")
    demo = commands.add_parser("demo", help="Serve the pre-recorded static fixture explorer (no API key needed)")
    demo.add_argument("--port", type=int, default=8000)
    demo.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    try:
        if args.command == "server":
            create_server().run(transport="stdio", show_banner=False)
        elif args.command == "tools":
            asyncio.run(inspect_tools(args.call))
        elif args.command == "demo":
            root = str(files("tracelens").joinpath("web"))
            handler = partial(SimpleHTTPRequestHandler, directory=root)
            with ThreadingHTTPServer((args.host, args.port), handler) as server:
                print(f"TraceLens SYNTHETIC fixture demo: http://{args.host}:{args.port}", flush=True)
                server.serve_forever()
        else:
            if args.mode == "live" and not os.getenv("OPENAI_API_KEY"):
                parser.error("Live mode requires OPENAI_API_KEY. Use --mode fixture for the offline example.")
            state = asyncio.run(investigate(args.run_dir, args.mode, args.scenario, args.model))
            print(f"SYNTHETIC | {args.mode.upper()} | {state.data['status']}")
            print(f"Report: {(args.run_dir / 'report.md').resolve()}")
            print(f"Progress: {state.path.resolve()}")
    except KeyboardInterrupt:
        print("Stopped. Investigation checkpoints, if any, are preserved.")
    except Exception as exc:
        parser.exit(1, f"TraceLens: {type(exc).__name__}: {exc}\n")
