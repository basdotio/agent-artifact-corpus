"""Read the packaged training reference without touching athlete state."""
import hashlib
import json
from pathlib import Path


def training_reference():
    root = Path(__file__).with_name("resources") / "garmin-browser-tools" / "references"
    raw = (root / "training.md").read_bytes()
    source = json.loads((root / "training-source.json").read_text())
    if hashlib.sha256(raw).hexdigest() != source["sha256"]:
        raise ValueError("training_reference_integrity_mismatch")
    return {"source": source, "text": raw.decode("utf-8"),
            "athlete_context_loaded": False, "current_plan_loaded": False}
