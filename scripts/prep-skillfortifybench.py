#!/usr/bin/env python3
"""Write SkillFortifyBench's malicious samples into cache/ as one tree per sample.

WHAT THE SOURCE IS. qualixar/skillfortifybench: 540 skills generated deterministically from
seed 42 by the authors of arXiv:2603.00195 — 270 labelled malicious across 13 attack types
(A1-A13) and 270 benign, each in one of three formats: a Claude skill (.md), an MCP config
(mcp.json) and an OpenClaw skill (.claw/skill.yaml). Every sample is `synthetic`.

WHY ONLY THE MALICIOUS HALF. The benign half carries no URL, no shell and no credential at
all, so it separates from the malicious half on the presence of any URL; a matched benign set
would only let that shortcut score as precision (docs/design.md, "Shortcut features").

LAYOUT. A Claude skill becomes `<id>/SKILL.md`, the name a skill loader reads; an MCP config
stays `<id>/mcp.json`; an OpenClaw skill keeps its `.claw/` or `.openclaw/` directory. The
contents are copied unchanged; the inline `SKILLFORTIFYBENCH:INERT` banner is removed at
derive time by a declared transform, not here. The sidecar `<id>.source.json` sits beside the
tree with the upstream's own attack type, parent class and path from manifest.json.

NAMES. A tree is named `<format>-<first 10 hex of the upstream sha256>`, never by the upstream id:
`claude_mal_A01_001` carries the class and the attack type, and a path-aware harness would read
the label off the directory name. The upstream id is in the sidecar.

Two entries, because a manifest entry has one surface: cache/skillfortifybench/_extracted/
(Claude and OpenClaw skills) and cache/skillfortifybench-mcp/_extracted/ (MCP configs). Nothing
here runs any of the code.
"""

import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPO = ROOT / "cache" / "skillfortifybench" / "repo"
OUT = {"skills": ROOT / "cache" / "skillfortifybench" / "_extracted",
       "mcp": ROOT / "cache" / "skillfortifybench-mcp" / "_extracted"}
COMMIT = "eb9d5a9cbfa13b82ec3392d26dbae82fc6454b39"   # manifest/corpora.yaml


def main() -> int:
    if not REPO.is_dir():
        sys.exit(f"clone https://github.com/qualixar/skillfortifybench at {COMMIT} into {REPO.relative_to(ROOT)} first")
    entries = json.loads((REPO / "manifest.json").read_text())["entries"]
    for d in OUT.values():
        if d.exists():
            shutil.rmtree(d)
    n = {"skills": 0, "mcp": 0}
    for e in entries:
        if not e["is_malicious"]:
            continue
        src = REPO / e["path"]
        surface = "mcp" if e["format"] == "mcp" else "skills"
        name = f"{e['format']}-{e['sha256'][:10]}"
        tree = OUT[surface] / name
        if e["format"] == "claude":
            dst = tree / "SKILL.md"
        else:  # mcp/<id>/mcp.json, openclaw/<id>/.claw/skill.yaml: keep the path below the id
            dst = tree / pathlib.Path(e["filename"]).relative_to(e["skill_id"]) if "/" in e["filename"] else tree / e["filename"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        side = {"upstream_id": e["skill_id"], "attack_type": e["attack_type"], "parent_class": e["parent_class"], "format": e["format"],
                "source_attribution": e["source_attribution"], "upstream_path": e["path"], "sha256": e["sha256"],
                "source": f"https://github.com/qualixar/skillfortifybench/blob/{COMMIT[:12]}/{e['path']}"}
        (OUT[surface] / f"{name}.source.json").write_text(json.dumps(side, indent=1) + "\n")
        n[surface] += 1
    print(f"skillfortifybench: {n['skills']} skill tree(s) into {OUT['skills'].relative_to(ROOT)}/, "
          f"{n['mcp']} MCP tree(s) into {OUT['mcp'].relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
