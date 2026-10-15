#!/usr/bin/env python3
"""Summarize ~/.jev-delegate/decisions.jsonl.

Shows how tasks were spread across tiers, how often Jev was unavailable, and a
rough relative-cost estimate against sending everything to the deep tier.

The cost weights are ASSUMPTIONS (relative price per token vs the deep tier).
Override them to match your plan. Subscription plans meter usage differently
from per-token pricing, so treat the estimate as directional, not a bill.
"""
import argparse
import json
from collections import Counter
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--log", default=str(Path.home() / ".jev-delegate" / "decisions.jsonl"))
    p.add_argument("--fast-weight", type=float, default=0.25, help="assumed cost of fast tier vs deep")
    p.add_argument("--balanced-weight", type=float, default=0.5, help="assumed cost of balanced tier vs deep")
    p.add_argument("--deep-weight", type=float, default=1.0)
    args = p.parse_args()

    path = Path(args.log)
    if not path.exists():
        print(f"No log at {path}. Route some tasks first.")
        return
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not rows:
        print("Log is empty.")
        return

    weights = {"fast": args.fast_weight, "balanced": args.balanced_weight, "deep": args.deep_weight, "inherit": args.deep_weight}
    counts = Counter(r["tier"] for r in rows)
    n = len(rows)
    print(f"{n} routed tasks")
    for tier in ("fast", "balanced", "deep", "inherit"):
        if counts[tier]:
            print(f"  {tier:9s} {counts[tier]:4d}  ({counts[tier] / n:.0%})")

    lat = sorted(r["latency_ms"] for r in rows if r.get("latency_ms") is not None)
    if lat:
        print(f"jev latency: median {lat[len(lat) // 2]} ms, max {lat[-1]} ms")

    cost = sum(weights[r["tier"]] for r in rows)
    baseline = n * args.deep_weight
    print(f"\nEstimated relative cost vs all-deep: {cost / baseline:.0%} "
          f"(weights fast={args.fast_weight}, balanced={args.balanced_weight}, deep={args.deep_weight}; assumed)")
    print("This assumes tasks are the same size across tiers and no retries. "
          "Measure real token usage before quoting a savings figure.")


if __name__ == "__main__":
    main()
