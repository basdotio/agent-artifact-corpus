#!/usr/bin/env python3
"""
plan-parallel-waves.py  -  BMAD Parallel Plan

Consume the dependency DAG from build-dependency-graph.py and topologically sort it
into conflict-free, dependency-satisfied WAVES, each capped at --max-parallel.

Algorithm (level-by-level, deterministic):
  remaining = eligible nodes
  while remaining:
    ready  = nodes whose every directed prerequisite is already scheduled
    sort ready by ascending story id
    wave   = []
    for s in ready:
      stop at max_parallel
      skip s if it has an undirected conflict (file/semantic) with anyone in wave
    if wave empty while nodes remain -> dependency cycle (error)
    schedule wave, remove from remaining

Output waves.json:
  { max_parallel, waves: [ { wave, stories:[{id,slug,branch,scope}],
                             integration_branch, merge_order } ], deferred }

PLANS ONLY. Read-only. Does not create worktrees, branches, or run git.

Usage:
  plan-parallel-waves.py --graph dependency-graph.json [--max-parallel 3] \
      --out waves.json
"""

import argparse
import json
import sys
from pathlib import Path


def id_key(sid):
    """Sort key: numeric (epic, story) when possible, else string."""
    try:
        e, s = sid.split(".", 1)
        return (0, int(e), int(s))
    except Exception:
        return (1, 0, sid)


def slugify(sid, slug):
    return f"story/{sid}-{slug}" if slug else f"story/{sid}"


def plan(graph):
    max_parallel = int(graph.get("max_parallel", 3) or 3)
    nodes = {n["id"]: n for n in graph.get("nodes", [])}

    # directed prerequisites: edge from -> to means "to depends on from"
    prereqs = {nid: set() for nid in nodes}
    for e in graph.get("ordering_edges", []):
        frm, to = e.get("from"), e.get("to")
        if frm in nodes and to in nodes:
            prereqs[to].add(frm)

    # undirected conflict adjacency
    conflict = {nid: set() for nid in nodes}
    for c in graph.get("conflicts", []):
        a, b = c.get("a"), c.get("b")
        if a in nodes and b in nodes:
            conflict[a].add(b)
            conflict[b].add(a)

    remaining = set(nodes)
    scheduled = set()
    waves = []
    wave_index = 0

    while remaining:
        ready = sorted(
            [s for s in remaining if prereqs[s] <= scheduled],
            key=id_key,
        )
        wave = []
        for s in ready:
            if len(wave) >= max_parallel:
                break
            if any(t in conflict[s] for t in wave):
                continue
            wave.append(s)

        if not wave:
            cyc = ", ".join(sorted(remaining, key=id_key))
            raise SystemExit(f"error: dependency cycle or unsatisfiable deps among: {cyc}")

        wave_index += 1
        members = []
        for sid in wave:
            n = nodes[sid]
            members.append({
                "id": sid,
                "slug": n.get("slug", ""),
                "branch": slugify(sid, n.get("slug", "")),
                "scope": n.get("scope", []),
            })
        waves.append({
            "wave": wave_index,
            "stories": members,
            "integration_branch": f"integration/wave-{wave_index}",
            "merge_order": sorted(wave, key=id_key),
        })

        scheduled |= set(wave)
        remaining -= set(wave)

    deferred = list(graph.get("blocked", []))
    return {"max_parallel": max_parallel, "waves": waves, "deferred": deferred}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Topologically sort the DAG into capped waves.")
    ap.add_argument("--graph", default="dependency-graph.json")
    ap.add_argument("--max-parallel", type=int, default=None,
                    help="Override max_parallel from the graph file.")
    ap.add_argument("--out", default="waves.json")
    args = ap.parse_args(argv)

    gpath = Path(args.graph)
    if not gpath.is_file():
        print(f"error: graph file not found: {gpath}", file=sys.stderr)
        return 2

    graph = json.loads(gpath.read_text(encoding="utf-8"))
    if args.max_parallel is not None:
        graph["max_parallel"] = args.max_parallel

    result = plan(graph)
    text = json.dumps(result, indent=2)
    Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"\n[plan-parallel-waves] {len(result['waves'])} waves "
          f"(cap {result['max_parallel']}), "
          f"{len(result['deferred'])} deferred -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
