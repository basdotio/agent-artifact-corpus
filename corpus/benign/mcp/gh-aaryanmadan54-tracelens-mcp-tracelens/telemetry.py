"""Reads only bundled telemetry. No dynamic paths, SQL, URLs or mutations."""
import hashlib
import json
from copy import deepcopy
from datetime import datetime
from importlib.resources import files
START = "2026-04-18T10:00:00Z"
END = "2026-04-18T10:30:00Z"


def load_dataset():
    return json.loads(files("tracelens").joinpath("data/telemetry.json").read_text("utf-8"))


def dataset_digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return parsed


def window(start, end):
    a, b = timestamp(start), timestamp(end)
    if a >= b or (b-a).total_seconds() > 3600:
        raise ValueError("Use a nonempty time window of at most one hour")
    return a, b


class Telemetry:
    def __init__(self, data=None):
        self._data = deepcopy(data if data is not None else load_dataset())

    def select(self, kind, service, start, end, limit):
        a, b = window(start, end)
        records = []
        for row in self._data[kind]:
            if row["service"] != service:
                continue
            match = (a <= timestamp(row["start"]) and timestamp(row["end"]) <= b) if kind == "metrics" else a <= timestamp(row["timestamp"]) < b
            if match:
                records.append(row)
        return {"synthetic": True, "trust": "untrusted_telemetry", "records": deepcopy(records[:limit]), "truncated": len(records) > limit}
