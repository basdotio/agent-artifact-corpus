import argparse
import json
import webbrowser

from .config import token


def main():
    parser = argparse.ArgumentParser(description="Mustang Tone Agent")
    parser.add_argument(
        "command", choices=["serve", "mcp", "inspect", "tev-benchmark"], nargs="?", default="serve"
    )
    parser.add_argument("--open", action="store_true", help="Open the local desktop interface")
    parser.add_argument(
        "--model", default="tev1:0.8b", choices=["tev1:0.8b", "tev1:4b"], help="Decision model to benchmark"
    )
    args = parser.parse_args()
    if args.command == "mcp":
        from .mcp_server import make_server

        make_server().run(transport="stdio")
    elif args.command == "inspect":
        from .phone import Phone

        print(json.dumps(Phone().inspect(), indent=2))
    elif args.command == "tev-benchmark":
        from .decisions import benchmark

        result = benchmark(args.model)
        result.pop("results", None)
        print(json.dumps(result, indent=2))
    else:
        import uvicorn

        from .api import create_app

        if args.open:
            webbrowser.open(f"http://127.0.0.1:8765/#token={token()}")
        uvicorn.run(create_app(), host="127.0.0.1", port=8765, log_level="warning")


if __name__ == "__main__":
    main()
