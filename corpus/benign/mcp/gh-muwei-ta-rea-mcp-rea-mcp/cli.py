"""CLI bridge for rea-agents.

Discovers the `rea` executable, lists its commands, fetches each command's
JSON Schema, and runs commands with JSON output.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Command catalogue extracted from `rea --llms` output.
_LLMS_ROW = re.compile(r"^\|\s*`rea\s+([a-z0-9][a-z0-9-]*)\s+([^`]*)`\s*\|\s*(.*?)\s*\|\s*$")
_SCHEMAS: dict[str, dict[str, Any]] = {}
_CATALOG: list[dict[str, str]] | None = None


@dataclass
class ReaCommand:
    """One rea CLI command with its positional args and options."""

    name: str
    description: str = ""
    args_schema: dict[str, Any] = field(default_factory=dict)
    options_schema: dict[str, Any] = field(default_factory=dict)


def _detect_node() -> str | None:
    """Locate a Node runtime that can run the rea entry script."""
    node = shutil.which("node")
    if node:
        return node
    for candidate in ("/usr/local/bin/node", "/usr/bin/node"):
        if Path(candidate).is_file():
            return candidate
    return None


def _resolve_npx_cache_rea() -> Path | None:
    """Find a rea-agents install inside an npm cache (npx fallback path)."""
    cache_root = Path(
        os.environ.get("npm_config_cache")
        or os.environ.get("NPM_CONFIG_CACHE")
        or (Path.home() / ".npm" / "_npx")
    )
    if not cache_root.is_dir():
        return None
    # Direct npx layout: <cache>/_npx/<hash>/node_modules/rea-agents
    npx_root = cache_root if cache_root.name == "_npx" else cache_root / "_npx"
    if npx_root.is_dir():
        for entry in sorted(npx_root.iterdir()):
            pkg = entry / "node_modules" / "rea-agents"
            if (pkg / "scripts" / "rea.mjs").is_file():
                return pkg
    return None


def resolve_entry() -> tuple[str, list[str]] | None:
    """Return (argv_prefix) that runs the rea CLI, or None when unavailable.

    Resolution order:
      1. REA_MCP_CLI env var (absolute path to rea executable or entry .mjs)
      2. `rea` / `rea-agents` on PATH
      3. a cached npx install under the npm cache directory
    """
    override = os.environ.get("REA_MCP_CLI")
    if override:
        p = Path(override)
        if p.is_file() and p.suffix == ".mjs":
            node = _detect_node()
            if node:
                return (node, [str(p)])
        if Path(override).is_file() or shutil.which(override):
            return (override, [])
        return None

    for name in ("rea", "rea-agents"):
        found = shutil.which(name)
        if found:
            return (found, [])

    pkg = _resolve_npx_cache_rea()
    if pkg:
        node = _detect_node()
        if node:
            return (node, [str(pkg / "scripts" / "rea.mjs")])
    return None


def _run_cli(argv: list[str], timeout: float = 600.0) -> str:
    prefix = resolve_entry()
    if prefix is None:
        raise RuntimeError(
            "rea CLI not found. Install rea-agents (`npm i -g rea-agents`) or set "
            "REA_MCP_CLI to the rea executable path."
        )
    exe, extra = prefix
    env = dict(os.environ)
    env.setdefault("NO_COLOR", "1")
    proc = subprocess.run(
        [exe, *extra, *argv],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0 or not out:
        detail = err or out or f"exit code {proc.returncode}"
        raise RuntimeError(detail)
    return out


def load_catalog() -> list[dict[str, str]]:
    """Load the command catalogue from `rea --llms` (cached)."""
    global _CATALOG
    if _CATALOG is not None:
        return _CATALOG
    manifest = _run_cli(["--llms"])
    catalog: list[dict[str, str]] = []
    for line in manifest.splitlines():
        m = _LLMS_ROW.match(line)
        if not m:
            continue
        name, usage, description = m.group(1), m.group(2).strip(), m.group(3).strip()
        if name in ("completions", "mcp", "setup", "uninstall", "update"):
            # Integrations and lifecycle commands: not exposed as MCP tools.
            continue
        catalog.append(
            {
                "name": name,
                "usage": usage,
                "description": description,
            }
        )
    _CATALOG = catalog
    return catalog


def fetch_schema(command: str) -> dict[str, Any]:
    """Fetch and cache the JSON Schema for one rea command."""
    if command in _SCHEMAS:
        return _SCHEMAS[command]
    raw = _run_cli([command, "--schema", "--format", "json"])
    schema = json.loads(raw)
    _SCHEMAS[command] = schema
    return schema


def camel_to_kebab(name: str) -> str:
    """Convert a camelCase option name to its kebab-case CLI flag."""
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def build_argv(command: str, schema: dict[str, Any], kwargs: dict[str, Any]) -> list[str]:
    """Build the CLI argv for one command invocation from typed kwargs."""
    argv: list[str] = [command]

    args_spec = schema.get("args", {}).get("properties", {})
    args_required = set(schema.get("args", {}).get("required", []))
    ordered_arg_names = list(args_spec.keys())

    options_spec = schema.get("options", {}).get("properties", {})

    consumed = set()

    # Positional arguments in schema declaration order.
    for name in ordered_arg_names:
        if name not in kwargs or kwargs[name] is None:
            if name in args_required:
                raise ValueError(f"Missing required argument: {name}")
            continue
        value = kwargs[name]
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        argv.append(str(value))
        consumed.add(name)

    # Options as kebab-case flags.
    for name, value in kwargs.items():
        if value is None or name in consumed:
            continue
        flag = camel_to_kebab(name)
        if flag not in options_spec:
            # Unknown option: still forward it (agent may pass newly added flags).
            pass
        if isinstance(value, bool):
            if value:
                argv.append(f"--{flag}")
        elif isinstance(value, (dict, list)):
            argv.extend([f"--{flag}", json.dumps(value, ensure_ascii=False)])
        else:
            argv.extend([f"--{flag}", str(value)])

    argv.extend(["--format", "json"])
    return argv


def run_command(command: str, kwargs: dict[str, Any] | None = None) -> str:
    """Run one rea command with JSON output and return stdout."""
    kwargs = kwargs or {}
    schema = fetch_schema(command)
    argv = build_argv(command, schema, kwargs)
    return _run_cli(argv)
