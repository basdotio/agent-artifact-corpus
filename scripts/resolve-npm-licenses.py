#!/usr/bin/env python3
"""Resolve the licence of every npm PACKAGE behind the automatelab tool-catalogue samples.

The automatelab dataset is CC-BY-4.0 for its additions; each tool row is attributed to the
upstream package, which keeps its own licence. For 357 trees the label's origin.license was the
dataset's, which is the wrong field for layer 1's rule (docs/licensing.md). This reads
`package` from each tree's tools.json, asks registry.npmjs.org for the package's `license`
field, and writes manifest/pins/npm-licenses.json keyed by tree name. The derive rule reads
that file through `license_from`, so a re-derivation reproduces the labels without a network.

Red line 2: the summary names how many packages fall outside the permissive set, with both
figures, because those samples leave the denominator.

Usage: scripts/resolve-npm-licenses.py [--refresh] [--apply]
  --apply rewrites origin.license in the am-* labels from the pins file
"""
import concurrent.futures
import datetime
import json
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PINS = ROOT / "manifest" / "pins" / "npm-licenses.json"
TREES = ROOT / "corpus" / "benign" / "mcp"
PERMISSIVE = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "CC0-1.0",
              "CC-BY-4.0", "Unlicense", "0BSD", "MIT-0", "Zlib"}


def one(pkg: str) -> tuple[str, str]:
    url = "https://registry.npmjs.org/" + urllib.parse.quote(pkg, safe="@")
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        return pkg, "NOT_FOUND" if e.code == 404 else f"HTTP{e.code}"
    except Exception:
        return pkg, "ERROR"
    lic = d.get("license")
    if lic is None:
        latest = d.get("dist-tags", {}).get("latest", "")
        lic = d.get("versions", {}).get(latest, {}).get("license")
    if isinstance(lic, dict):
        lic = lic.get("type")
    if isinstance(lic, list):
        lic = "/".join(str(x.get("type", x)) if isinstance(x, dict) else str(x) for x in lic)
    return pkg, str(lic or "NONE")


def apply(trees: dict[str, str], pins: dict[str, dict]) -> int:
    """Rewrite origin.license in every am-* label from the pins file — what `corpus derive
    --write` would produce once the parquet is fetched. Only the one line changes."""
    changed = 0
    for name in trees:
        lic = pins.get(name, {}).get("license")
        if not lic:
            continue
        f = TREES / f"am-{name}.yaml"
        lines = f.read_text().splitlines(keepends=True)
        for i, line in enumerate(lines):
            if line.startswith("  license: "):
                if line != f"  license: {lic}\n":
                    lines[i] = f"  license: {lic}\n"
                    f.write_text("".join(lines))
                    changed += 1
                break
    return changed


def main() -> int:
    refresh = "--refresh" in sys.argv
    trees = {}
    for d in sorted(TREES.glob("am-*/")):
        trees[d.name[len("am-"):]] = json.loads((d / "tools.json").read_text())["package"]
    pins = json.loads(PINS.read_text()) if PINS.exists() and not refresh else {}
    todo = sorted({pkg for name, pkg in trees.items() if name not in pins})
    print(f"{len(trees)} trees, {len(todo)} packages to resolve", file=sys.stderr)
    if todo:
        today = datetime.date.today().isoformat()
        with concurrent.futures.ThreadPoolExecutor(8) as ex:
            got = dict(ex.map(one, todo))
        for name, pkg in trees.items():
            if name not in pins:
                pins[name] = {"package": pkg, "license": got[pkg], "checked": today,
                              "via": "npm-registry"}
        PINS.write_text(json.dumps(dict(sorted(pins.items())), indent=2) + "\n")

    if "--apply" in sys.argv:
        print(f"applied: {apply(trees, pins)} label(s) changed", file=sys.stderr)

    tally: dict[str, int] = {}
    outside = 0
    for name in trees:
        lic = pins.get(name, {}).get("license", "?")
        tally[lic] = tally.get(lic, 0) + 1
        if lic not in PERMISSIVE:
            outside += 1
    print("\ntrees by package licence:")
    for lic, n in sorted(tally.items(), key=lambda kv: -kv[1]):
        print(f"  {lic:<40} {n:>4}{'' if lic in PERMISSIVE else '   <- outside layer 1'}")
    t = len(trees)
    print(f"\n{t} trees; {t - outside} on permissive packages, {outside} not ({outside / t:.1%}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
