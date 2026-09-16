#!/usr/bin/env python3
import hashlib, json
from pathlib import Path
def get_hashes(filepath):
    data = Path(filepath).read_bytes()
    return {"md5": hashlib.md5(data).hexdigest(), "sha256": hashlib.sha256(data).hexdigest()}
if __name__ == "__main__":
    import sys; print(json.dumps(get_hashes(sys.argv[1]) if len(sys.argv)>1 else {"error": "No file provided"}, indent=2))
