"""provmcp CLI.

    provmcp keygen --out ~/.provmcp/
    provmcp serve  --config servers.yaml [--transport stdio|streamable-http] [--key ...]
    provmcp verify ./provenance.jsonl [--pubkey ~/.provmcp/pub.pem]
    provmcp replay ./provenance.jsonl --config servers.yaml
    provmcp export ./provenance.jsonl --out ./bundle/ [--key ...]
    provmcp verify-bundle ./bundle/
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import __version__
from .keys import KEY_ENV, MissingKeyError, generate, load_private, load_public

log = logging.getLogger("provmcp")


def _add_key_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--key", default=None, help=f"Ed25519 private key PEM (or ${KEY_ENV})")
    p.add_argument("--unsigned", action="store_true",
                   help="run without signatures; the chain is still hashed")


def _signing_key(args: argparse.Namespace):
    if args.unsigned:
        log.warning("running UNSIGNED: entries are hash-chained but not signed")
        return None
    return load_private(args.key)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="provmcp")
    ap.add_argument("--version", action="version", version=f"provmcp {__version__}")
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    serve = sub.add_parser("serve", help="run the proxy")
    serve.add_argument("--config", default="servers.yaml")
    serve.add_argument("--transport", default="stdio", choices=("stdio", "streamable-http"))
    serve.add_argument("--ledger", default=None, help="override the ledger path in config")
    serve.add_argument("--server-logs", default=None,
                       help="directory for downstream servers' stderr (default: passes through)")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    _add_key_args(serve)

    verify = sub.add_parser("verify", help="check a ledger's hash chain and signatures")
    verify.add_argument("ledger")
    verify.add_argument("--pubkey", default=None)

    replay = sub.add_parser("replay", help="re-run recorded calls and report what changed")
    replay.add_argument("ledger")
    replay.add_argument("--config", default="servers.yaml")
    replay.add_argument("--single-run", action="store_true",
                        help="do not re-run disagreeing calls to detect nondeterminism")
    replay.add_argument("--json", action="store_true", help="machine-readable output")

    export = sub.add_parser("export", help="write a portable PROV bundle")
    export.add_argument("ledger")
    export.add_argument("--out", required=True)
    _add_key_args(export)

    vb = sub.add_parser("verify-bundle", help="verify an exported bundle from scratch")
    vb.add_argument("bundle")

    kg = sub.add_parser("keygen", help="generate an Ed25519 signing key pair")
    kg.add_argument("--out", required=True)

    sub.add_parser("resolvers", help="list release resolvers: built-in and installed plugins")

    rs = sub.add_parser("resolve", help="run one resolver now and print the release it returns")
    rs.add_argument("source")
    rs.add_argument("--opt", action="append", default=[], metavar="KEY=VALUE",
                    help="source_options entry (repeatable)")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level="DEBUG" if args.verbose else "INFO",
        stream=sys.stderr,
        format="%(levelname)s %(name)s: %(message)s",
    )
    try:
        return _dispatch(args)
    except MissingKeyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _dispatch(args: argparse.Namespace) -> int:
    from .ledger import Ledger

    if args.cmd == "keygen":
        priv, pub = generate(Path(args.out))
        print(f"private key: {priv}  (mode 600 — never commit this)")
        print(f"public key:  {pub}")
        print(f"export {KEY_ENV}={priv}")
        return 0

    if args.cmd == "resolvers":
        from .sources import registry

        for info in registry(reload=True).values():
            print(f"{info.name:16s} {info.origin}")
        return 0

    if args.cmd == "resolve":
        import asyncio

        from .sources import registry, resolve_release

        if args.source not in registry(reload=True):
            print(f"unknown resolver {args.source!r}; run `provmcp resolvers`", file=sys.stderr)
            return 2
        opts = dict(kv.split("=", 1) for kv in args.opt)
        rel = asyncio.run(resolve_release(args.source, opts, {}))
        print(rel if rel is not None else "(unresolved)")
        return 0 if rel is not None else 1

    if args.cmd == "verify":
        ledger = Ledger(Path(args.ledger))
        pub = load_public(args.pubkey) if args.pubkey else None
        if pub is None:
            log.warning("no --pubkey: checking the hash chain only, not signatures")
        problems = ledger.verify(pub)
        if problems:
            print(f"LEDGER INVALID — {len(problems)} problem(s):")
            for p in problems:
                print(f"  {p}")
            return 1
        n, head = ledger.head()
        print(f"ledger intact: {n} entries, head {head[:16]}…, chain verified"
              + (", signatures verified" if pub else ""))
        return 0

    if args.cmd == "verify-bundle":
        from .bundle import verify_bundle

        problems = verify_bundle(Path(args.bundle))
        if problems:
            print(f"BUNDLE INVALID — {len(problems)} problem(s):")
            for p in problems:
                print(f"  {p}")
            return 1
        print("bundle verified: manifest, chain, and signatures consistent")
        return 0

    if args.cmd == "export":
        from .bundle import write_bundle

        # Export re-signs nothing; the key is only needed to emit the public half.
        # An unsigned ledger exports without one.
        ledger = Ledger(Path(args.ledger), signing_key=_signing_key(args))
        out = write_bundle(ledger, Path(args.out))
        n, _ = ledger.head()
        print(f"bundle written: {out}  ({n} entries)")
        return 0

    from .config import load_config

    if args.cmd == "replay":
        import asyncio
        import json
        from dataclasses import asdict

        from .replay import replay_ledger, summarize

        config = load_config(args.config)
        results = asyncio.run(
            replay_ledger(Ledger(Path(args.ledger)), config, double_run=not args.single_run)
        )
        if args.json:
            print(json.dumps([asdict(r) for r in results], indent=2, default=str))
        else:
            print(summarize(results))
        return 0

    if args.cmd == "serve":
        import asyncio

        from .proxy import build_proxy

        config = load_config(args.config)
        if args.server_logs:
            config.server_log_dir = Path(args.server_logs)
        ledger_path = Path(args.ledger) if args.ledger else config.ledger
        ledger = Ledger(ledger_path, signing_key=_signing_key(args))
        proxy = build_proxy(config, ledger)
        log.info("provmcp %s: %d downstream server(s), ledger %s (%d entries so far)",
                 __version__, len(config.servers), ledger_path, ledger.head()[0])

        if args.transport == "stdio":
            from mcp.server.stdio import stdio_server

            async def run_stdio() -> None:
                async with stdio_server() as (r, w):
                    await proxy.run(r, w, proxy.create_initialization_options())

            asyncio.run(run_stdio())
            return 0

        import uvicorn

        # Stateless: one POST, one response, no session to pin. Any replica can
        # answer any request; the only shared thing is the ledger file.
        app = proxy.streamable_http_app(stateless_http=True, json_response=True, host=args.host)
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
        return 0

    raise SystemExit(f"unknown command {args.cmd}")


if __name__ == "__main__":
    raise SystemExit(main())
