#!/usr/bin/env python3
"""One command from deck-data.json to send-ready, verified PDFs.

Usage:
    python3 build.py <client_dir> [--style style-1]

Runs, in order, and stops at the first failure:
  0. lint_deck.py          deck structure, word budget per slide, every number traced to a source
  1. render.py --preview   the one PDF to send (flattened pages + text layer + links), previews/
  2. a11y_check.py         WCAG 2.2 AA colour contrast + non-text contrast; PDF title, text layer, links, size
  3. compat_check.py       flat-page structure check (any OS) + every page rendered by Apple PDFKit (macOS),
                           PDFium and poppler, diffed against the browser reference
Then prints the one file to send.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def step(name, cmd):
    print(f"\n== {name}")
    r = subprocess.run([sys.executable] + cmd)
    if r.returncode != 0:
        print(f"\n✗ {name} FAILED. Fix the issues above, then re-run build.py.")
        sys.exit(r.returncode)
    print(f"✓ {name} passed")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cdir = os.path.abspath(sys.argv[1])
    extra = sys.argv[2:]
    step("Deck lint (structure, word budget, fact-trace)", [os.path.join(HERE, "lint_deck.py"), cdir])
    step("Render", [os.path.join(HERE, "render.py"), cdir, "--preview"] + extra)
    step("Accessibility (WCAG 2.2 AA)", [os.path.join(HERE, "a11y_check.py"), cdir])
    step("Viewer compatibility (structure + PDFKit/PDFium/poppler)", [os.path.join(HERE, "compat_check.py"), cdir])
    pdf = next(os.path.join(cdir, f) for f in sorted(os.listdir(cdir)) if f.endswith(".pdf") and "Summary" not in f)
    print("\nREADY: send this one file on WhatsApp or email")
    print(f"  {pdf}  ({os.path.getsize(pdf) // 1024} KB)")
    print(f"  QA: {os.path.join(cdir, 'previews')}  ·  {os.path.join(cdir, 'a11y', 'report.md')}  ·  {os.path.join(cdir, 'compat', 'report.md')}")


if __name__ == "__main__":
    main()
