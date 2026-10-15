from __future__ import annotations

import json
import time

import httpx
import numpy as np

from .config import DATA

CRITERIA = {
    "brighter": "Increase treble or brightness; sound is dark or muffled",
    "darker": "Reduce treble or brightness; sound is harsh or too bright",
    "gain_up": "Increase distortion, drive or sustain",
    "gain_down": "Reduce distortion or drive; make sound cleaner",
    "modulation_up": "Increase pitch modulation or swirling effect",
    "modulation_down": "Reduce pitch modulation or swirling effect",
    "delay_up": "Increase delay or echo",
    "delay_down": "Reduce delay or echo",
    "accept": "User is satisfied and wants to keep this tone",
    "other": "None applies, ambiguous or unrelated feedback",
}
EXAMPLES = {
    "brighter": ["Too muffled", "More top end please", "Make it brighter", "Needs more treble"],
    "darker": ["Too bright", "Reduce the harshness", "Less treble", "It sounds piercing"],
    "gain_up": ["More distortion", "Needs more drive", "Add gain", "More saturated please"],
    "gain_down": ["Too distorted", "Make it cleaner", "Less gain", "Reduce the drive"],
    "modulation_up": ["More swirling", "More pitch modulation", "Increase the chorus effect", "More warble"],
    "modulation_down": [
        "Less swirling",
        "Too much pitch modulation",
        "Reduce the chorus effect",
        "Less warble",
    ],
    "delay_up": ["More echo", "Increase delay mix", "Needs more repeats", "Add delay"],
    "delay_down": ["Less echo", "Reduce delay mix", "Too many repeats", "Remove some delay"],
    "accept": ["This is good enough", "Keep this tone", "I am happy with this", "Save this sound"],
    "other": ["What is the weather?", "Hello", "It is different somehow", "Play the next song"],
}


def decide(text: str, model: str | None = None) -> dict:
    model = model or status().get("model", "tev1:0.8b")
    with httpx.Client(timeout=30) as client:
        response = client.post(
            "http://127.0.0.1:11434/v1/systemone",
            json={
                "model": model,
                "state": {"feedback": text[:500]},
                "keep_alive": "10m",
                "questions": {
                    "adjustment": {
                        "type": "choice",
                        "instructions": "Classify guitar tone feedback.",
                        "criteria": CRITERIA,
                    }
                },
            },
        )
        response.raise_for_status()
        result = response.json()["answers"]["adjustment"]
        if result["choice"] not in CRITERIA:
            raise ValueError("Decision model returned an unknown category")
        return result


def benchmark(model: str = "tev1:0.8b") -> dict:
    # Warm-up excluded from latency threshold.
    decide("Hello", model)
    cases = []
    for expected, phrases in EXAMPLES.items():
        for phrase in phrases:
            start = time.perf_counter()
            answer = decide(phrase, model)
            cases.append(
                {
                    "expected": expected,
                    "observed": answer["choice"],
                    "seconds": time.perf_counter() - start,
                    "confidence": answer.get("confidence"),
                }
            )
    accuracy = sum(c["expected"] == c["observed"] for c in cases) / len(cases)
    p95 = float(np.percentile([c["seconds"] for c in cases], 95))
    result = {
        "model": model,
        "cases": 40,
        "accuracy": accuracy,
        "warm_p95_seconds": p95,
        "enabled": accuracy >= 0.95 and p95 < 2,
        "results": cases,
        "note": "Basic project routing benchmark; not an audio or general reasoning evaluation.",
    }
    (DATA / f"tev-benchmark-{model.replace(':', '-')}.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    current = status()
    if result["enabled"] or not current.get("enabled"):
        (DATA / "tev-benchmark.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def status() -> dict:
    path = DATA / "tev-benchmark.json"
    if not path.exists():
        return {"enabled": False, "reason": "Not benchmarked"}
    result = json.loads(path.read_text(encoding="utf-8"))
    result.pop("results", None)
    return result
