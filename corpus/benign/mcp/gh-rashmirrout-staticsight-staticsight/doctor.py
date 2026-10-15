"""`staticsight doctor`: verify engines and workspace before connecting an MCP client."""

from __future__ import annotations

import asyncio
import os

from .config import load_config
from .engines.capabilities import PURPOSE, probe_all
from .platform import current


def _semantic_lines(cfg) -> list[str]:
    from .core.errors import StaticSightError
    from .engines.embedder import dependencies_ok, missing_model_files, model_dir, model_id

    out: list[str] = []
    if cfg.embed_model == "test-hash" and not cfg.embed_model_dir:
        return ["  OK   model     test-hash (tests only)"]
    try:
        dependencies_ok()
        out.append("  OK   packages  onnxruntime, tokenizers, numpy")
    except StaticSightError as exc:
        out.append(f"  WARN packages  {exc.message}")
        if exc.hint:
            out.append(f"       fix: {exc.hint}")
        return out
    try:
        missing = missing_model_files(cfg)
    except StaticSightError as exc:
        return out + [f"  WARN model     {exc.message}"]
    if missing:
        out.append(f"  WARN model     {model_id(cfg)} not downloaded ({len(missing)} file(s) missing)")
        out.append("       fix: downloaded automatically on first use, or run `staticsight model download` "
                   "(offline: STATICSIGHT_EMBED_MODEL_DIR)")
    else:
        out.append(f"  OK   model     {model_id(cfg)} ({model_dir(cfg)})")
    return out


async def _report() -> tuple[str, int]:
    cfg = load_config()
    plat = current()
    statuses = await probe_all()
    import sys
    from importlib.metadata import PackageNotFoundError, version

    try:
        mcp_version = f"mcp {version('mcp')}"
    except PackageNotFoundError:
        mcp_version = "mcp (version unknown)"
    runtime = f"Python {sys.version.split()[0]} ({sys.executable}), {mcp_version}"
    lines = ["StaticSight doctor", f"Platform:  {plat.name}", f"Runtime:   {runtime}", f"Workspace: {cfg.workspace_root}"]
    is_git = (cfg.workspace_root / ".git").exists()
    lines.append(f"  {'OK  ' if is_git else 'WARN'} git repository" + ("" if is_git else " not found (diff tools need one)"))
    probe_dir = cfg.cache_dir
    while not probe_dir.exists() and probe_dir.parent != probe_dir:
        probe_dir = probe_dir.parent  # doctor never creates anything; check the nearest existing parent
    writable = os.access(probe_dir, os.W_OK)
    lines.append(f"Cache:     {cfg.cache_dir} ({'writable' if writable else 'NOT writable'}; models)")
    from .config import workspace_data_dir

    data, why = workspace_data_dir(cfg, create=False)
    lines.append(f"Data:      {data} ({why}; indexes)")
    lines.append("")
    lines.append("Engines:")
    exit_code = 0
    for st in statuses:
        if st.ok:
            mark = "OK  "
        elif st.level == "required":
            mark = "FAIL"
            exit_code = 1
        else:
            mark = "WARN"
        detail = st.version if st.ok else st.problem
        lines.append(f"  {mark} {st.name:<9} [{st.level}] {detail}")
        lines.append(f"       used for: {PURPOSE.get(st.name, '')}")
        if not st.ok and st.hint:
            lines.append(f"       fix: {st.hint}")
    lines.append("")
    lines.append("Semantic search (optional):")
    lines += _semantic_lines(cfg)
    lines.append("")
    lines.append("Result: " + ("all required engines OK" if exit_code == 0 else "missing or unusable required engines (see FAIL)"))
    return "\n".join(lines), exit_code


def run_doctor() -> int:
    text, code = asyncio.run(_report())
    print(text)
    return code
