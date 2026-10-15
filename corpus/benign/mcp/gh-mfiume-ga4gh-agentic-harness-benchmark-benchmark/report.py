"""Summarize runs: code-graded answer accuracy, process checks, cost, by category.

    python -m benchmark.report runs/gpt-oss-low [runs/gpt-oss-high ...]

Answer accuracy counts only turns the code can grade (yes/no, number, string, set, and the TRS
validator), and leaves out turns where a service rate-limited the call, since that failure is
the service's, not the model's. Open and abstention turns are counted as awaiting a judge.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterator

from .answer import text as answer_text
from .checks import grade_turn
from .infra import row_hit
from .tasks import ROOT, load
from .validate import TrsValidator


def _rows(run: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (run / "results.jsonl").read_text().splitlines() if line.strip()]


def summarize(run: Path, validator: TrsValidator, tasks_by_id: dict[str, Any]) -> dict[str, Any]:
    rows = _rows(run)
    # Keep the last attempt of each task; a task that ran across a sleep is not scored.
    latest: dict[tuple[str, int], dict[str, Any]] = {}
    for row in rows:
        latest[(row["task_id"], row["repeat"])] = row
    slept = sum(1 for r in latest.values() if r.get("interrupted_by_sleep"))
    rows = [r for r in latest.values() if not r.get("interrupted_by_sleep") and not row_hit(r)]
    stale = [r for r in rows if r["status"] == "ok" and _stale(r, tasks_by_id)]
    rows = [r for r in rows if r not in stale]
    infra_rows = sum(1 for r in latest.values() if row_hit(r))
    manifest = json.loads((run / "manifest.json").read_text())
    per_cat: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    totals: dict[str, float] = defaultdict(float)
    for row in rows:
        cat = row["category"]
        totals["tasks"] += 1
        per_cat[cat]["tasks"] += 1
        if row["status"] != "ok" and "task exceeded" in str(row.get("error", "")):
            # Out of time is the model's result (too slow to answer within the budget), scored
            # as a failed task, not a framework error.
            for bucket in (totals, per_cat[cat]):
                bucket["timeouts"] += 1
                bucket["graded"] += 1
                bucket["strict_tasks"] += 1
            continue
        if row["status"] != "ok":
            totals["errors"] += 1
            per_cat[cat]["errors"] += 1
            continue
        totals["seconds"] += row["seconds"]
        task = tasks_by_id.get(row["task_id"])
        strict_ok, strict_counted = True, False
        for i, turn in enumerate(row["turns"]):
            totals["turns"] += 1
            totals["tool_calls"] += len(turn["tool_calls"])
            totals["prompt_tokens"] += turn["usage"].get("prompt_tokens", 0)
            totals["completion_tokens"] += turn["usage"].get("completion_tokens", 0)
            # Regrade from the stored submission, so grader and snapshot fixes apply to finished runs.
            if task and i < len(task["turns"]):
                calls = [{"tool": c["tool"], "arguments": c["arguments"]} for c in turn["tool_calls"]]
                turn["grade"] = grade_turn(task["turns"][i], turn["reply"], calls, turn.get("submitted"))
            answer = turn["grade"].get("answer")
            if answer and answer["verdict"] == "no_truth":
                totals["no_truth"] += 1
                continue
            if answer and answer["verdict"] == "needs_validation" and task:
                spec = task["turns"][i]["answer"]["validator"]
                answer = validator.check(spec, "\n".join([turn["reply"], answer_text(turn.get("submitted"))]))
            if turn.get("infra_affected"):
                totals["infra_turns"] += 1
                per_cat[cat]["infra_turns"] += 1
            elif answer and answer["verdict"] in ("pass", "fail"):
                passed = answer["verdict"] == "pass"
                for bucket in (totals, per_cat[cat]):
                    bucket["graded"] += 1
                    bucket["passed"] += passed
                strict_counted = True
                strict_ok &= passed
            elif answer:
                totals["judge_pending"] += 1
                per_cat[cat]["judge_pending"] += 1
            for check in turn["grade"].get("checks", []):
                for bucket in (totals, per_cat[cat]):
                    bucket["checks"] += 1
                    bucket["checks_passed"] += check["verdict"] == "pass"
        if strict_counted:
            for bucket in (totals, per_cat[cat]):
                bucket["strict_tasks"] += 1
                bucket["strict_passed"] += strict_ok
    totals["slept"] = slept
    totals["stale"] = len(stale)
    totals["infra_tasks"] = infra_rows
    return {"run": run.name, "model": manifest["model"], "totals": dict(totals),
            "categories": {k: dict(v) for k, v in sorted(per_cat.items())}}


def _stale(row: dict[str, Any], tasks_by_id: dict[str, Any]) -> bool:
    """A run of a task whose questions have since been revised."""
    task = tasks_by_id.get(row["task_id"])
    return bool(task) and any(i < len(task["turns"]) and t.get("prompt") != task["turns"][i]["prompt"]
                              for i, t in enumerate(row.get("turns") or []))


def latest_rows(run: Path) -> list[dict[str, Any]]:
    """The last attempt of each (task, repeat)."""
    latest: dict[tuple[str, int], dict[str, Any]] = {}
    for row in _rows(run):
        latest[(row["task_id"], row["repeat"])] = row
    return list(latest.values())


def graded_turns(run: Path, validator: TrsValidator, tasks_by_id: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Every turn of a run with one verdict, by the same rules as ``summarize``: pass, fail
    (a timeout is a failed task), judge, no_truth, infra (rate-limited or offline), slept, error."""
    for row in latest_rows(run):
        base = {"task_id": row["task_id"], "repeat": row["repeat"], "category": row["category"]}
        if row.get("interrupted_by_sleep") or row_hit(row):
            yield {**base, "turn_index": 0, "turn": None, "verdict": "slept" if row.get("interrupted_by_sleep") else "infra"}
            continue
        if row["status"] != "ok":
            timeout = "task exceeded" in str(row.get("error", ""))
            yield {**base, "turn_index": 0, "turn": None, "verdict": "fail" if timeout else "error", "timeout": timeout}
            continue
        task = tasks_by_id.get(row["task_id"])
        if task and any(i < len(task["turns"]) and t.get("prompt") != task["turns"][i]["prompt"]
                        for i, t in enumerate(row["turns"])):
            # The task was revised after this run: its answers are to a different question.
            yield {**base, "turn_index": 0, "turn": None, "verdict": "stale"}
            continue
        for i, turn in enumerate(row["turns"]):
            if task and i < len(task["turns"]):
                calls = [{"tool": c["tool"], "arguments": c["arguments"]} for c in turn["tool_calls"]]
                turn["grade"] = grade_turn(task["turns"][i], turn["reply"], calls, turn.get("submitted"))
            answer = turn["grade"].get("answer")
            if answer and answer["verdict"] == "needs_validation" and task:
                answer = validator.check(task["turns"][i]["answer"]["validator"],
                                         "\n".join([turn["reply"], answer_text(turn.get("submitted"))]))
            if not answer:
                verdict = "none"
            elif answer["verdict"] in ("pass", "fail", "no_truth"):
                verdict = answer["verdict"]
            else:
                verdict = "judge"
            yield {**base, "turn_index": i, "turn": turn, "verdict": verdict, "detail": (answer or {}).get("detail")}


def _macro(categories: dict[str, dict[str, float]]) -> str:
    rates = [c["passed"] / c["graded"] for c in categories.values() if c.get("graded")]
    return f"{100 * sum(rates) / len(rates):.1f}% over {len(rates)} categories" if rates else "-"


def _pct(a: float, b: float) -> str:
    return f"{100 * a / b:.1f}% ({int(a)}/{int(b)})" if b else "-"


def render(summaries: list[dict[str, Any]]) -> str:
    lines = []
    for s in summaries:
        t, m = s["totals"], s["model"]
        lines += [f"## {s['run']}: {m['model']} (effort {m.get('effort') or 'default'})", "",
                  f"- Tasks: {int(t.get('tasks', 0))}, framework errors: {int(t.get('errors', 0))}, "
                  f"out of time (scored as failed): {int(t.get('timeouts', 0))}, "
                  f"left out because the machine slept: {int(t.get('slept', 0))}, "
                  f"because a service or the network failed: {int(t.get('infra_tasks', 0))}, "
                  f"because the task was revised after the run: {int(t.get('stale', 0))}",
                  f"- Answer accuracy (code-graded turns): {_pct(t.get('passed', 0), t.get('graded', 0))}; "
                  f"category average {_macro(s['categories'])} (each category weighted equally, so the "
                  f"many single-fact lookups do not dominate)",
                  f"- Tasks with every graded turn right: {_pct(t.get('strict_passed', 0), t.get('strict_tasks', 0))}",
                  f"- Process checks passed: {_pct(t.get('checks_passed', 0), t.get('checks', 0))}",
                  f"- Awaiting judge: {int(t.get('judge_pending', 0))} turns; excluded as rate-limited: {int(t.get('infra_turns', 0))}; "
                  f"no ground truth yet: {int(t.get('no_truth', 0))}",
                  f"- Tool calls per turn: {t.get('tool_calls', 0) / max(t.get('turns', 1), 1):.1f}; "
                  f"seconds per task: {t.get('seconds', 0) / max(t.get('tasks', 1) - t.get('errors', 0), 1):.0f}; "
                  f"tokens: {int(t.get('prompt_tokens', 0)):,} in, {int(t.get('completion_tokens', 0)):,} out", "",
                  "| Category | Tasks | Answer accuracy | Checks passed | Awaiting judge |", "|---|---|---|---|---|"]
        for cat, c in s["categories"].items():
            lines.append(f"| {cat} | {int(c.get('tasks', 0))} | {_pct(c.get('passed', 0), c.get('graded', 0))} | "
                         f"{_pct(c.get('checks_passed', 0), c.get('checks', 0))} | {int(c.get('judge_pending', 0))} |")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", nargs="+", type=Path)
    args = parser.parse_args()
    tasks, _ = load()
    by_id = {t["id"]: t for t in tasks}
    validator = TrsValidator(ROOT / "cassettes" / "trs-validation.json")
    text = render([summarize(run, validator, by_id) for run in args.runs])
    print(text)
    for run in args.runs:
        (run / "report.md").write_text(text)


if __name__ == "__main__":
    main()
