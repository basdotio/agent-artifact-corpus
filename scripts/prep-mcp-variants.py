#!/usr/bin/env python3
"""Write the licence-clean malicious MCP variants into cache/ as one tree per variant.

WHAT THE SOURCE IS. yms0527/awesome-mcp-servers carries 190 malicious MCP variants: an attack of
one of 15 types INJECTED into a real open-source MCP server, the server's directory name kept.
They are `injected` samples — real server code plus an inserted attack — never wild.

WHY ONLY SOME. The repository is MIT, but each variant is a modified copy of somebody else's
server, and the repository's licence cannot grant what the server's author did not. A variant is
taken only when its own tree carries the base server's licence file and that licence is MIT,
Apache-2.0, BSD or ISC (103 of 190 at the pinned commit). No-licence, copyleft and unknown ones
are left out. The licence each tree carries is written to manifest/pins/mcp-variants-licenses.json
so derive labels every sample with the base server's licence, not the repository's.

EMPTY VARIANTS. 13 of the 20 Tool Poisoning variants are gitlinks with no .gitmodules: the authors
committed nested repositories by accident, so the dataset ships a commit id and no files. Those are
skipped; nothing of the attack is published.

RECOVERED LICENCES. Seven variants ship no licence file although their base server's own
repository carries a permissive one (looked up 2026-11-02 for the attack types still below the
cap). For those the upstream LICENSE text, fetched from that repository, is written into the tree
as LICENSE — the one file added to a vendored tree here, because MIT and Apache-2.0 both require
the licence to travel with a copy — and the sidecar names where it came from.

NAMES. `<attack-type-slug>--<server dir>`: the same server can carry two attack types, and the
attack directories have spaces in them. The sidecar `<name>.source.json` sits beside the tree,
never inside it, with the attack type, impact, base server and licence from the upstream's own
variant_name_mapping.csv.

Trees are copied unchanged. Nothing here runs any of the code.
"""

import csv
import json
from datetime import date
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPO = ROOT / "cache" / "mcp-variants" / "repo"
OUT = ROOT / "cache" / "mcp-variants" / "_extracted"
PINS = ROOT / "manifest" / "pins" / "mcp-variants-licenses.json"
COMMIT = "e8303ec7a14dd336489c88d798140dd3faf1a6cf"   # manifest/corpora.yaml

LICENCES = [  # (spdx, a phrase only that licence's text carries)
    ("MIT", r"Permission is hereby granted, free of charge"),
    ("Apache-2.0", r"Apache License,?\s+Version 2\.0"),
    ("BSD-3-Clause", r"Neither the name of"),
    ("BSD-2-Clause", r"Redistribution and use in source and binary forms"),
    ("ISC", r"Permission to use, copy, modify, and/or distribute"),
]
COPYLEFT = r"GNU (AFFERO |LESSER )?GENERAL PUBLIC LICENSE|Mozilla Public License"

# variant directory -> (spdx, base server repository): no licence file in the tree, a permissive
# one at the base server's repository (its default branch, 2026-11-02)
RECOVERED = {
    "jonnadul_mcpsshclient": ("MIT", "jonnadul/mcpsshclient"),
    "ssh-exec": ("MIT", "pathintegral-institute/mcp.science"),
    "well-architected-security-mcp-server": ("Apache-2.0", "awslabs/mcp"),
    "MatthewDailey_mcp-starter": ("Unlicense", "MatthewDailey/mcp-starter"),
    "materials-project": ("MIT", "pathintegral-institute/mcp.science"),
    "graphiti-mcp": ("Apache-2.0", "getzep/graphiti"),
}


def upstream_licence(repo: str) -> str:
    """The licence text GitHub serves for a repository's default branch."""
    import base64
    import urllib.request
    with urllib.request.urlopen(f"https://api.github.com/repos/{repo}/license") as r:
        return base64.b64decode(json.load(r)["content"]).decode()


def licence_of(tree: pathlib.Path) -> str | None:
    for f in sorted(tree.iterdir()):
        if f.is_file() and re.match(r"(?i)(licen[cs]e|copying)(\.|$)", f.name):
            text = f.read_text(errors="ignore")[:4000]
            if re.search(COPYLEFT, text):
                return None
            for spdx, phrase in LICENCES:
                if re.search(phrase, text, re.I):
                    return spdx
    return None


def main() -> int:
    if not REPO.is_dir():
        sys.exit(f"clone https://github.com/yms0527/awesome-mcp-servers at {COMMIT} into {REPO.relative_to(ROOT)} first")
    rows = list(csv.DictReader(open(REPO / "malicious-mcp-variants" / "variant_name_mapping.csv")))
    if OUT.exists():   # a stale tree from an earlier run would be derived as if it were current
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    pins, skipped = {}, 0
    for r in rows:
        src = REPO / "malicious-mcp-variants" / r["attack_directory"] / r["labelled_variant_directory"]
        if not src.is_dir() or not any(f.is_file() for f in src.rglob("*")):
            skipped += 1   # an empty gitlink: the variant's files were never published
            continue
        lic = licence_of(src)
        rec = RECOVERED.get(r["labelled_variant_directory"]) if lic is None else None
        if rec:
            lic = rec[0]
        if lic is None:
            skipped += 1
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", r["attack_directory"].lower()).strip("-")
        name = f"{slug}--{r['labelled_variant_directory']}"
        dst = OUT / name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, symlinks=True)
        if rec:
            (dst / "LICENSE").write_text(upstream_licence(rec[1]))
        side = {"attack_type": r["attack_directory"], "impact": r["final_impact_location"],
                "base_server": r["original_server_name"], "base_licence": lic,
                "source": f"https://github.com/yms0527/awesome-mcp-servers/tree/{COMMIT[:12]}/malicious-mcp-variants/"
                          f"{r['attack_directory']}/{r['labelled_variant_directory']}"}
        if rec:
            side["licence_recovered_from"] = f"https://github.com/{rec[1]} (LICENSE added to the tree)"
        (OUT / f"{name}.source.json").write_text(json.dumps(side, indent=1) + "\n")
        pins[name] = {"checked": str(date.today()), "license": lic,
                      "via": (f"the base server's repository https://github.com/{rec[1]}; its LICENSE added to the tree"
                              if rec else "the base server's licence file inside the variant tree")}
    PINS.write_text(json.dumps(dict(sorted(pins.items())), indent=2) + "\n")
    print(f"mcp-variants: {len(pins)} licence-clean variant(s) into {OUT.relative_to(ROOT)}/, "
          f"{skipped} left out (empty, no licence found, copyleft or unrecognised); pins in {PINS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
