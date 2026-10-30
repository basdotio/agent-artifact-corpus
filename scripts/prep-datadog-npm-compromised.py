#!/usr/bin/env python3
"""Vendor the supply-chain-compromised agent packages selected from DataDog's dataset.

Why this exists, and why it is not prep-datadog-npm.py. That script vendors
samples/npm/malicious_intent — packages a bad actor published to BE malware. This one vendors
samples/npm/compromised_lib — real, published agent packages whose a specific version was
supply-chain-compromised to run an attacker payload at install or plugin-load time, while the
package's advertised function stays intact. Different pool, different provenance story, so the
selection lives in its own script.

WHAT IS SELECTED. Every compromised_lib package with an agent/MCP/skill name was read; these
FIVE are the ones a majority of readers called malicious, deduplicated by payload. Three were
kept on two-model agreement. Two more came in on 2026-10-30 under the majority rule, when a third
reader (Claude, with file search) found what the truncated first reading could not: one carrier
of the "Shai-Hulud" Bun worm (@postman/postman-mcp-server, whose setup_bun.js and
bun_environment.js are byte-identical in browserbase/mcp, mcp-use and ~10 others, all left out)
and one of the redhat hcc-*-mcp worm (hcc-kessel-mcp; hcc-pf-mcp is the same family and is left
out). mcp-knowledge-base shares mcp-knowledge-graph's bundle.js byte for byte and is left out.

ONE VERSION PER PACKAGE, pinned by hand below to the version that carries the payload.

These are LIVE malware. This script only copies already-extracted bytes; it never executes them.

NO EXECUTABLE BINARIES ARE VENDORED. memtensor ships a per-platform `sckit` stage-zero binary
under `.sckit/<os>-<arch>/`; those are the actual payload and are NOT copied (the dict value's
`strip_binaries` drops them). What is kept is the readable loader (`lib/sckit.js`) that spawns
them and the base64 config it passes — the harm the label quotes — plus `.sckit/ca-roots.pem`,
which is an inert certificate bundle. The two npm-server payloads (antv's obfuscated index.js,
the knowledge-graph bundle.js) are text and are kept as written, as the malicious_intent trees
keep theirs.
"""

import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "cache" / "datadog-npm-compromised" / "_extracted"

# cache-dir-name -> (destination surface dir, vendored sample id, strip_binaries)
KEEPERS = {
    "antvmcp-server-chart": ("mcp", "dd-npm-antv-mcp-chart-preinstall", False),
    "mcp-knowledge-graph": ("mcp", "dd-npm-knowledge-graph-workflow-exfil", False),
    "memtensormemos-cloud-openclaw-plugin": ("connector", "dd-npm-memtensor-openclaw-stage0", True),
    "postmanpostman-mcp-server": ("mcp", "dd-npm-postman-mcp-shai-hulud", False),
    "redhat-cloud-serviceshcc-kessel-mcp": ("mcp", "dd-npm-redhat-kessel-mcp-worm", False),
}

# Executable stage-zero binaries that must never be vendored, by basename.
BINARY_NAMES = {"sckit", "sckit.exe"}


def copy_tree(src: pathlib.Path, dst: pathlib.Path, strip_binaries: bool) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    def ignore(_dir: str, names: list[str]) -> set[str]:
        return {n for n in names if n in BINARY_NAMES} if strip_binaries else set()
    shutil.copytree(src, dst, ignore=ignore)


def main() -> int:
    if not SRC.is_dir():
        print(f"not extracted: {SRC.relative_to(ROOT)} does not exist", file=sys.stderr)
        return 1
    done = missing = 0
    for cache_name, (surface_dir, sample_id, strip_binaries) in KEEPERS.items():
        src = SRC / cache_name
        if not src.is_dir():
            print(f"  {cache_name}: not in cache", file=sys.stderr)
            missing += 1
            continue
        dst = ROOT / "corpus" / "malicious" / surface_dir / sample_id
        copy_tree(src, dst, strip_binaries)
        # Guard: no executable stage-zero binary may reach the corpus.
        leaked = [p for p in dst.rglob("*") if p.name in BINARY_NAMES]
        if leaked:
            print(f"  {sample_id}: REFUSING — binary leaked: {leaked}", file=sys.stderr)
            shutil.rmtree(dst)
            return 1
        done += 1
        print(f"  corpus/malicious/{surface_dir}/{sample_id} <- {cache_name}"
              + (" (binaries stripped)" if strip_binaries else ""))
    print(f"vendored {done} compromised agent package(s)")
    if missing:
        print(f"{missing} missing — re-extract the cache", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
