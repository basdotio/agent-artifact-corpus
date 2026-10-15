"""Official MCP SDK stdio server, scoped to one validated packaged fixture."""

import argparse
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from devsec_bench.benchmarks.loader import discover
from devsec_bench.tools.registry import Registry


def create_server(registry: Registry) -> FastMCP:
    server = FastMCP(
        "DevSec Agent Bench",
        instructions="Read-only analysis of the authorized synthetic target. No execution tools.",
    )

    def invoke(name: str, args: dict[str, Any]) -> dict[str, Any]:
        result = registry.call(name, args)
        print(registry.events[-1].model_dump_json(), file=sys.stderr, flush=True)
        return result

    @server.tool()
    def list_files(repository: str = "target") -> dict[str, Any]:
        """List up to 250 authorized text files, excluding private paths."""
        return invoke("list_files", {"repository": repository})

    @server.tool()
    def read_file(path: str, repository: str = "target") -> dict[str, Any]:
        """Read at most 32 KiB from a canonical authorized relative text path."""
        return invoke("read_file", {"path": path, "repository": repository})

    @server.tool()
    def search_code(query: str, repository: str = "target") -> dict[str, Any]:
        """Literal text search, at most 50 matches; regex execution is unavailable."""
        return invoke("search_code", {"query": query, "repository": repository})

    @server.tool()
    def read_manifest(path: str, repository: str = "target") -> dict[str, Any]:
        """Read a permitted manifest filename with the normal read restrictions."""
        return invoke("read_manifest", {"path": path, "repository": repository})

    @server.tool()
    def inspect_dependencies(repository: str = "target") -> dict[str, Any]:
        """Check exact Python pins against the repository's local advisory fixture."""
        return invoke("inspect_dependencies", {"repository": repository})

    @server.tool()
    def inspect_git_diff(repository: str = "target") -> dict[str, Any]:
        """Read an optional pinned changes.diff; never execute git or its hooks."""
        return invoke("inspect_git_diff", {"repository": repository})

    @server.tool()
    def get_repository_metadata(repository: str = "target") -> dict[str, Any]:
        """Return alias, authorized file count and read-only status."""
        return invoke("get_repository_metadata", {"repository": repository})

    return server


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default="SEC-001")
    args = parser.parse_args()
    scenario = next((s for s in discover() if s.id == args.scenario), None)
    if scenario is None:
        parser.error("Unknown authorized scenario")
    assert scenario is not None
    create_server(Registry(scenario.repository, scenario.tools)).run(transport="stdio")


if __name__ == "__main__":
    main()
