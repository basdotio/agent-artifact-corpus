import json
import os
from datetime import datetime, timezone


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


class State:
    """One writer per directory. Atomic checkpoints; never exposed as a tool."""
    def __init__(self, directory, identity):
        self.directory = directory
        self.path = directory / "progress.json"
        self.data = json.loads(self.path.read_text("utf-8")) if self.path.exists() else {
            "version": 1, "identity": identity, "status": "running", "cache": {}, "attempts": {},
            "evidence": {}, "events": [], "messages": [], "pending": [], "round": 0,
            "tool_calls": 0, "failure_consumed": False,
        }
        if self.data["identity"] != identity:
            raise ValueError("Run configuration or dataset changed. Use a new --run-dir.")
        self.save()

    def save(self):
        write_json(self.path, self.data)

    def event(self, kind, **details):
        self.data["events"].append({"at": datetime.now(timezone.utc).isoformat(), "kind": kind, **details})
        self.save()
