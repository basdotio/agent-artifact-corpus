"""The experiment graph: each node a configuration, each edge one change, each decision recorded.

    python -m benchmark.experiments show
    python -m benchmark.experiments add NODE --parent P --change "..." [--mcp-repo R --mcp-ref REF] [--sdk-repo R --sdk-ref REF]
                                        [--tool-filter G] [--targets C,...]
    python -m benchmark.experiments run NODE [inner|outer|all]        # bin/run-node with the node's sources
    python -m benchmark.experiments compare NODE [--config dev-low]   # paired against its parent
    python -m benchmark.experiments decide NODE                       # applies the acceptance rule, records it

A node is {model configuration, MCP commit, SDK commit, tool filter}; it runs from detached
worktrees of exactly those commits (~/Development/bench-wt/nodes/NODE). Runs live under
runs/exp/NODE/CONFIG (dev-low, heldout-low, heldout-high). The graph and every comparison are
committed in experiments/; runs are not.

Acceptance rule (version 2, fixed 2026-10-04 before any change was measured under it):
  Each change is a sibling of root, measured on the dev tasks it can affect (its target set),
  at low effort, over several seeds (5 for a set of 40 tasks or fewer, else 3), against root on
  the same tasks and seeds. Per task, d = child's pass rate - root's (over seeds and graded turns).
  Accept if sum(d) >= +2 and a one-sided sign test over tasks with d != 0 gives p < 0.10.
Why not version 1 (one seed, net >= +2 on all dev, no category <= -2): a tool description is in
every prompt, so any change resamples every task. C1 changed only the Beacon tool and flipped
28 of 197 turns, 14 each way, mostly in categories it cannot affect.
The held-out split is not consulted by this rule; it is reported once for the accepted set.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from .report import graded_turns
from .tasks import ROOT, load
from .validate import TrsValidator

GRAPH = ROOT / "experiments" / "graph.json"
RUNS = ROOT / "runs" / "exp"
WORKTREES = Path.home() / "Development" / "bench-wt" / "nodes"
MIN_SUM_D, SIGN_P = 2.0, 0.10


def load_graph() -> dict[str, Any]:
    return json.loads(GRAPH.read_text()) if GRAPH.is_file() else {"nodes": {}}


def save_graph(graph: dict[str, Any]) -> None:
    GRAPH.parent.mkdir(exist_ok=True)
    GRAPH.write_text(json.dumps(graph, indent=1) + "\n")


def _rev(repo: str, ref: str) -> str:
    return subprocess.run(["git", "-C", repo, "rev-parse", "--short", ref + "^{commit}"], capture_output=True,
                          text=True, check=True).stdout.strip()


TARGET_SETS = ROOT / "experiments" / "target-sets.json"
SMALL = 40


def task_set(key: str) -> list[str]:
    sets = json.loads(TARGET_SETS.read_text())
    if key == "small":
        return sorted(set().union(*(set(v) for v in sets.values() if len(v) <= SMALL)))
    return sets[key]


def seeds_for(tasks: list[str] | None) -> list[int]:
    return [0, 1, 2, 3, 4] if tasks and len(tasks) <= SMALL else [0, 1, 2]


def add(node: str, parent: str | None, change: str, *, mcp_repo: str | None = None, mcp_ref: str | None = None,
        sdk_repo: str | None = None, sdk_ref: str | None = None, tool_filter: str | None = None,
        targets: list[str] | None = None, detail: str = "", tasks: list[str] | None = None) -> dict[str, Any]:
    """A node pins the MCP and SDK by commit; unset ones are inherited from the parent."""
    graph = load_graph()
    if node in graph["nodes"]:
        raise SystemExit(f"node {node} exists")
    inherited = graph["nodes"][parent] if parent else {}
    mcp_repo = mcp_repo or inherited.get("mcp_repo")
    sdk_repo = sdk_repo or inherited.get("sdk_repo")
    entry = {
        "parent": parent, "change": change, "detail": detail, "targets": targets or [],
        "mcp_repo": mcp_repo, "mcp_commit": _rev(mcp_repo, mcp_ref) if mcp_ref else inherited.get("mcp_commit"),
        "sdk_repo": sdk_repo, "sdk_commit": _rev(sdk_repo, sdk_ref) if sdk_ref else inherited.get("sdk_commit"),
        "tool_filter": tool_filter if tool_filter is not None else inherited.get("tool_filter"),
        "tasks": tasks, "seeds": seeds_for(tasks),
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "status": "planned",
    }
    graph["nodes"][node] = entry
    save_graph(graph)
    return entry


def checkout(name: str, node: dict[str, Any]) -> dict[str, str]:
    """Detached worktrees of the node's MCP and SDK commits, so each node runs exactly its code."""
    paths = {}
    for part in ("mcp", "sdk"):
        path = WORKTREES / name / part
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "-C", node[f"{part}_repo"], "worktree", "add", "--detach", str(path),
                            node[f"{part}_commit"]], check=True, capture_output=True)
        head = _rev(str(path), "HEAD")
        if head != node[f"{part}_commit"]:
            raise SystemExit(f"{path} is at {head}, not {node[f'{part}_commit']}")
        paths[part] = str(path)
    return paths


def runner_args(name: str, node: dict[str, Any]) -> list[str]:
    paths = checkout(name, node)
    args = ["--mcp-src", paths["mcp"], "--sdk-src", paths["sdk"]]
    if node.get("tool_filter"):
        args += ["--tool-filter", node["tool_filter"]]
    return args


def run(name: str, scope: str, seeds: list[int] | None = None, tasks: list[str] | None = None,
        model: str | None = None, effort: str | None = None, label: str | None = None, split: str = "all") -> int:
    """scope "low": dev split at low effort, the node's seeds and target tasks (or those given);
    "outer": the held-out configurations (bin/run-node)."""
    graph = load_graph()
    node = graph["nodes"][name]
    args = runner_args(name, node)
    node["status"] = "running"
    save_graph(graph)
    if scope == "outer":
        code = subprocess.call([str(ROOT / "bin" / "run-node"), name, "outer", *args])
    elif scope == "model":
        # Another model on this node's build: every task (dev and held-out), seed 0, the model's
        # own default temperature and thinking.
        out = RUNS / name / (f"all-{label}" if split == "all" else f"{split}-{label}")
        env = {**os.environ, "BENCH_MODEL": model}
        code = subprocess.call([str(ROOT / "bin" / "run-config"), str(out), effort or "default", split, "1",
                                "--temperature", "-1", *args], env=env)
    else:
        seeds = seeds or node["seeds"]
        out = RUNS / name / "low"
        out.mkdir(parents=True, exist_ok=True)
        tasks = tasks if tasks is not None else node.get("tasks")
        if tasks:
            (out / f"tasks-{seeds[0]}.txt").write_text("\n".join(tasks) + "\n")
            args += ["--task-file", str(out / f"tasks-{seeds[0]}.txt")]
        if seeds != list(range(seeds[0], seeds[0] + len(seeds))):
            raise SystemExit("seeds must be contiguous")
        code = subprocess.call([str(ROOT / "bin" / "run-config"), str(out), "low", "dev", str(len(seeds)),
                                "--seed", str(seeds[0]), *args])
    graph = load_graph()
    graph["nodes"][name]["status"] = "measured" if code == 0 else "run failed"
    save_graph(graph)
    return code


def mcnemar(b: int, c: int) -> float:
    """Exact two-sided McNemar p on discordant counts b and c."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def verdicts(run_dir: Path) -> dict[tuple[str, int, int], tuple[str, str]]:
    tasks, _ = load()
    by_id = {t["id"]: t for t in tasks}
    validator = TrsValidator(ROOT / "cassettes" / "trs-validation.json")
    return {(v["task_id"], v["repeat"], v["turn_index"]): (v["verdict"], v["category"])
            for v in graded_turns(run_dir, validator, by_id)}


def sign_test(up: int, down: int) -> float:
    """One-sided: probability of at least ``up`` improvements among up + down if each way is even."""
    n = up + down
    return sum(math.comb(n, i) for i in range(up, n + 1)) / 2 ** n if n else 1.0


def compare(child: str, base: str = "root", config: str = "low") -> dict[str, Any]:
    """Paired by task and seed. config "low" is the dev measurement on the child's target tasks and
    seeds; "heldout-low" and "heldout-high" compare every held-out task on the seeds both ran."""
    graph = load_graph()
    node = graph["nodes"][child]
    a, b = verdicts(RUNS / base / config), verdicts(RUNS / child / config)
    if config == "low":
        wanted, seeds = set(node.get("tasks") or {k[0] for k in b}), set(node["seeds"])
    else:
        wanted, seeds = {k[0] for k in b}, {k[1] for k in a} & {k[1] for k in b}
    per_task: dict[str, list[tuple[bool, bool]]] = defaultdict(list)
    categories: dict[str, str] = {}
    for key in set(a) & set(b):
        task, seed, _ = key
        (va, cat), (vb, _) = a[key], b[key]
        if task in wanted and seed in seeds and va in ("pass", "fail") and vb in ("pass", "fail"):
            per_task[task].append((va == "pass", vb == "pass"))
            categories[task] = cat
    diffs = {t: sum(cb for _, cb in pairs) / len(pairs) - sum(ca for ca, _ in pairs) / len(pairs)
             for t, pairs in per_task.items()}
    up = sorted(t for t, d in diffs.items() if d > 0)
    down = sorted(t for t, d in diffs.items() if d < 0)
    pairs = [p for ps in per_task.values() for p in ps]
    by_cat: dict[str, float] = defaultdict(float)
    for t, d in diffs.items():
        by_cat[categories[t]] += d
    return {"child": child, "base": base, "seeds": sorted(seeds), "tasks": len(per_task), "paired_turns": len(pairs),
            "base_passes": sum(x for x, _ in pairs), "child_passes": sum(y for _, y in pairs),
            "base_accuracy": sum(x for x, _ in pairs) / len(pairs) if pairs else None,
            "child_accuracy": sum(y for _, y in pairs) / len(pairs) if pairs else None,
            "sum_d": round(sum(diffs.values()), 2), "tasks_up": len(up), "tasks_down": len(down),
            "sign_p": sign_test(len(up), len(down)),
            "categories": {c: round(v, 2) for c, v in sorted(by_cat.items())}, "up": up, "down": down}


def decide(name: str) -> dict[str, Any]:
    result = compare(name)
    accepted = result["sum_d"] >= MIN_SUM_D and result["sign_p"] < SIGN_P
    reason = (f"sum(d) {result['sum_d']:+.2f} over {result['tasks']} tasks x seeds {result['seeds']} "
              f"(needs >= +{MIN_SUM_D}); tasks up {result['tasks_up']}, down {result['tasks_down']}, "
              f"sign test p {result['sign_p']:.3g} (needs < {SIGN_P}); accuracy "
              f"{result['base_accuracy']:.3f} -> {result['child_accuracy']:.3f}")
    graph = load_graph()
    graph["nodes"][name].update(status="accepted" if accepted else "rejected", decision=reason, compare=result,
                                decided=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    save_graph(graph)
    return graph["nodes"][name]


def show() -> str:
    graph = load_graph()
    lines = []

    def walk(parent: str | None, depth: int) -> None:
        for name, node in graph["nodes"].items():
            if node["parent"] == parent:
                c = node.get("compare") or {}
                score = (f" {c['base_accuracy']:.3f} -> {c['child_accuracy']:.3f} sum(d) {c['sum_d']:+.2f}"
                         if c.get("paired_turns") else "")
                lines.append(f"{'  ' * depth}{name} [{node['status']}]{score}  {node['change']}")
                walk(name, depth + 1)
    walk(None, 0)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add")
    p.add_argument("node")
    p.add_argument("--parent")
    p.add_argument("--change", required=True)
    p.add_argument("--detail", default="")
    p.add_argument("--mcp-repo")
    p.add_argument("--mcp-ref")
    p.add_argument("--sdk-repo")
    p.add_argument("--sdk-ref")
    p.add_argument("--tool-filter")
    p.add_argument("--targets", default="")
    p.add_argument("--task-set", help="a key of experiments/target-sets.json; omitted means every dev task")
    p = sub.add_parser("run")
    p.add_argument("node")
    p.add_argument("scope", nargs="?", default="low", choices=["low", "outer", "model"])
    p.add_argument("--model", help="scope model: e.g. ollama:qwen3:14b")
    p.add_argument("--effort", help="scope model: thinking level, if the model takes one")
    p.add_argument("--label", help="scope model: names the run directory, SPLIT-LABEL")
    p.add_argument("--split", default="all", choices=["all", "dev", "heldout"], help="scope model: which tasks")
    p.add_argument("--seeds", help="contiguous, e.g. 1,2 (default: the node's)")
    p.add_argument("--task-set", help="a key of experiments/target-sets.json, or 'small' for the union of small sets")
    p = sub.add_parser("compare")
    p.add_argument("node")
    p.add_argument("--against", default="root")
    p.add_argument("--config", default="low", help="run directory under each node: low, heldout-low, heldout-high, or another")
    p = sub.add_parser("decide")
    p.add_argument("node")
    sub.add_parser("show")
    args = parser.parse_args()
    if args.cmd == "add":
        print(json.dumps(add(args.node, args.parent, args.change, mcp_repo=args.mcp_repo, mcp_ref=args.mcp_ref,
                             sdk_repo=args.sdk_repo, sdk_ref=args.sdk_ref,
                             tool_filter=args.tool_filter, targets=[t for t in args.targets.split(",") if t],
                             detail=args.detail, tasks=task_set(args.task_set) if args.task_set else None),
                         indent=1))
    elif args.cmd == "run":
        seeds = [int(x) for x in args.seeds.split(",")] if args.seeds else None
        return run(args.node, args.scope, seeds, task_set(args.task_set) if args.task_set else None,
                   model=args.model, effort=args.effort, label=args.label, split=args.split)
    elif args.cmd == "compare":
        result = compare(args.node, args.against, args.config)
        print(json.dumps(result, indent=1))
    elif args.cmd == "decide":
        node = decide(args.node)
        print(f"{args.node}: {node['status']}: {node['decision']}")
    else:
        print(show())
    return 0


if __name__ == "__main__":
    sys.exit(main())
