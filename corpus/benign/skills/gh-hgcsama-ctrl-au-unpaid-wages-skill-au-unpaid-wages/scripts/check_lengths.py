#!/usr/bin/env python3
"""Check FWO enquiry field drafts against the form's character limits.

Usage: python check_lengths.py drafts/fwo-enquiry-fields.md

Reads fenced code blocks that follow a heading line containing "(max N)" and reports the
length of each block against N. Exit status 1 if any block is over its limit.
"""
import re
import sys
from pathlib import Path

LIMIT_RE = re.compile(r"\(max\s+(\d+)\)")


def main(path: str) -> int:
    text = Path(path).read_text(encoding="utf-8")
    lines = text.splitlines()
    i, over, found = 0, 0, 0
    pending_label, pending_limit = None, None
    while i < len(lines):
        line = lines[i]
        m = LIMIT_RE.search(line)
        if m:
            pending_label = line.strip().lstrip("-# ").split("(max")[0].strip(" :")
            pending_limit = int(m.group(1))
        elif line.strip().startswith("```") and pending_limit is not None:
            j = i + 1
            block = []
            while j < len(lines) and not lines[j].strip().startswith("```"):
                block.append(lines[j])
                j += 1
            body = "\n".join(block).strip()
            n = len(body)
            status = "OK " if n <= pending_limit else "OVER"
            if n > pending_limit:
                over += 1
            found += 1
            print(f"{status} {n:>5}/{pending_limit:<5} {pending_label}")
            pending_label, pending_limit = None, None
            i = j
        i += 1
    if not found:
        print("no '(max N)' blocks found")
    return 1 if over else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
