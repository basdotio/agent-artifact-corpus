#!/usr/bin/env python3
"""Vendor the malicious npm MCP servers selected from DataDog's dataset.

Why this exists, and why it is not prep-datadog.py. prep-datadog.py unpacks the flat
samples/ai-skills tree — one directory per sample, one zip inside. The npm subset of the same
upstream is shaped differently: samples/npm/malicious_intent/<package>/<version>/<dated>.zip,
many versions per package. Folding that into the ai-skills script would make its one-sample /
one-zip contract false. So the npm fetch and selection live here.

WHAT IS SELECTED, AND WHY SO FEW. 1,000+ packages carry the malicious_intent flag; ~128 have an
agent-ish name; this keeps SEVEN. Every one was read (two model passes, then the deciding quote
located in the bytes here) and kept only if it is BOTH a real MCP server AND genuinely malicious.
The rest were either generic npm malware wearing an mcp-ish name (a dropper, a /etc/passwd
preinstall, a wallet stealer — real, but not an MCP server and not on a surface this corpus has),
or clean republishes flagged by mistake (airtable-mcp, a benign WaterCrawl republish — distinct
from the malicious @iflow-mcp WaterCrawl fork kept below). Ten of thousands filtered to seven is
the honest size of "malicious MCP servers in the wild, captured".

ONE VERSION PER PACKAGE. A package ships many versioned zips; they are near-duplicates and
`corpus validate` refuses those. The version carrying the payload is pinned by hand below — not
"highest version" blindly, because the malice is not always in the latest tag.

These are LIVE malware. This script only copies already-extracted bytes; it never executes them.
Extraction (unzip with the `infected` password) is done once by hand into
cache/datadog-npm-mcp/_extracted/ and is not repeated here.
"""

import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "cache" / "datadog-npm-mcp" / "_extracted"
DEST = ROOT / "corpus" / "malicious" / "mcp"

# cache-dir-name -> vendored sample id. Only the five keepers; the cache holds more that were
# read and rejected, and listing exactly these is what keeps a rejected one from drifting in.
KEEPERS = {
    "lanyer640mcp-runcommand-server": "dd-npm-lanyer640-runcommand-revshell",
    "inscadamcp-server": "dd-npm-inscada-telemetry-exfil",
    "birdmania1namecheap-mcp": "dd-npm-namecheap-affiliate-injection",
    "mcp-server-fixthis": "dd-npm-fixthis-exchange-exfil",
    "mcp-server-todo": "dd-npm-todo-wallet-exfil",
    "iflow-mcpwatercrawl-watercrawl-mcp": "dd-npm-iflow-watercrawl-hidden-eval",
    "excluder-mcp": "dd-npm-excluder-env-exfil",
}


def main() -> int:
    if not SRC.is_dir():
        print(f"not extracted: {SRC.relative_to(ROOT)} does not exist", file=sys.stderr)
        return 1
    done = missing = 0
    for cache_name, sample_id in KEEPERS.items():
        src = SRC / cache_name
        if not src.is_dir():
            print(f"  {cache_name}: not in cache", file=sys.stderr)
            missing += 1
            continue
        out = DEST / sample_id
        if out.exists():
            shutil.rmtree(out)
        shutil.copytree(src, out)
        done += 1
        print(f"  {sample_id} <- {cache_name}")
    print(f"vendored {done} npm MCP server(s) into {DEST.relative_to(ROOT)}")
    if missing:
        print(f"{missing} missing — re-extract the cache", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
