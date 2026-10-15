"""Development smoke evaluation, explicitly not an independent scientific benchmark."""
import json
import platform
import statistics
import time
from pathlib import Path
from .core import digest
from .demo import fixtures


def run(engine, path=None):
    cases = json.loads(Path(path).read_text()) if path else fixtures()
    if not isinstance(cases, list) or not cases:
        raise ValueError("Benchmark must be a nonempty list of labeled requests.")
    for case in cases:
        if case.get("expected") not in case.get("choices", {}):
            raise ValueError("Every benchmark label must be one of its choices.")
    engine.decide({**cases[0], "bypass_cache": True})  # warm-up, not scored
    rows = []
    for case in cases:
        result = engine.decide({**case, "bypass_cache": True})
        rows.append({"id": case["id"], "group": case.get("group", "custom"),
                     "expected": case["expected"], "correct": result["proposal"] == case["expected"], **result})
    accepted = [r for r in rows if r["status"] == "passes_policy"]
    times = sorted(r["latency_ms"] for r in rows)
    return {"evaluation_kind": "User-supplied evaluation" if path else "Synthetic development smoke test; labels authored during implementation, not expert validated or held out",
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "dataset_sha256": digest(cases), "machine": platform.platform(), "backend": engine.backend.identity,
            "cases": len(rows), "raw_accuracy": sum(r["correct"] for r in rows) / len(rows),
            "policy_coverage": len(accepted) / len(rows),
            "accuracy_among_policy_passes": sum(r["correct"] for r in accepted) / len(accepted) if accepted else None,
            "wrong_policy_passes": sum(not r["correct"] for r in accepted),
            "median_ms": statistics.median(times), "p95_ms": times[max(0, __import__('math').ceil(len(times)*0.95)-1)],
            "cloud_calls": 0, "jev_comparison": "not run", "measured_cloud_token_savings": None,
            "timing_scope": "Warmed engine calls; no model loading, network, UI or human review time. Cache bypassed.",
            "rows": rows}
