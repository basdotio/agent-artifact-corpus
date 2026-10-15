"""Command-line entry points besides the MCP server: doctor, semantic index management, search, model download."""

from __future__ import annotations

import argparse
import asyncio
import sys

from .config import load_config
from .core.errors import StaticSightError

USAGE = """staticsight [COMMAND]

  (no command) | stdio | sse | streamable-http   run the MCP server
  doctor                                         check engines and workspace
  index build [--full]                           build/refresh the semantic index (blocking, with progress)
  index refresh                                  incremental refresh (only changed files)
  index status                                   show semantic + GNU Global index status
  search "query" [--glob G] [--language L] [--kind K] [--top N]
  similar FILE LINE [--end N] [--top N]
  model download | status                        fetch / verify the pinned embedding model
  tool --list                                    list the 16 review tools and their parameters
  tool NAME [ARGS] [--param VALUE ...]           run one tool, print the Markdown an agent receives

Global option: --repo PATH selects the repository (same as WORKSPACE_ROOT). Default: the nearest folder above
the current directory that holds .staticsight/ or .git. Indexes live in <repo>/.staticsight/ (git-ignored)."""


def _progress(msg: str) -> None:
    print(f"  … {msg}", file=sys.stderr, flush=True)


def one_shot_semantic() -> None:
    """A command-line process exits after one answer, so a background refresh would die with it: refresh in the
    foreground instead, whatever the drift (the MCP server keeps its 200-file threshold)."""
    import os

    os.environ["STATICSIGHT_SEMANTIC_AUTO_REFRESH_FILES"] = str(10**9)


async def ensure_semantic_built() -> None:
    """First use in a terminal: build the index now, with progress, instead of answering keyword-only."""
    from .semantic.index import get_semantic_index

    cfg = load_config()
    idx = get_semantic_index(cfg)
    if not cfg.semantic_auto_refresh or (idx.exists() and idx.compatible()):
        return
    _progress("building the semantic index (first run in this repository)")
    try:
        await idx.refresh(progress=_progress)
    except StaticSightError:
        pass  # the tool itself reports what is missing (packages, model, ...)


async def _index(args) -> int:
    from .semantic.index import get_semantic_index
    from .semantic.search import status_section

    cfg = load_config()
    idx = get_semantic_index(cfg)
    if args.action in ("build", "refresh"):
        full = bool(getattr(args, "full", False))
        print(f"Semantic index for {cfg.workspace_root}", file=sys.stderr)

        async def ticker():
            last = ""
            while True:
                await asyncio.sleep(2)
                note = idx.progress_note(short=True)
                if note != last and idx.state.status == "building":
                    _progress(note)
                    last = note

        t = asyncio.create_task(ticker())
        try:
            summary = await idx.refresh(full=full, progress=_progress)
        finally:
            t.cancel()
        print(summary)
        return 0
    print("\n".join(status_section(cfg)).strip())
    return 0


async def _search(args) -> int:
    from .semantic.search import semantic_search_report

    await ensure_semantic_built()
    cfg = load_config()
    print(await semantic_search_report(cfg, args.query, args.glob, args.language, args.kind, args.top))
    return 0


async def _similar(args) -> int:
    from .semantic.search import similar_code_report

    await ensure_semantic_built()
    print(await similar_code_report(load_config(), args.file, args.line, args.end, args.top))
    return 0


def _model(args) -> int:
    from .engines.embedder import download_model, missing_model_files, model_dir, model_id

    cfg = load_config()
    if cfg.embed_model == "test-hash" and not cfg.embed_model_dir:
        print("test-hash needs no download")
        return 0
    if args.action == "download":
        d = download_model(cfg, _progress)
        print(f"model {model_id(cfg)} ready in {d}")
        return 0
    missing = missing_model_files(cfg)
    print(f"model {model_id(cfg)} in {model_dir(cfg)}: " + ("OK (verified)" if not missing else "missing " + ", ".join(missing)))
    return 0 if not missing else 1


def run_cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="staticsight", usage=USAGE, add_help=True)
    sub = p.add_subparsers(dest="cmd")
    pi = sub.add_parser("index")
    pi.add_argument("action", choices=["build", "refresh", "status"])
    pi.add_argument("--full", action="store_true")
    ps = sub.add_parser("search")
    ps.add_argument("query")
    ps.add_argument("--glob", default="")
    ps.add_argument("--language", default="")
    ps.add_argument("--kind", default="")
    ps.add_argument("--top", type=int, default=10)
    psim = sub.add_parser("similar")
    psim.add_argument("file")
    psim.add_argument("line", type=int)
    psim.add_argument("--end", type=int, default=0)
    psim.add_argument("--top", type=int, default=8)
    pm = sub.add_parser("model")
    pm.add_argument("action", choices=["download", "status"])
    args = p.parse_args(argv)
    one_shot_semantic()
    try:
        if args.cmd == "index":
            return asyncio.run(_index(args))
        if args.cmd == "search":
            return asyncio.run(_search(args))
        if args.cmd == "similar":
            return asyncio.run(_similar(args))
        if args.cmd == "model":
            return _model(args)
    except StaticSightError as exc:
        print(f"error: {exc.message}" + (f"\nhint: {exc.hint}" if exc.hint else ""), file=sys.stderr)
        return 1
    print(USAGE)
    return 2
