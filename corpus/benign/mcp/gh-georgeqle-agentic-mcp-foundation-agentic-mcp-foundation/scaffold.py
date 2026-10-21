"""Generate a working MCP adapter using the shared lifecycle contract."""

import argparse
import json
import re
from pathlib import Path

TEMPLATE = '''"""Generated typed adapter. Replace echo with domain operations."""
import asyncio
import hashlib
import json
import os
import sys
import threading
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from agentic_mcp_foundation.jobs import JobStore, JobEngine
from agentic_mcp_foundation.transport import SharedClient, serve

HOME = Path(os.getenv("AGENTIC_TOOL_HOME", str(Path.home()/".local/share/__NAME__")))
IDENTITY = {"build": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "contract_major": 1}

def coordinator():
    state = {}
    lock = threading.Lock()
    def dispatch(operation, payload):
        with lock:
            if not state:
                store = JobStore(HOME/"jobs.sqlite3")
                store.recover()
                def echo(request, context):
                    context.progress("echoing")
                    return {"text": request["text"]}
                state.update(store=store, engine=JobEngine(store, {"echo": echo}))
        if operation == "submit":
            text = payload.get("text")
            if not isinstance(text, str) or not 1 <= len(text) <= 1000:
                raise ValueError("text must contain 1–1000 characters")
            return state["engine"].submit("echo", {"text": text}, payload["key"])
        if operation == "job":
            return state["engine"].get(payload["id"])
        if operation == "cancel":
            return state["engine"].cancel(payload["id"])
        if operation == "retire":
            state["engine"].drain()
            return {"retired": True}
        raise ValueError("Unknown operation")
    serve(HOME, IDENTITY, dispatch, lambda: None)

def main():
    if "--coordinator" in sys.argv:
        coordinator()
        return
    client = SharedClient(HOME, IDENTITY, [sys.executable, "-m", "__MODULE__", "--coordinator"], {})
    mcp = FastMCP("__NAME__")
    @mcp.tool()
    async def get_status() -> dict:
        return await asyncio.to_thread(client.call, "health")
    @mcp.tool()
    async def submit_echo(text: str, idempotency_key: str) -> dict:
        return await asyncio.to_thread(client.call, "submit", {"text": text, "key": idempotency_key})
    @mcp.tool()
    async def get_job(job_id: str) -> dict:
        return await asyncio.to_thread(client.call, "job", {"id": job_id})
    @mcp.tool()
    async def cancel_job(job_id: str) -> dict:
        return await asyncio.to_thread(client.call, "cancel", {"id": job_id})
    mcp.run()

if __name__ == "__main__":
    main()
'''


def scaffold(name, output):
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", name) or len(name) > 50:
        raise ValueError("Use a lowercase hyphenated tool name, at most 50 characters")
    if output.exists():
        raise FileExistsError("Output exists; scaffolding never overwrites a project")
    module = name.replace("-", "_")
    package = output / "src" / module
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "__main__.py").write_text(
        TEMPLATE.replace("__NAME__", name).replace("__MODULE__", module)
    )
    (output / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["hatchling>=1.27"]\nbuild-backend = "hatchling.build"\n\n'
        f'[project]\nname = "{name}"\nversion = "0.1.0"\nrequires-python = ">=3.10"\n'
        'dependencies = ["agentic-mcp-foundation @ git+https://github.com/GeorgeQLe/agentic-mcp-foundation.git@v0.1.0", "mcp>=1.12,<2"]\n'
        "\n[tool.hatch.metadata]\nallow-direct-references = true\n"
    )
    plugin = output / "plugin/.codex-plugin"
    plugin.mkdir(parents=True)
    (plugin / "plugin.json").write_text(
        json.dumps(
            {
                "name": name,
                "version": "0.1.0",
                "description": f"Typed {name} operations with durable jobs",
                "skills": "./skills/",
                "mcpServers": "./.mcp.json",
            },
            indent=2,
        )
    )
    (output / "plugin/.mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    name: {
                        "command": "python3",
                        "args": ["-m", module],
                        "env_vars": ["AGENTIC_TOOL_HOME"],
                    }
                }
            },
            indent=2,
        )
    )
    skill = output / "plugin/skills" / ("use-" + name)
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        f"---\nname: use-{name}\ndescription: Execute and recover typed {name} jobs.\n---\n\n"
        "Check get_status before work. Submit with a stable idempotency key, retain its job ID, "
        "and poll get_job. After reconnecting, recover the original job before retrying. "
        "A changed request requires a new key. Cancellation is cooperative; active work retains "
        "its capacity. Inspect interrupted receipts before submitting new work.\n"
    )
    (output / "README.md").write_text(
        f"# {name}\n\nThis starter uses agentic-mcp-foundation from its v0.1.0 Git tag. "
        "Run `uv sync` to install and lock the dependency to its resolved commit. "
        "It is not yet published to a package index.\n\n"
        f"Run `python -m {module}` after installation. The generated echo operation demonstrates "
        "shared discovery, durable results, idempotency, reconnect recovery and cancellation. "
        "Replace echo with typed domain operations; add capability readiness and a real probe "
        "appropriate to your backend. Use the foundation launcher and local-vision installer "
        "as the reference for verified distribution. The plugin launch declaration assumes the "
        "package is already installed in the selected Python environment.\n"
    )
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("scaffold")
    create.add_argument("name")
    create.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(scaffold(args.name, args.output))
