#!/usr/bin/env python3
"""Pick the cheapest Claude tier that can handle each delegated task, using Jev.

Usage:
    route.py "task one" "task two"        # JSON list, one object per task, in order
    route.py --file tasks.json            # JSON list of strings
    echo "task" | route.py -              # read one task from stdin
    route.py --dry-run "task"             # print the request, send nothing

Needs TYPESAFE_API_KEY (or JEV_API_KEY). Standard library only.

Design rules (see references/tuning.md for the reasoning):
  * Jev never sees model names, only descriptions of the work.
  * One request, four questions, evaluated in parallel.
  * Default tier is "balanced". Moving up needs little confidence, moving down
    needs a lot, because a wasted retry costs more than a slightly pricey run.
  * Any failure returns tier "inherit" (do not override the model). The router
    must never make a task worse than not having a router.
"""
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DEFAULT_URL = "https://api.typesafe.ai/v1/systemone"
MODEL = os.environ.get("JEV_MODEL", "jev-latest")
MAX_TASK_CHARS = 6000  # Jev only needs the gist; state is capped near 32k tokens

TIER_ORDER = ["fast", "balanced", "deep"]
TIER_MODELS = {
    "fast": os.environ.get("JEV_FAST_MODEL", "haiku"),
    "balanced": os.environ.get("JEV_BALANCED_MODEL", "sonnet"),
    "deep": os.environ.get("JEV_DEEP_MODEL", "opus"),
}
CHOICE_TO_TIER = {"mechanical": "fast", "ordinary": "balanced", "hard": "deep"}

QUESTIONS = {
    "tier": {
        "type": "choice",
        "instructions": "How demanding is the work described in `task`?",
        "criteria": {
            "mechanical": (
                "Well-specified and local: rename, reformat, move code, fix a typo, "
                "write a docstring, run a command and report output, small edit to "
                "one known file, simple lookup or summary"
            ),
            "ordinary": (
                "Normal engineering: implement a clear feature, write tests, fix a "
                "bug whose cause is roughly known, refactor within one module, "
                "review a small diff"
            ),
            "hard": (
                "Open-ended or high-stakes: unknown root cause, architecture or "
                "design decisions, cross-cutting refactor, security-sensitive work, "
                "concurrency or data-integrity problems, ambiguous requirements"
            ),
        },
    },
    "effort": {
        "type": "score",
        "instructions": "How much careful reasoning does a good result for `task` need?",
        "criteria": [
            "None: the steps are obvious and can be done directly",
            "A little: a few steps, one thing to keep in mind",
            "A fair amount: several interacting parts or trade-offs to weigh",
            "A lot: subtle, easy to get wrong, needs to explore and verify",
        ],
    },
    "risky": {
        "type": "noul",
        "instructions": (
            "Would carrying out `task` itself change production systems, move real "
            "money, or alter data that cannot be restored? Writing or testing code "
            "that deals with those things does not count."
        ),
    },
    "wide": {
        "type": "noul",
        "instructions": (
            "Does `task` need understanding of many files or a whole codebase at "
            "once, rather than one small, known area?"
        ),
    },
}


def build_request(task: str) -> dict:
    return {
        "model": MODEL,
        "state": {"task": task[:MAX_TASK_CHARS]},
        "questions": QUESTIONS,
    }


def call_jev(task: str, key: str, url: str, timeout: float) -> dict:
    body = json.dumps(build_request(task)).encode()
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    deadline = time.monotonic() + timeout
    for attempt in (0, 1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("latency budget exhausted")
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=remaining) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            # Retry once on rate limit / overload, if there is budget left.
            if e.code in (429, 529) and attempt == 0 and deadline - time.monotonic() > 0.4:
                time.sleep(0.25)
                continue
            raise
    raise RuntimeError("unreachable")


def effort_hint(score: float, cap: str) -> str:
    levels = ["low", "medium", "high", "xhigh"]
    if score < 0.75:
        idx = 0
    elif score < 1.5:
        idx = 1
    elif score < 2.25:
        idx = 2
    else:
        idx = 3
    return levels[min(idx, levels.index(cap))]


def decide(answers: dict, min_up: float, min_down: float, max_effort: str) -> dict:
    """Turn Jev's answers into a tier. Pure function so it can be tested."""
    tier_ans = answers["tier"]
    choice = tier_ans["choice"]
    conf = float(tier_ans.get("confidence", 0.0))
    effort = float(answers["effort"]["score"])
    risky = float(answers["risky"]["noul"])
    wide = float(answers["wide"]["noul"])

    wanted = CHOICE_TO_TIER.get(choice, "balanced")
    tier, reason = "balanced", f"default (jev said {choice} at {conf:.2f})"

    if risky >= 0.7:
        tier, reason = "deep", f"risky {risky:.2f}"
    elif wanted == "deep":
        if conf >= min_up:
            tier, reason = "deep", f"hard at {conf:.2f}"
        else:
            reason = f"hard but only {conf:.2f} confident, staying balanced"
    elif wanted == "fast":
        # Only downgrade when several independent signals agree.
        if conf < min_down:
            reason = f"mechanical but only {conf:.2f} confident, staying balanced"
        elif effort >= 1.5:
            reason = f"mechanical but effort {effort:.1f}, staying balanced"
        elif wide >= 0.6:
            reason = f"mechanical but wide {wide:.2f}, staying balanced"
        else:
            tier, reason = "fast", f"mechanical at {conf:.2f}, effort {effort:.1f}"
    else:
        tier, reason = "balanced", f"ordinary at {conf:.2f}"

    return {
        "tier": tier,
        "model": TIER_MODELS[tier],
        "effort_hint": effort_hint(effort, max_effort),
        "confidence": round(conf, 3),
        "risky": round(risky, 3),
        "wide": round(wide, 3),
        "effort_score": round(effort, 2),
        "reason": reason,
    }


def inherit(reason: str) -> dict:
    return {
        "tier": "inherit",
        "model": None,
        "effort_hint": None,
        "confidence": None,
        "reason": reason,
    }


def log_decision(task: str, result: dict, latency_ms: int) -> None:
    if os.environ.get("JEV_DELEGATE_LOG", "1") == "0":
        return
    try:
        path = Path.home() / ".jev-delegate" / "decisions.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        # Never log task text: keep an id, a length and the decision only.
        rec = {
            "ts": int(time.time()),
            "task_id": hashlib.sha1(task.encode()).hexdigest()[:8],
            "task_chars": len(task),
            "latency_ms": latency_ms,
            **{k: result.get(k) for k in ("tier", "confidence", "risky", "wide", "effort_score", "reason")},
        }
        with path.open("a") as f:
            f.write(json.dumps(rec) + "\n")
    except OSError:
        pass  # logging must never break routing


def route_one(task: str, args) -> dict:
    key = os.environ.get("TYPESAFE_API_KEY") or os.environ.get("JEV_API_KEY")
    preview = " ".join(task.split())[:80]
    if not key:
        out = inherit("no TYPESAFE_API_KEY set; not overriding the model")
        out["task"] = preview
        return out
    t0 = time.monotonic()
    try:
        resp = call_jev(task, key, args.url, args.timeout)
        out = decide(resp["answers"], args.min_upgrade, args.min_downgrade, args.max_effort)
        out["jev_model"] = resp.get("model")
    except Exception as e:  # fail open, always
        out = inherit(f"jev unavailable ({type(e).__name__}: {e})")
    latency = int((time.monotonic() - t0) * 1000)
    out["latency_ms"] = latency
    out["task"] = preview
    log_decision(task, out, latency)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("tasks", nargs="*", help='task descriptions, or "-" to read one from stdin')
    p.add_argument("--file", help="JSON file containing a list of task strings")
    p.add_argument("--url", default=os.environ.get("JEV_URL", DEFAULT_URL))
    p.add_argument("--timeout", type=float, default=2.5, help="seconds per task (default 2.5)")
    p.add_argument("--min-upgrade", type=float, default=0.3, help="confidence needed to go up a tier")
    p.add_argument("--min-downgrade", type=float, default=0.6, help="confidence needed to go down a tier")
    p.add_argument("--max-effort", choices=["low", "medium", "high", "xhigh"], default="high")
    p.add_argument("--dry-run", action="store_true", help="print the request and exit")
    args = p.parse_args()

    tasks = list(args.tasks)
    if tasks == ["-"]:
        tasks = [sys.stdin.read()]
    if args.file:
        tasks += json.loads(Path(args.file).read_text())
    tasks = [t for t in tasks if t and t.strip()]
    if not tasks:
        p.error("no tasks given")

    if args.dry_run:
        print(json.dumps(build_request(tasks[0]), indent=2))
        return 0

    with ThreadPoolExecutor(max_workers=min(8, len(tasks))) as pool:
        results = list(pool.map(lambda t: route_one(t, args), tasks))
    print(json.dumps(results, indent=2))  # always a list, same order as the tasks
    return 0


if __name__ == "__main__":
    sys.exit(main())
