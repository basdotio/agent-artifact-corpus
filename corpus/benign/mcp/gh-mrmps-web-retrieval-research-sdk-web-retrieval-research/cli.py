from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .client import ENDPOINTS, ResearchClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Call web retrieval APIs or run their MCP tools")
    commands = parser.add_subparsers(dest="command", required=True)
    call = commands.add_parser("call", help="Make one provider request and print its full trace")
    call.add_argument("provider", choices=ENDPOINTS)
    call.add_argument("operation", help="Provider operation; see README capability matrix")
    source = call.add_mutually_exclusive_group(required=True)
    source.add_argument("--json", help="JSON request object")
    source.add_argument("--file", type=Path, help="Path to JSON request object")
    commands.add_parser("serve", help="Run the stdio MCP server for Codex or Claude")
    args = parser.parse_args()
    if args.command == "serve":
        from .mcp_server import main as serve

        serve()
        return
    try:
        payload = json.loads(args.json if args.json is not None else args.file.read_text())
        with ResearchClient() as client:
            result = client.call(args.provider, args.operation, payload)
    except (ValueError, TypeError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    if result.error:
        sys.exit(1)


if __name__ == "__main__":
    main()
