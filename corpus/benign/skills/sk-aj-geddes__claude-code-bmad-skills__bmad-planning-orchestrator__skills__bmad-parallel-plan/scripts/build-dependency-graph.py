#!/usr/bin/env python3
"""
build-dependency-graph.py  -  BMAD Parallel Plan

Read sprint-status.yaml (for story status) and a directory of ready-for-dev story
files ({epic}.{story}.{slug}.story.md), then emit a dependency DAG as JSON:

  - nodes          : one per wave-eligible story  {id, slug, epic, status, scope}
  - ordering_edges : directed constraints  {from, to, reason}
        * intra-epic sequence  (stories within an epic are usually sequential)
        * explicit depends_on  (from each story's Dependency Maps section)
  - conflicts      : undirected mutual-exclusion pairs  {a, b, class, detail}
        * class "file"     : Owned File/Module Scopes intersect
        * class "semantic" : both touch a shared/cross-cutting module (see --shared)
  - blocked        : ready stories excluded for missing scope  {id, reason}

PLANS ONLY. Read-only. Does not run git, agents, or tests.

Usage:
  build-dependency-graph.py --status sprint-status.yaml --stories ./stories \
      --out dependency-graph.json [--max-parallel 3] [--shared src/auth src/db]

YAML is parsed with PyYAML when present; otherwise a tolerant line scanner pulls
just the fields we need (id/status). The story markdown is the source of truth for
scope and dependencies, so the planner never depends on rich YAML.
"""

import argparse
import json
import re
import sys
from pathlib import Path

STORY_RE = re.compile(r"^(\d+)\.(\d+)\.(.+)\.story\.md$")


# --------------------------------------------------------------------------- #
# sprint-status.yaml  ->  {story_id: status}
# --------------------------------------------------------------------------- #
def load_status_map(status_path):
    """Return {id: status}. Tolerant: works with or without PyYAML."""
    p = Path(status_path)
    text = p.read_text(encoding="utf-8") if p.is_file() else ""
    if not text.strip():
        return {}
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(text) or {}
        return _status_from_yaml(data)
    except Exception:
        return _status_from_lines(text)


def _status_from_yaml(data):
    out = {}

    def walk(node):
        if isinstance(node, dict):
            sid, st = node.get("id"), node.get("status")
            if sid is not None and st is not None:
                out[str(sid)] = str(st).strip()
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data)
    return out


def _status_from_lines(text):
    """Fallback: pair the nearest preceding `id:` with a following `status:`."""
    out, cur = {}, None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0]
        m = re.search(r'(?:^|[\s-])id:\s*["\']?([\w.\-]+)["\']?', line)
        if m:
            cur = m.group(1)
            continue
        m = re.search(r'status:\s*["\']?([\w\-]+)["\']?', line)
        if m and cur is not None:
            out[cur] = m.group(1)
            cur = None
    return out


# --------------------------------------------------------------------------- #
# story markdown -> scope[] and depends_on[]
# --------------------------------------------------------------------------- #
SECTION_RE = re.compile(r"^#{1,6}\s+(.*\S)\s*$")
BULLET_RE = re.compile(r"^\s*[-*]\s+(.*\S)\s*$")
DEP_ID_RE = re.compile(r"(\d+\.\d+)")


def _section_body(lines, start_idx):
    """Yield bullet contents under the heading at start_idx until the next heading."""
    for line in lines[start_idx + 1:]:
        if SECTION_RE.match(line):
            break
        m = BULLET_RE.match(line)
        if m:
            yield m.group(1).strip()


def parse_story(path):
    """Return (scope_paths, depends_on_ids) for one story file."""
    lines = path.read_text(encoding="utf-8").splitlines()
    scope, deps = [], []

    for i, line in enumerate(lines):
        h = SECTION_RE.match(line)
        if not h:
            continue
        title = h.group(1).lower()

        if "owned file" in title or "module scope" in title:
            for item in _section_body(lines, i):
                token = item.strip().strip("`").split("#", 1)[0].strip()
                parts = token.split()
                token = parts[0].strip("`") if parts else ""
                if token and not token.lower().startswith("none"):
                    scope.append(token)

        elif "dependency map" in title or title == "dependencies":
            for item in _section_body(lines, i):
                low = item.lower()
                if "depends_on" in low or "depends on" in low or low.startswith("blocked by"):
                    deps += DEP_ID_RE.findall(item)

    scope = list(dict.fromkeys(scope))
    deps = list(dict.fromkeys(deps))
    return scope, deps


# --------------------------------------------------------------------------- #
# graph assembly
# --------------------------------------------------------------------------- #
ELIGIBLE = {"ready-for-dev", "in-progress", "review"}


def normalize(p):
    return p.rstrip("/").lstrip("./")


def scopes_intersect(a, b):
    """Return (x, y) of the first overlapping pair, else None (prefix-aware for dirs)."""
    na = [normalize(x) for x in a]
    nb = [normalize(x) for x in b]
    for x in na:
        for y in nb:
            if x == y or x.startswith(y + "/") or y.startswith(x + "/"):
                return (x, y)
    return None


def shared_touch(scope, shared):
    out = []
    for s in scope:
        ns = normalize(s)
        for sh in shared:
            nsh = normalize(sh)
            if ns == nsh or ns.startswith(nsh + "/") or nsh.startswith(ns + "/"):
                out.append(nsh)
    return out


def build(stories_dir, status_map, shared):
    nodes, blocked = [], []
    scope_by_id, deps_by_id, epic_members = {}, {}, {}

    for f in sorted(Path(stories_dir).glob("*.story.md")):
        m = STORY_RE.match(f.name)
        if not m:
            continue
        epic, story, slug = int(m.group(1)), int(m.group(2)), m.group(3)
        sid = f"{epic}.{story}"
        status = status_map.get(sid, "ready-for-dev")
        if status not in ELIGIBLE:
            continue

        scope, deps = parse_story(f)
        if not scope:
            blocked.append({"id": sid, "reason": "no Owned File/Module Scope declared"})
            continue

        nodes.append({"id": sid, "slug": slug, "epic": epic,
                      "status": status, "scope": scope})
        scope_by_id[sid] = scope
        deps_by_id[sid] = deps
        epic_members.setdefault(epic, []).append((story, sid))

    valid = set(scope_by_id)

    # ordering edges: intra-epic sequence + explicit depends_on
    ordering, seen = [], set()

    def add_edge(frm, to, reason):
        k = (frm, to)
        if k not in seen:
            seen.add(k)
            ordering.append({"from": frm, "to": to, "reason": reason})

    for members in epic_members.values():
        members.sort()
        for (_, id_prev), (_, id_next) in zip(members, members[1:]):
            add_edge(id_prev, id_next, "intra-epic-sequence")
    for sid, deps in deps_by_id.items():
        for d in deps:
            if d in valid and d != sid:
                add_edge(d, sid, "depends_on")

    # undirected conflicts: file overlap, else shared-module semantic
    conflicts = []
    ids = [n["id"] for n in nodes]
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            hit = scopes_intersect(scope_by_id[a], scope_by_id[b])
            if hit:
                conflicts.append({"a": a, "b": b, "class": "file",
                                  "detail": f"{hit[0]} / {hit[1]}"})
            elif shared:
                common = set(shared_touch(scope_by_id[a], shared)) & \
                         set(shared_touch(scope_by_id[b], shared))
                if common:
                    conflicts.append({"a": a, "b": b, "class": "semantic",
                                      "detail": "shared:" + ",".join(sorted(common))})

    return nodes, ordering, conflicts, blocked


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the BMAD story dependency DAG (JSON).")
    ap.add_argument("--status", default="sprint-status.yaml")
    ap.add_argument("--stories", default="stories")
    ap.add_argument("--out", default="dependency-graph.json")
    ap.add_argument("--max-parallel", type=int, default=3)
    ap.add_argument("--shared", nargs="*", default=[],
                    help="Shared/cross-cutting module paths from architecture.md")
    args = ap.parse_args(argv)

    sdir = Path(args.stories)
    if not sdir.is_dir():
        print(f"error: stories directory not found: {sdir}", file=sys.stderr)
        return 2

    status_map = load_status_map(args.status)
    nodes, ordering, conflicts, blocked = build(sdir, status_map, args.shared)

    graph = {
        "max_parallel": args.max_parallel,
        "nodes": nodes,
        "ordering_edges": ordering,
        "conflicts": conflicts,
        "blocked": blocked,
    }
    text = json.dumps(graph, indent=2)
    Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"\n[build-dependency-graph] {len(nodes)} eligible, "
          f"{len(ordering)} ordering edges, {len(conflicts)} conflicts, "
          f"{len(blocked)} blocked -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
