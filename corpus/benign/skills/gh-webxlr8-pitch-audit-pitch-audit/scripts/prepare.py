#!/usr/bin/env python3
"""One command to prepare everything the deck needs for a prospect, as fast as possible.

Usage:
    python3 prepare.py <url> clients/<slug> [--speed auto|psi|local|off]

Runs in parallel:   audit.py (site checks + speed tests)  ||  prospect_assets.py (their logo + photos)
Then:               filmstrip from the speed test, score.py, one generated background.
Exit code 2 = site unreachable or parked (confirm the URL with the user).
Afterwards: write research.md + manual.json, re-run score.py, write deck-data.json, run build.py.
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def py(script, *args, quiet=False):
    return subprocess.Popen([sys.executable, os.path.join(HERE, script), *args],
                            stdout=subprocess.DEVNULL if quiet else None, stderr=subprocess.DEVNULL if quiet else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("client_dir")
    ap.add_argument("--speed", default="auto", choices=["auto", "psi", "local", "off"])
    a = ap.parse_args()
    os.makedirs(a.client_dir, exist_ok=True)
    t0 = time.time()
    audit = py("audit.py", a.url, "--out", a.client_dir, "--speed", a.speed)
    assets = py("prospect_assets.py", a.client_dir, a.url, "--no-filmstrip")
    rc = audit.wait()
    assets.wait()
    if rc == 2:
        print("\nSite unreachable or parked: confirm the URL before pitching.")
        sys.exit(2)
    if rc != 0:
        sys.exit(f"audit failed (exit {rc})")
    for p in (py("prospect_assets.py", a.client_dir, "--filmstrip-only"), py("backgrounds.py", a.client_dir, "--count", "1", quiet=True)):
        p.wait()
    py("score.py", a.client_dir).wait()
    print(f"\nPrepared in {time.time() - t0:.0f}s. Next: research.md + manual.json → score.py → deck-data.json → build.py")


if __name__ == "__main__":
    main()
