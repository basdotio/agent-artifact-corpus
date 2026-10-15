import argparse
import json
from pathlib import Path
import sys
from .core import Engine, MLXBackend


def main():
    parser = argparse.ArgumentParser(description="Local, inspectable AI decisions")
    parser.add_argument("--model", help="Checkpoint directory or Hugging Face repository")
    parser.add_argument("--revision", help="Pin a Hugging Face checkpoint commit")
    parser.add_argument("--device", choices=["gpu", "cpu"])
    sub = parser.add_subparsers(dest="command", required=True)
    ui = sub.add_parser("serve", help="Open the loopback web workbench")
    ui.add_argument("--port", type=int, default=8765)
    for name in ("decide", "evidence"):
        p = sub.add_parser(name)
        p.add_argument("file", help="JSON file, or - for stdin")
    bench = sub.add_parser("benchmark")
    bench.add_argument("--dataset", help="Custom JSON fixtures with expected labels")
    bench.add_argument("--output", help="Save a report instead of printing it")
    sub.add_parser("mcp", help="Expose tools over MCP stdio")
    args = parser.parse_args()
    if args.command == "mcp":
        from .mcp_server import run
        return run(args.model, args.revision, args.device)
    engine = Engine(MLXBackend(args.model, args.revision, args.device))
    if args.command == "serve":
        from .server import serve
        return serve(engine, args.port)
    if args.command == "benchmark":
        from .benchmark import run
        result = run(engine, args.dataset)
    else:
        payload = json.load(sys.stdin) if args.file == "-" else json.loads(Path(args.file).read_text())
        result = getattr(engine, args.command)(payload)
    encoded = json.dumps(result, indent=2, ensure_ascii=False)
    if args.command == "benchmark" and args.output:
        Path(args.output).write_text(encoded + "\n")
        print(args.output)
    else:
        print(encoded)


if __name__ == "__main__":
    main()
