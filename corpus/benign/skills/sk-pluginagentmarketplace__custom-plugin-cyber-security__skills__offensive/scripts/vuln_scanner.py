#!/usr/bin/env python3
import re, json
VULNS = {"sqli": r"(SELECT|INSERT|UPDATE|DELETE).*\+.*input", "xss": r"<script>|onerror=|onclick=", "lfi": r"\.\./|\.\.\%2f"}
def scan(code):
    return {k: bool(re.search(v, code, re.I)) for k, v in VULNS.items()}
if __name__ == "__main__":
    import sys; print(json.dumps(scan(open(sys.argv[1]).read() if len(sys.argv)>1 else sys.stdin.read()), indent=2))
