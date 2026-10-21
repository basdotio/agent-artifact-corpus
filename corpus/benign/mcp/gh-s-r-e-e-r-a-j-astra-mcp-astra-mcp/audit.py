
# Developer: Sreeraj
# GitHub: https://github.com/s-r-e-e-r-a-j

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def write_audit(path: str, event: dict[str, object]) -> None:
    destination = Path(path).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), **event}
    descriptor = os.open(destination, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=True) + "\n")
