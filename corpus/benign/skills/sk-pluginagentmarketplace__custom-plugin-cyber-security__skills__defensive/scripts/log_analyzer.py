#!/usr/bin/env python3
import re, json
INDICATORS = {"failed_login": r"failed|invalid password", "privilege_escalation": r"sudo|su\s+-|escalat", "suspicious_ip": r"\b(?:\d{1,3}\.){3}\d{1,3}\b"}
def analyze(log):
    return {k: len(re.findall(v, log, re.I)) for k, v in INDICATORS.items()}
if __name__ == "__main__":
    import sys; print(json.dumps(analyze(open(sys.argv[1]).read() if len(sys.argv)>1 else sys.stdin.read()), indent=2))
