"""Start the GA4GH MCP server with its upstream HTTP going through the HTTP cassette.

Run with the MCP server's own Python, and this repository on PYTHONPATH:

    BENCH_HTTP_CASSETTE=cassettes/http.jsonl BENCH_HTTP_MODE=replay-or-record \\
        <mcp venv>/bin/python -m benchmark.mcp_launch --registry ...

Everything after the module name is passed to the server unchanged. The MCP repositories are not
modified; the cassette is installed in this process before the server starts.
"""

from __future__ import annotations

import atexit
import os
import sys
from pathlib import Path

from . import dns_cache
from .http_cassette import install


def main() -> int:
    cassette_path = Path(os.environ["BENCH_HTTP_CASSETTE"])
    dns_cache.install(cassette_path.with_name("dns.json"))
    cassette = install(cassette_path, os.environ.get("BENCH_HTTP_MODE", "replay-or-record"))
    atexit.register(lambda: print(f"[http-cassette] {cassette.stats}", file=sys.stderr, flush=True))
    from ga4gh_mcp.__main__ import main as server_main
    sys.argv = ["ga4gh-mcp", *sys.argv[1:]]
    return server_main() or 0


if __name__ == "__main__":
    sys.exit(main())
