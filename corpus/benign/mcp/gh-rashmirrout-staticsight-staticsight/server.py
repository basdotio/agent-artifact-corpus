"""StaticSight MCP server entrypoint: FastMCP instance, tool registration, prompt, and indexer startup."""

from __future__ import annotations

import functools
import inspect
import json
import logging
import os
import re
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .config import load_config
from .core import md
from .core.errors import StaticSightError
from .engines.capabilities import probe_all
from .semantic.search import status_section
from .shared import shared_file as _shared_file
from .platform import current as current_platform
from .indexer import get_indexer
from .tools.diff_scopes import get_diff_scopes
from .tools.graph_gtags import get_symbol_contract, get_symbol_definition, get_upstream_callers
from .tools.review import review_changes
from .tools.semantic import find_similar_code, refresh_semantic_index, semantic_search
from .tools.ripgrep_mem import get_include_blast_radius, track_struct_risks
from .tools.state_mutation import track_state_mutations
from .tools.lock_order import track_lock_order
from .tools.static_cpp import run_file_static_audit
from .tools.syntax_ctags import get_branch_skeleton, get_enclosing_scope

log = logging.getLogger("staticsight")


def load_spec() -> dict[str, Any]:
    p = _shared_file("tool-spec.json")
    if p is None:
        return {"server": {"name": "StaticSight", "instructions": ""}, "tools": [], "prompts": []}
    return json.loads(p.read_text(encoding="utf-8"))


async def get_index_status() -> str:
    """Reports the state of the GNU Global symbol index and of the semantic search index (building with progress, ready, stale, not built), their locations and age, the embedding model, and which CLI engines are installed. Use when caller/definition results say they came from the ripgrep fallback, or to follow a background semantic index build."""
    cfg = load_config()
    idx = get_indexer(cfg)
    st = idx.status()
    statuses = await probe_all()
    engines = ", ".join(f"`{e.name}` {'✅' if e.ok else '❌'}" for e in statuses)
    out = [
        "### 🗂️ INDEX STATUS",
        f"- **Workspace:** `{cfg.workspace_root}`",
        f"- **State:** {st['state']}",
    ]
    if st["detail"]:
        out.append(f"- **Detail:** {st['detail']}")
    if st["db_path"]:
        out.append(f"- **Database:** `{st['db_path']}`")
    if st["age_s"] is not None:
        out.append(f"- **Age:** {st['age_s']}s (auto-refresh after {cfg.reindex_after_s}s)")
    out.append(f"- **Engines:** {engines}")
    out.append(f"- **Platform:** {current_platform().name}")
    for e in statuses:
        if e.ok and e.version:
            out.append(f"  - `{e.name}`: {e.version}")
        elif not e.ok:
            out.append(f"  - `{e.name}` ({e.level}): {e.problem}" + (f". 💡 {e.hint}" if e.hint else ""))
    out += status_section(cfg)
    return "\n".join(out)


TOOLS: list[Callable[..., Awaitable[str]]] = [
    review_changes,
    get_diff_scopes,
    get_enclosing_scope,
    get_branch_skeleton,
    get_upstream_callers,
    get_symbol_definition,
    get_symbol_contract,
    track_struct_risks,
    get_include_blast_radius,
    track_state_mutations,
    track_lock_order,
    run_file_static_audit,
    semantic_search,
    find_similar_code,
    refresh_semantic_index,
    get_index_status,
]


def safe_tool(fn: Callable[..., Awaitable[str]]) -> Callable[..., Awaitable[str]]:
    """Convert every failure into a Markdown card and enforce the output budget."""

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> str:
        cfg = load_config()
        limit = cfg.review_max_chars if fn.__name__ == "review_changes" else cfg.max_chars
        try:
            result = await fn(*args, **kwargs)
        except StaticSightError as exc:
            return md.error_card(exc.title, exc.message, exc.hint)
        except (TypeError, ValueError) as exc:
            log.exception("tool %s rejected arguments", fn.__name__)
            return md.error_card("Invalid argument", str(exc))
        except Exception as exc:  # the server must never crash because of one tool call
            log.exception("tool %s failed", fn.__name__)
            return md.error_card("Internal error", f"`{fn.__name__}` failed: {type(exc).__name__}: {exc}",
                                 "This is a StaticSight bug; the other tools are still usable.")
        return md.enforce_budget(result, limit)

    wrapper.__signature__ = inspect.signature(fn)  # type: ignore[attr-defined]
    return wrapper


@asynccontextmanager
async def lifespan(_server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    idx = get_indexer(load_config())
    idx.start()  # background: the MCP handshake must not wait for gtags
    yield {"indexer": idx}


def build_server() -> FastMCP:
    spec = load_spec()
    mcp = FastMCP(spec["server"].get("name", "StaticSight"), instructions=spec["server"].get("instructions") or None, lifespan=lifespan)
    default_ann = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
    per_tool = {t["name"]: t.get("annotations", {}) for t in spec.get("tools", [])}
    for fn in TOOLS:
        annotations = ToolAnnotations(**{**default_ann, **per_tool.get(fn.__name__, {})})
        mcp.tool(description=inspect.cleandoc(fn.__doc__ or ""), annotations=annotations, structured_output=False)(safe_tool(fn))

    prompt_file = _shared_file("prompts/review_cpp_changes.md")
    prompt_text = prompt_file.read_text(encoding="utf-8") if prompt_file else "Review the C++ changes using the StaticSight tools."

    @mcp.prompt(name="review_cpp_changes", description="Step-by-step workflow for a thorough, evidence-based review of C++ changes using StaticSight tools.")
    def review_cpp_changes(focus: str = "") -> str:
        extra = f"Pay special attention to: {focus.strip()}." if focus and focus.strip() else ""
        return re.sub(r"[ \t]+\n", "\n", prompt_text.replace("{focus}", extra))

    return mcp


mcp = build_server()


def apply_repo_option(argv: list[str]) -> list[str]:
    """Strip a global `--repo PATH` / `--repo=PATH` (any position) and make it the workspace, like WORKSPACE_ROOT."""
    out: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--repo" or a.startswith("--repo="):
            if a == "--repo":
                if i + 1 >= len(argv):
                    print("error: --repo needs a folder", file=sys.stderr)
                    raise SystemExit(2)
                val, i = argv[i + 1], i + 2
            else:
                val, i = a.split("=", 1)[1], i + 1
            p = Path(val).expanduser()
            if not p.is_dir():
                print(f"error: --repo {val}: not a folder", file=sys.stderr)
                raise SystemExit(2)
            os.environ["WORKSPACE_ROOT"] = str(p.resolve())
            continue
        out.append(a)
        i += 1
    return out


def main() -> None:
    sys.argv[1:] = apply_repo_option(sys.argv[1:])
    if len(sys.argv) > 1 and sys.argv[1] == "tool":
        from .toolrun import run_tool_cli

        raise SystemExit(run_tool_cli(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "doctor":
        from .doctor import run_doctor

        raise SystemExit(run_doctor())
    if len(sys.argv) > 1 and sys.argv[1] in ("index", "search", "similar", "model", "-h", "--help", "help"):
        from .cli import USAGE, run_cli

        if sys.argv[1] in ("-h", "--help", "help"):
            print(USAGE)
            raise SystemExit(0)
        raise SystemExit(run_cli(sys.argv[1:]))
    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    transport = "stdio"
    if len(sys.argv) > 1 and sys.argv[1] in ("stdio", "sse", "streamable-http"):
        transport = sys.argv[1]
    mcp.run(transport=transport)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
