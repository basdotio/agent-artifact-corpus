#!/usr/bin/env python3
"""Write Connor's proof-of-concept MCP servers into cache/ as one tree per server.

WHAT THE SOURCE IS. yiheng98/Connor, the artifact of arXiv:2604.01905 ("From Component
Manipulation to System Compromise: Understanding and Detecting Malicious MCP Servers"): 114
MCP servers the authors wrote by hand, each a small working tool server with one attack planted
in one of its components. They sit in six directories named after what the attack is for
(backdoor, payload execution, ransomware, reverse shell, stealing, sabotaging), each with
p1..p19, the component the attack was planted through. Every sample is `synthetic`: written to
demonstrate an attack, never found in a registry.

WHAT IS TAKEN. Only `PoCs/<goal>_PoC/p<N>/` — `main.py`, `mcp.json`, `pyproject.toml`, copied
unchanged. `PoCs/` is Apache-2.0 and carries a NOTICE that every copy must keep; it is reproduced
in this repository's NOTICE. `Dataset/` is third-party material under its upstreams' terms, some
with no licence, and is not read here. `PoCs/response/` holds two web pages and a script that an
attacker's own web server would hand back to the servers that fetch from it; they are not part of
any server tree and are left out, so a server whose attack arrives in that response shows the
fetch and not the payload.

NAMES. A tree is named `srv-<first 10 hex of a sha256 over its three files>`, never by the
upstream path: `stealing_PoC/p7` carries what the attack is for, and a path-aware harness would
read the label off the directory name. The hash covers all three files because the p19 servers
of several goals share one `main.py` and differ only in `mcp.json`, where their attack is. The
upstream path is in the sidecar `<name>.source.json`, beside the tree and never inside it.

Nothing here runs any of the code.
"""

import hashlib
import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPO = ROOT / "cache" / "connor" / "repo"
OUT = ROOT / "cache" / "connor" / "_extracted"
COMMIT = "326ab9116699442d2744b445b38c69524fbf43e6"   # manifest/corpora.yaml
FILES = ("main.py", "mcp.json", "pyproject.toml")


def main() -> int:
    pocs = REPO / "PoCs"
    if not pocs.is_dir():
        sys.exit(f"clone https://github.com/yiheng98/Connor at {COMMIT} into {REPO.relative_to(ROOT)} first")
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    n, seen = 0, {}
    for goal_dir in sorted(p for p in pocs.iterdir() if p.is_dir() and p.name.endswith("_PoC")):
        for poc in sorted(goal_dir.iterdir(), key=lambda p: int(re.sub(r"\D", "", p.name) or 0)):
            if not poc.is_dir():
                continue
            have = sorted(f.name for f in poc.iterdir())
            if have != sorted(FILES):
                sys.exit(f"{poc.relative_to(REPO)}: expected {sorted(FILES)}, found {have}")
            h = hashlib.sha256()
            for f in FILES:                                   # name, NUL, bytes, NUL: unambiguous
                h.update(f.encode() + b"\0" + (poc / f).read_bytes() + b"\0")
            digest = h.hexdigest()
            name = f"srv-{digest[:10]}"
            upstream = str(poc.relative_to(REPO))
            if name in seen:
                sys.exit(f"{upstream} and {seen[name]} are the same three files")
            seen[name] = upstream
            tree = OUT / name
            tree.mkdir()
            for f in FILES:
                shutil.copyfile(poc / f, tree / f)
            side = {"upstream_path": upstream,
                    "goal": goal_dir.name[: -len("_PoC")],     # the upstream's own spelling, typos included
                    "component": poc.name,
                    "sha256_tree": digest,
                    "source": f"https://github.com/yiheng98/Connor/tree/{COMMIT[:12]}/{upstream}"}
            (OUT / f"{name}.source.json").write_text(json.dumps(side, indent=1) + "\n")
            n += 1
    print(f"connor: {n} server tree(s) into {OUT.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
