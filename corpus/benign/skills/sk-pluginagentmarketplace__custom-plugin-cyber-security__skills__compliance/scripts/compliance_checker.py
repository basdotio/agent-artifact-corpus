#!/usr/bin/env python3
import json
from pathlib import Path
REQUIRED_DOCS = ["security_policy.md", "incident_response.md", "access_control.md"]
def check(path):
    p = Path(path)
    return {doc: (p/doc).exists() for doc in REQUIRED_DOCS}
if __name__ == "__main__":
    import sys; print(json.dumps(check(sys.argv[1] if len(sys.argv)>1 else "."), indent=2))
