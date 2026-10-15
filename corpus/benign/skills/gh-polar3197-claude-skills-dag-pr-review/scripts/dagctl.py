#!/usr/bin/env python3
"""dagctl - deterministic scheduler for a DAG-based pull request review.

The orchestrating agent never decides by itself what is ready to run. This
script owns the review graph, its state file, the prompts handed to each
subagent, result-contract validation, runtime node expansion, finding
deduplication, verification fan-out and the final report.

Standard library only. Python 3.9+.

Lifecycle (every command takes the global --dir option, default .dag-review):

    init      diff the branch, classify files, pick a risk tier  -> context.json
    autoplan  deterministic draft graph                           -> plan.json
    load      validate plan.json and create the run state         -> state.json
    next      claim ready nodes (critical path first), render their prompts
    complete  validate a node's result file; retry, expand or finish the node
    collect   dedupe findings, create one verifier per finding    -> findings.json
    report    assemble the final review                           -> review.md / review.json

Helpers: status, show, fail, reclaim.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

VERSION = 1
SKILL_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = SKILL_DIR / "references" / "prompts"

REVIEW_KINDS = ("intent", "cluster", "leaf", "crosscut")
LENSES = ("security", "tests", "performance", "guidelines", "api-compat", "concurrency", "data-migration", "general")
TERMINAL = {"done", "failed", "expanded"}
SEVERITIES = ("critical", "major", "minor", "nit")
SEV_RANK = {s: i for i, s in enumerate(SEVERITIES)}  # lower is worse
RESULT_STATUSES = {"DONE", "DONE_WITH_CONCERNS", "NEEDS_EXPANSION", "BLOCKED"}
VERDICTS = {"confirmed", "refuted", "unverifiable"}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")

TIERS = {
    # Cost scales with risk (see references/design-notes.md, "risk tiers").
    "trivial": {"max_nodes": 6, "max_parallel": 4, "max_verify": 6},
    "lite": {"max_nodes": 16, "max_parallel": 8, "max_verify": 12},
    "full": {"max_nodes": 40, "max_parallel": 8, "max_verify": 25},
}
DEFAULT_CAPS = {
    "max_depth": 5,              # longest dependency chain in the graph
    "max_expansion_depth": 2,    # how many times a subtree may be split at runtime
    "max_attempts": 2,           # per node, before it is marked failed
    "leaf_line_budget": 400,     # changed lines one leaf should own
    "max_findings_per_node": 15,
    "min_confidence": 0.2,       # reviewer-reported confidence below this is discarded pre-verify
    "summary_chars": 1800,
}
TRIVIAL_LINES, LITE_LINES = 20, 300

SENSITIVE_RE = re.compile(
    r"(auth|security|crypto|passw|secret|credential|token|session|permission|acl|oauth|jwt|saml|"
    r"payment|billing|migrat|\.sql$|(^|/)iam|policy|sanitiz|escape|\.github/workflows/|dockerfile|"
    r"terraform|\.tf$|(^|/)k8s/|helm|nginx|cors|csrf)", re.I)
TEST_RE = re.compile(
    r"(^|/)(tests?|__tests__|specs?|e2e)/|(_test|\.test|\.spec|_spec)\.[A-Za-z0-9]+$|(^|/)test_[^/]+\.py$|(^|/)conftest\.py$",
    re.I)
DOCS_RE = re.compile(r"\.(md|mdx|rst|txt|adoc)$|(^|/)docs?/", re.I)
GENERATED_RE = re.compile(
    r"(^|/)(package-lock\.json|npm-shrinkwrap\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|Pipfile\.lock|uv\.lock|"
    r"Cargo\.lock|go\.sum|Gemfile\.lock|composer\.lock|bun\.lockb)$|\.min\.(js|css)$|\.snap$|\.map$|"
    r"(^|/)(dist|build|vendor|node_modules|__generated__)/|\.pb\.go$|_pb2(_grpc)?\.py$|\.generated\.", re.I)
GUIDELINE_NAMES = ("CLAUDE.md", "AGENTS.md", "REVIEW.md", ".cursorrules", "CONTRIBUTING.md")


# --------------------------------------------------------------------------- utils

class DagError(Exception):
    pass


def die(msg: str, code: int = 1):
    print(json.dumps({"ok": False, "error": msg}, indent=2))
    sys.exit(code)


def emit(obj):
    print(json.dumps(obj, indent=2))


def read_json(path: Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def git(args, cwd=None) -> str:
    r = subprocess.run(["git", *args], capture_output=True, text=True, cwd=cwd)
    if r.returncode != 0:
        raise DagError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def slug(text: str, n: int = 40) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return (s[:n].strip("-")) or "root"


def split_path_range(spec: str):
    """'src/a.py:10-80' -> ('src/a.py', (10, 80)); 'src/a.py' -> ('src/a.py', None)."""
    m = re.match(r"^(.*?):(\d+)-(\d+)$", spec)
    if m:
        return m.group(1), (int(m.group(2)), int(m.group(3)))
    return spec, None


class Run:
    """Paths and loaded documents of one review run."""

    def __init__(self, d: str):
        self.dir = Path(d).resolve()
        self.context_path = self.dir / "context.json"
        self.plan_path = self.dir / "plan.json"
        self.state_path = self.dir / "state.json"
        self.findings_path = self.dir / "findings.json"
        self.results_dir = self.dir / "results"
        self.prompts_dir = self.dir / "prompts"

    def context(self):
        if not self.context_path.exists():
            raise DagError(f"no context at {self.context_path}; run `init` first")
        return read_json(self.context_path)

    def state(self):
        if not self.state_path.exists():
            raise DagError(f"no state at {self.state_path}; run `load` first")
        return read_json(self.state_path)

    def save_state(self, st):
        st["updated"] = int(time.time())
        write_json(self.state_path, st)

    def result_file(self, nid):
        return self.results_dir / f"{nid}.json"

    def prompt_file(self, nid):
        return self.prompts_dir / f"{nid}.md"


# --------------------------------------------------------------------------- init

def default_base(root: str) -> str:
    try:
        ref = git(["symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"], cwd=root).strip()
        if ref:
            return ref.replace("refs/remotes/", "")
    except DagError:
        pass
    for cand in ("origin/main", "origin/master", "main", "master"):
        try:
            git(["rev-parse", "--verify", "--quiet", cand], cwd=root)
            return cand
        except DagError:
            continue
    raise DagError("could not determine a base ref; pass --base")


def parse_numstat_z(out: str):
    """Parse `git diff --numstat -z -M`. Returns {path: (added, deleted, binary, old_path)}."""
    toks = out.split("\0")
    res, i = {}, 0
    while i < len(toks):
        tok = toks[i]
        if not tok:
            i += 1
            continue
        parts = tok.split("\t", 2)
        if len(parts) < 3:
            i += 1
            continue
        a, d, path = parts[0], parts[1], parts[2]
        old = None
        if path == "":  # rename/copy: next two tokens are old, new
            old, path = toks[i + 1], toks[i + 2]
            i += 3
        else:
            i += 1
        binary = a == "-" or d == "-"
        res[path] = (0 if binary else int(a), 0 if binary else int(d), binary, old)
    return res


def parse_name_status_z(out: str):
    toks = out.split("\0")
    res, i = {}, 0
    while i < len(toks):
        st = toks[i]
        if not st:
            i += 1
            continue
        if st[0] in "RC":
            res[toks[i + 2]] = st[0]
            i += 3
        else:
            res[toks[i + 1]] = st[0]
            i += 2
    return res


def classify(path: str, status: str, added: int, deleted: int, binary: bool):
    tags = []
    if SENSITIVE_RE.search(path):
        tags.append("sensitive")
    if TEST_RE.search(path):
        tags.append("test")
    if DOCS_RE.search(path):
        tags.append("docs")
    if GENERATED_RE.search(path):
        tags.append("generated")
    if binary:
        tags.append("binary")
    if status == "D":
        tags.append("deleted")
    elif added == 0 and deleted > 0:
        tags.append("deletion-only")
    skip = None
    if "generated" in tags:
        skip = "generated or lock file"
    elif binary:
        skip = "binary file"
    elif status == "D":
        skip = "file deleted (listed for the intent and cross-cutting nodes)"
    return tags, skip


def find_guidelines(root: Path, paths):
    found = set()
    for p in paths:
        cur = Path(p).parent
        while True:
            for name in GUIDELINE_NAMES:
                cand = root / cur / name
                if cand.is_file():
                    found.add((cur / name).as_posix())
            if cur == Path(".") or str(cur) in ("", "."):
                break
            cur = cur.parent
    return sorted(found)


def cmd_init(a, run: Run):
    if run.state_path.exists() and not a.force:
        raise DagError(f"a run already exists in {run.dir}; use `status` to resume, or --force to start over")
    root = git(["rev-parse", "--show-toplevel"]).strip()
    head = a.head or "HEAD"
    base = a.base or default_base(root)
    head_sha = git(["rev-parse", head], cwd=root).strip()
    merge_base = git(["merge-base", base, head_sha], cwd=root).strip()
    nums = parse_numstat_z(git(["diff", "--numstat", "-z", "-M", merge_base, head_sha], cwd=root))
    stats = parse_name_status_z(git(["diff", "--name-status", "-z", "-M", merge_base, head_sha], cwd=root))
    files = []
    for path in sorted(set(nums) | set(stats)):
        added, deleted, binary, old = nums.get(path, (0, 0, False, None))
        status = stats.get(path, "M")
        tags, skip = classify(path, status, added, deleted, binary)
        f = {"path": path, "status": status, "added": added, "deleted": deleted, "tags": tags}
        if old:
            f["old_path"] = old
        if skip:
            f["skip"] = skip
        files.append(f)
    if not files:
        raise DagError(f"no changes between {base} (merge-base {merge_base[:12]}) and {head}")

    reviewable = [f for f in files if "skip" not in f]
    lines = sum(f["added"] + f["deleted"] for f in reviewable)
    # deletions still count toward risk: removing an auth module is a security-relevant change
    lines += sum(f["deleted"] for f in files if "deleted" in f["tags"] and "generated" not in f["tags"])
    sensitive = any("sensitive" in f["tags"] for f in files if "generated" not in f["tags"])
    if a.tier:
        tier = a.tier
    elif sensitive or lines > LITE_LINES:
        tier = "full"
    elif lines <= TRIVIAL_LINES:
        tier = "trivial"
    else:
        tier = "lite"
    caps = {**DEFAULT_CAPS, **TIERS[tier]}
    if a.max_parallel:
        caps["max_parallel"] = a.max_parallel

    body = ""
    if a.pr_body_file:
        body = Path(a.pr_body_file).read_text(encoding="utf-8")
    ctx = {
        "version": VERSION,
        "created": int(time.time()),
        "run_dir": str(run.dir),
        "repo_root": root,
        "base": base,
        "head": head,
        "head_sha": head_sha,
        "merge_base": merge_base,
        "pr": {"number": a.pr_number, "title": a.pr_title or "", "body": body},
        "tier": tier,
        "tier_reason": ("forced" if a.tier else
                        "sensitive paths touched" if sensitive else f"{lines} reviewable changed lines"),
        "caps": caps,
        "files": files,
        "totals": {"files": len(files), "reviewable_files": len(reviewable), "reviewable_lines": lines,
                   "sensitive_files": sum("sensitive" in f["tags"] for f in reviewable)},
        "guideline_files": find_guidelines(Path(root), [f["path"] for f in files]),
    }
    if a.force and run.dir.exists():
        for p in (run.plan_path, run.state_path, run.findings_path):
            if p.exists():
                p.unlink()
        for sub in (run.results_dir, run.prompts_dir):
            if sub.exists():
                for p in sub.iterdir():
                    p.unlink()
    write_json(run.context_path, ctx)
    emit({"ok": True, "context": str(run.context_path), "tier": tier, "tier_reason": ctx["tier_reason"],
          "totals": ctx["totals"], "guideline_files": ctx["guideline_files"],
          "skipped": [{"path": f["path"], "reason": f["skip"]} for f in files if "skip" in f],
          "next": "run `autoplan`, optionally refine plan.json, then `load`"})


# --------------------------------------------------------------------------- autoplan

def _pack(files, budget, key):
    """Group files by key(path) then pack each group into chunks of <= budget changed lines."""
    groups = {}
    for f in files:
        groups.setdefault(key(f["path"]), []).append(f)
    chunks = []
    for k in sorted(groups):
        cur, cur_lines = [], 0
        for f in sorted(groups[k], key=lambda x: x["path"]):
            n = f["added"] + f["deleted"]
            if cur and cur_lines + n > budget:
                chunks.append((k, cur))
                cur, cur_lines = [], 0
            cur.append(f)
            cur_lines += n
        if cur:
            chunks.append((k, cur))
    return chunks


def _dirkey(depth):
    def key(p):
        parts = Path(p).parent.parts
        return "/".join(parts[:depth]) if parts else "."
    return key


def build_autoplan(ctx):
    caps = ctx["caps"]
    tier = ctx["tier"]
    files = ctx["files"]
    reviewable = [f for f in files if "skip" not in f]
    code = [f for f in reviewable if not ({"test", "docs"} & set(f["tags"]))]
    sensitive = [f for f in reviewable if "sensitive" in f["tags"]]
    all_paths = [f["path"] for f in files]
    rev_paths = [f["path"] for f in reviewable]

    def crosscuts():
        out = []
        if tier == "trivial" or not reviewable:
            return out
        if tier == "full" or sensitive:
            out.append({"id": "x-security", "kind": "crosscut", "lens": "security",
                        "title": "Security review across the change",
                        "files": [f["path"] for f in (sensitive or code or reviewable)],
                        "focus": "Trust boundaries, authn/authz, injection, secrets, unsafe deserialization, SSRF, "
                                 "path traversal, permission changes and removed checks."})
        if code:
            out.append({"id": "x-tests", "kind": "crosscut", "lens": "tests",
                        "title": "Test adequacy for the changed behaviour", "files": rev_paths,
                        "focus": "Is new or changed behaviour exercised? Do changed tests still assert the right "
                                 "thing? Were assertions weakened or tests deleted?"})
        if tier == "full" and code:
            out.append({"id": "x-performance", "kind": "crosscut", "lens": "performance",
                        "title": "Performance and resource use", "files": [f["path"] for f in code],
                        "focus": "Hot paths, N+1 queries, unbounded loops or memory, missing pagination, "
                                 "blocking I/O on request paths."})
        if ctx["guideline_files"]:
            out.append({"id": "x-guidelines", "kind": "crosscut", "lens": "guidelines",
                        "title": "Compliance with repository guideline files", "files": rev_paths,
                        "focus": "Only violations of rules you can quote verbatim from: "
                                 + ", ".join(ctx["guideline_files"])})
        for x in out:
            x["deps"] = ["intent"]
        return out

    budget = caps["leaf_line_budget"]
    depth_key = 2
    n_cross = len(crosscuts())
    for attempt in range(10):
        last_resort = attempt == 9
        nodes = [{"id": "intent", "kind": "intent", "title": "PR intent and risk map", "deps": [],
                  "files": all_paths,
                  "focus": "What the change does, which contracts or invariants it alters, where the risk is."}]
        if tier == "trivial":
            if reviewable:
                nodes.append({"id": "leaf-all", "kind": "leaf", "title": "Review the whole change",
                              "deps": ["intent"], "files": rev_paths})
        else:
            if last_resort:
                # ignore directories: balance files across exactly as many leaves as the cap allows
                slots = max(1, min(len(reviewable), caps["max_nodes"] - 1 - n_cross))
                bins = [[] for _ in range(slots)]
                load = [0] * slots
                for f in sorted(reviewable, key=lambda x: -(x["added"] + x["deleted"])):
                    j = load.index(min(load))
                    bins[j].append(f)
                    load[j] += f["added"] + f["deleted"]
                chunks = [("all", sorted(b, key=lambda x: x["path"])) for b in bins if b]
            else:
                chunks = _pack(reviewable, budget, _dirkey(depth_key))
            use_clusters = tier == "full" and not last_resort
            by_cluster = {}
            for k, fs in chunks:
                by_cluster.setdefault(k, []).append(fs)
            used = set()
            for k in sorted(by_cluster):
                parts = by_cluster[k]
                parent = "intent"
                if use_clusters and len(parts) > 1:
                    cid = f"cluster-{slug(k)}"
                    while cid in used:
                        cid += "-x"
                    used.add(cid)
                    nodes.append({"id": cid, "kind": "cluster", "title": f"Component: {k}", "deps": ["intent"],
                                  "files": [f["path"] for fs in parts for f in fs],
                                  "focus": "Map how these files interact and what changed contracts the "
                                           "file-level reviewers must keep in mind."})
                    parent = cid
                for i, fs in enumerate(parts, 1):
                    lid = f"leaf-{slug(k)}" + (f"-{i}" if len(parts) > 1 else "")
                    while lid in used:
                        lid += "-x"
                    used.add(lid)
                    nodes.append({"id": lid, "kind": "leaf", "title": f"Review {k}" + (f" (part {i})" if len(parts) > 1 else ""),
                                  "deps": [parent], "files": [f["path"] for f in fs]})
        nodes.extend(crosscuts())
        if len(nodes) <= caps["max_nodes"]:
            break
        budget *= 2
        if budget > 4000 and depth_key > 1:
            depth_key, budget = 1, caps["leaf_line_budget"]
    skipped = [{"path": f["path"], "reason": f["skip"]} for f in files if "skip" in f]
    return {"version": VERSION, "nodes": nodes, "skipped": skipped}


def cmd_autoplan(a, run: Run):
    ctx = run.context()
    plan = build_autoplan(ctx)
    write_json(run.plan_path, plan)
    kinds = {}
    for n in plan["nodes"]:
        kinds[n["kind"]] = kinds.get(n["kind"], 0) + 1
    emit({"ok": True, "plan": str(run.plan_path), "tier": ctx["tier"], "nodes": len(plan["nodes"]),
          "by_kind": kinds, "cap": ctx["caps"]["max_nodes"],
          "next": "optionally refine plan.json (see references/plan-format.md), then run `load`"})


# --------------------------------------------------------------------------- validation

def find_cycle(nodes: dict):
    """Kahn's algorithm. Returns a list of node ids involved in cycles (empty if acyclic)."""
    indeg = {k: 0 for k in nodes}
    children = {k: [] for k in nodes}
    for k, n in nodes.items():
        for d in n.get("deps", []):
            if d in nodes:
                indeg[k] += 1
                children[d].append(k)
    q = [k for k, v in indeg.items() if v == 0]
    seen = 0
    while q:
        k = q.pop()
        seen += 1
        for c in children[k]:
            indeg[c] -= 1
            if indeg[c] == 0:
                q.append(c)
    return sorted(k for k, v in indeg.items() if v > 0) if seen != len(nodes) else []


def longest_chain(nodes: dict) -> int:
    memo = {}

    def depth(k, stack=()):
        if k in memo:
            return memo[k]
        if k in stack:
            return 10 ** 6
        ds = [d for d in nodes[k].get("deps", []) if d in nodes]
        memo[k] = 1 + max((depth(d, stack + (k,)) for d in ds), default=0)
        return memo[k]

    return max((depth(k) for k in nodes), default=0)


def validate_plan(plan, ctx):
    errors, warnings = [], []
    caps = ctx["caps"]
    changed = {f["path"]: f for f in ctx["files"]}
    nodes_list = plan.get("nodes") if isinstance(plan, dict) else None
    if not isinstance(nodes_list, list) or not nodes_list:
        return ["plan.nodes must be a non-empty list"], warnings
    nodes = {}
    for i, n in enumerate(nodes_list):
        if not isinstance(n, dict):
            errors.append(f"nodes[{i}] is not an object")
            continue
        nid = n.get("id")
        if not isinstance(nid, str) or not ID_RE.match(nid):
            errors.append(f"nodes[{i}].id {nid!r} must match {ID_RE.pattern}")
            continue
        if nid in nodes:
            errors.append(f"duplicate node id {nid!r}")
            continue
        if n.get("kind") not in REVIEW_KINDS:
            errors.append(f"{nid}: kind must be one of {REVIEW_KINDS} (verify nodes are created by `collect`)")
        if n.get("kind") == "crosscut" and n.get("lens") not in LENSES:
            errors.append(f"{nid}: crosscut nodes need lens in {LENSES}")
        if not isinstance(n.get("title", ""), str):
            errors.append(f"{nid}: title must be a string")
        if nid.startswith("verify-"):
            errors.append(f"{nid}: ids starting with 'verify-' are reserved for verifier nodes")
        deps = n.get("deps", [])
        if not isinstance(deps, list) or not all(isinstance(d, str) for d in deps):
            errors.append(f"{nid}: deps must be a list of ids")
            n = {**n, "deps": []}
        files = n.get("files", [])
        if not isinstance(files, list) or not all(isinstance(f, str) for f in files):
            errors.append(f"{nid}: files must be a list of paths")
            files = []
        for spec in files:
            p, rng = split_path_range(spec)
            if p not in changed:
                errors.append(f"{nid}: file {p!r} is not part of the diff")
            if rng and rng[0] > rng[1]:
                errors.append(f"{nid}: bad line range in {spec!r}")
        if n.get("kind") in ("leaf", "cluster", "crosscut") and not files:
            errors.append(f"{nid}: {n.get('kind')} nodes must list files")
        nodes[nid] = n
    for nid, n in nodes.items():
        for d in n.get("deps", []) or []:
            if d == nid:
                errors.append(f"{nid}: depends on itself")
            elif d not in nodes:
                errors.append(f"{nid}: unknown dependency {d!r}")
    intents = [k for k, n in nodes.items() if n.get("kind") == "intent"]
    if len(intents) != 1:
        errors.append(f"plan needs exactly one intent node (found {len(intents)})")
    elif nodes[intents[0]].get("deps"):
        errors.append("the intent node must have no deps")
    cyc = find_cycle(nodes)
    if cyc:
        errors.append(f"dependency cycle among: {', '.join(cyc)}")
    else:
        depth = longest_chain(nodes)
        if depth > caps["max_depth"]:
            errors.append(f"graph depth {depth} exceeds max_depth {caps['max_depth']}")
    if len(nodes) > caps["max_nodes"]:
        errors.append(f"{len(nodes)} nodes exceeds the {ctx['tier']} tier cap of {caps['max_nodes']}")
    # coverage: every reviewable file must be owned by a leaf, or explicitly skipped with a reason
    skipped = {}
    for s in plan.get("skipped", []) or []:
        if not isinstance(s, dict) or not s.get("path") or not s.get("reason"):
            errors.append(f"skipped entries need path and reason: {s!r}")
            continue
        if s["path"] not in changed:
            errors.append(f"skipped path {s['path']!r} is not part of the diff")
        skipped[s["path"]] = s["reason"]
    leaf_owned = set()
    for n in nodes.values():
        if n.get("kind") == "leaf":
            leaf_owned.update(split_path_range(f)[0] for f in n.get("files", []))
    for p, f in changed.items():
        if p in leaf_owned or p in skipped:
            continue
        if "skip" in f:
            warnings.append(f"{p}: not reviewed ({f['skip']})")
            continue
        errors.append(f"{p}: changed file is not owned by any leaf node and not listed in plan.skipped")
    return errors, warnings


def cmd_load(a, run: Run):
    ctx = run.context()
    if run.state_path.exists() and not a.force:
        raise DagError("state.json already exists; use `status` to resume or `load --force` to replace it")
    plan = read_json(Path(a.plan) if a.plan else run.plan_path)
    errors, warnings = validate_plan(plan, ctx)
    if errors:
        emit({"ok": False, "errors": errors, "warnings": warnings,
              "hint": "fix plan.json and run `load` again"})
        sys.exit(2)
    if a.dry_run:
        emit({"ok": True, "dry_run": True, "warnings": warnings})
        return
    nodes = {}
    for n in plan["nodes"]:
        spec = {
            "id": n["id"], "kind": n["kind"], "title": n.get("title", n["id"]),
            "deps": list(dict.fromkeys(n.get("deps", []))), "files": n.get("files", []),
            "focus": n.get("focus", ""), "lens": n.get("lens"),
            "redact_description": n.get("redact_description", n["kind"] != "intent"),
            "model": n.get("model"),
        }
        spec.update({"status": "pending", "attempts": 0, "expansion_depth": 0, "allow_expand": True,
                     "last_error": None})
        nodes[n["id"]] = spec
    st = {"version": VERSION, "phase": "review", "caps": ctx["caps"], "nodes": nodes,
          "skipped": plan.get("skipped", []), "warnings": warnings, "log": []}
    run.save_state(st)
    emit({"ok": True, "state": str(run.state_path), "nodes": len(nodes), "warnings": warnings,
          "next": "run `next` and launch every returned node as a parallel subagent"})


# --------------------------------------------------------------------------- scheduling

def children_map(nodes):
    ch = {k: [] for k in nodes}
    for k, n in nodes.items():
        for d in n["deps"]:
            if d in ch:
                ch[d].append(k)
    return ch


def critical_path(nodes):
    """Longest chain of not-yet-terminal descendants, counting the node itself."""
    ch = children_map(nodes)
    memo = {}

    def cp(k):
        if k not in memo:
            memo[k] = 1 + max((cp(c) for c in ch[k] if nodes[c]["status"] not in TERMINAL), default=0)
        return memo[k]

    return {k: cp(k) for k in nodes}


def risk(ctx_files, n):
    tags = {f["path"]: f["tags"] for f in ctx_files}
    score = sum(1 for spec in n.get("files", []) if "sensitive" in tags.get(split_path_range(spec)[0], []))
    if n.get("lens") == "security":
        score += 10
    return score


def ready_ids(st, ctx):
    nodes = st["nodes"]
    phase_kinds = REVIEW_KINDS if st["phase"] == "review" else ("verify",)
    out = [k for k, n in nodes.items()
           if n["status"] == "pending" and n["kind"] in phase_kinds
           and all(nodes[d]["status"] in TERMINAL for d in n["deps"])]
    cp = critical_path(nodes)
    out.sort(key=lambda k: (-cp[k], -risk(ctx["files"], nodes[k]), k))
    return out


def upstream_summaries(st, nid):
    """Direct deps plus the intent node, in dependency order."""
    nodes = st["nodes"]
    want = list(nodes[nid]["deps"])
    intent = next((k for k, n in nodes.items() if n["kind"] == "intent"), None)
    if intent and intent != nid and intent not in want:
        want.insert(0, intent)
    out = []
    for d in want:
        n = nodes[d]
        if n.get("summary"):
            out.append((d, n["title"], n["summary"]))
        elif n["status"] == "failed":
            out.append((d, n["title"], "(this upstream node failed; no context available - proceed without it)"))
    return out


def file_line(ctx_files, spec):
    p, rng = split_path_range(spec)
    f = next((x for x in ctx_files if x["path"] == p), None)
    if not f:
        return f"- `{spec}`"
    bits = [f"+{f['added']}/-{f['deleted']}", f["status"]]
    if f.get("old_path"):
        bits.append(f"renamed from {f['old_path']}")
    if f["tags"]:
        bits.append(", ".join(f["tags"]))
    where = f" (only lines {rng[0]}-{rng[1]} of the new file)" if rng else ""
    return f"- `{p}`{where} - {'; '.join(bits)}"


def render_prompt(run: Run, st, ctx, nid):
    n = st["nodes"][nid]
    kind = n["kind"]
    static = (PROMPTS_DIR / "common.md").read_text(encoding="utf-8") if kind != "verify" else ""
    static += "\n\n" + (PROMPTS_DIR / f"{kind}.md").read_text(encoding="utf-8")
    caps = st["caps"]
    # --- everything below is node specific; keep the static prefix above identical across siblings
    L = ["", "---", "", "# Your assignment", ""]
    L.append(f"- **Node:** `{nid}` - kind `{kind}`" + (f", lens `{n['lens']}`" if n.get("lens") else ""))
    L.append(f"- **Title:** {n['title']}")
    if n.get("focus"):
        L.append(f"- **Focus:** {n['focus']}")
    L.append(f"- **Repository root:** `{ctx['repo_root']}`")
    rng = f"{ctx['merge_base']} {ctx['head_sha']}"
    L.append(f"- **Diff command:** `git -C {ctx['repo_root']} diff {rng} -- <paths>` "
             f"(merge-base of `{ctx['base']}` .. `{ctx['head']}`)")
    L.append(f"- **Code at head:** read files from the working tree only if `git -C {ctx['repo_root']} rev-parse HEAD` "
             f"is `{ctx['head_sha'][:12]}`; otherwise use `git -C {ctx['repo_root']} show {ctx['head_sha'][:12]}:<path>`.")
    if kind != "verify":
        can = n["allow_expand"] and n["expansion_depth"] < caps["max_expansion_depth"] and kind in ("leaf", "cluster")
        L.append(f"- **May request expansion:** {'yes' if can else 'no - review the whole scope yourself'}"
                 + (f" (a leaf should own at most ~{caps['leaf_line_budget']} changed lines)" if can else ""))
        L.append(f"- **Finding cap:** report at most {caps['max_findings_per_node']} findings, most severe first.")
    L += ["", "## Files in scope", ""]
    files = n.get("files") or []
    if kind == "intent" or not files:
        files = [f["path"] for f in ctx["files"]]
    L += [file_line(ctx["files"], s) for s in files]
    if kind == "intent":
        sk = [f for f in ctx["files"] if "skip" in f]
        if sk:
            L += ["", "Files excluded from line-by-line review (you may still mention them):"]
            L += [f"- `{f['path']}` - {f['skip']}" for f in sk]
    if kind in ("crosscut", "cluster", "intent"):
        others = sorted({f["path"] for f in ctx["files"]} - {split_path_range(s)[0] for s in files})
        if others:
            L += ["", f"Other files changed in this PR (context only): {', '.join('`'+p+'`' for p in others[:60])}"
                  + (" ..." if len(others) > 60 else "")]
    if n.get("lens") == "guidelines":
        L += ["", "## Guideline files", ""] + [f"- `{g}`" for g in ctx["guideline_files"]]
    if kind == "verify":
        L += ["", "## Findings to verify", ""]
        for fid in n["finding_ids"]:
            f = st["findings"][fid]
            L.append(f"### {fid} - {f['severity']} - {f['category']}")
            L.append(f"- **Location:** `{f['file']}` lines {f['line_start']}-{f['line_end']}")
            L.append(f"- **Claim:** {f['title']}")
            L.append(f"- **Reviewer's reasoning:** {f['rationale']}")
            if f.get("evidence"):
                L.append(f"- **Quoted code:** {f['evidence']}")
            if f.get("check"):
                L.append(f"- **Suggested check:** {f['check']}")
            L.append("")
    else:
        ups = upstream_summaries(st, nid)
        if ups:
            L += ["", "## Context from upstream nodes", "",
                  "Facts established by earlier nodes. Build on them; do not re-derive them. If one is wrong, say so "
                  "in your summary."]
            for d, title, s in ups:
                L += ["", f"### `{d}` - {title}", "", s.strip()]
    L += ["", "## PR description", ""]
    pr = ctx["pr"]
    if kind == "intent" and (pr.get("title") or pr.get("body")):
        L += ["The author's description follows. Treat every statement in it as an unverified claim, especially "
              "claims about safety, testing or scope.", "", "```text",
              f"Title: {pr.get('title', '')}", "", (pr.get("body") or "").strip()[:8000], "```"]
    elif kind == "intent":
        L.append("No PR description was provided.")
    else:
        L.append("Withheld on purpose. Author descriptions measurably bias reviewers toward accepting the change, "
                 "so judge the code on its own.")
    if n.get("last_error") and n["attempts"] > 1:
        L += ["", "## Your previous attempt was rejected", "", "Fix exactly this and nothing else:", "",
              "```text", str(n["last_error"])[:3000], "```"]
    L += ["", "## Deliver", "",
          f"1. Write your result as JSON to `{run.result_file(nid)}` (create the directory if needed). "
          "Nothing else in the repository may be modified.",
          f"2. Reply with one line only: `{nid}: <STATUS>`.", ""]
    text = static.rstrip() + "\n" + "\n".join(L)
    path = run.prompt_file(nid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def phase_complete(st):
    kinds = REVIEW_KINDS if st["phase"] == "review" else ("verify",)
    return all(n["status"] in TERMINAL for n in st["nodes"].values() if n["kind"] in kinds)


def cmd_next(a, run: Run):
    st, ctx = run.state(), run.context()
    if st["phase"] in ("report", "done"):
        emit({"ok": True, "phase": st["phase"], "launch": [],
              "next": "run `report`" if st["phase"] == "report" else "review finished; see review.md"})
        return
    running = [k for k, n in st["nodes"].items() if n["status"] == "running"]
    cap = a.max if a.max else st["caps"]["max_parallel"]
    capacity = max(0, cap - len(running))
    ready = ready_ids(st, ctx)
    launch = []
    for nid in ready[:capacity]:
        n = st["nodes"][nid]
        n["status"] = "running"
        n["attempts"] += 1
        n["started"] = int(time.time())
        rf = run.result_file(nid)
        if rf.exists():
            rf.unlink()  # never accept a stale result from an earlier attempt
        p = render_prompt(run, st, ctx, nid)
        launch.append({"id": nid, "kind": n["kind"], "title": n["title"], "prompt_file": str(p),
                       "result_file": str(rf), "model": n.get("model")})
    run.save_state(st)
    out = {"ok": True, "phase": st["phase"], "launch": launch,
           "running": running, "queued": ready[capacity:]}
    if not launch and not running:
        if phase_complete(st):
            out["phase_complete"] = st["phase"]
            out["next"] = "run `collect`" if st["phase"] == "review" else "run `report`"
        else:
            out["stuck"] = True
            out["next"] = "no node is ready; check `status` (a dependency may be pending in another phase)"
    elif launch:
        out["next"] = ("launch every node above as a subagent in ONE message, then run `complete <id>` for each "
                       "as it finishes, then `next` again")
    else:
        out["next"] = "wait for running nodes, `complete` them, then call `next` again"
    emit(out)


# --------------------------------------------------------------------------- results

def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def validate_finding(f, i, changed_paths):
    errs = []
    if not isinstance(f, dict):
        return [f"findings[{i}] is not an object"], None
    for k in ("file", "severity", "category", "title", "rationale"):
        if not isinstance(f.get(k), str) or not f.get(k).strip():
            errs.append(f"findings[{i}].{k} must be a non-empty string")
    if not isinstance(f.get("severity"), str) or f.get("severity") not in SEVERITIES:
        errs.append(f"findings[{i}].severity must be one of {SEVERITIES}")
    ls = f.get("line_start")
    le = f.get("line_end", ls)
    if not isinstance(ls, int) or isinstance(ls, bool) or ls < 1:
        errs.append(f"findings[{i}].line_start must be a positive integer (line in the NEW file)")
    elif not isinstance(le, int) or isinstance(le, bool) or le < ls:
        errs.append(f"findings[{i}].line_end must be an integer >= line_start")
    c = f.get("confidence")
    if not _num(c) or not 0 <= c <= 1:
        errs.append(f"findings[{i}].confidence must be a number between 0 and 1")
    if errs:
        return errs, None
    clean = {k: f[k] for k in ("file", "severity", "category", "title", "rationale", "confidence")}
    clean["line_start"], clean["line_end"] = ls, le
    for k in ("evidence", "suggested_fix", "check"):
        if isinstance(f.get(k), str) and f[k].strip():
            clean[k] = f[k]
    clean["category"] = clean["category"].strip().lower()
    clean["outside_diff"] = clean["file"] not in changed_paths
    return [], clean


def validate_review_result(res, n, ctx, caps):
    errs = []
    if not isinstance(res, dict):
        return ["result must be a JSON object"], None
    if res.get("node_id") != n["id"]:
        errs.append(f"node_id must be {n['id']!r}")
    status = res.get("status")
    if not isinstance(status, str) or status not in RESULT_STATUSES:
        errs.append(f"status must be one of {sorted(RESULT_STATUSES)}")
    summary = res.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        errs.append("summary must be a non-empty string")
    elif len(summary) > caps["summary_chars"] * 2:
        errs.append(f"summary is {len(summary)} chars; keep it under {caps['summary_chars']}")
    changed = {f["path"] for f in ctx["files"]}
    findings = []
    raw = res.get("findings", [])
    if not isinstance(raw, list):
        errs.append("findings must be a list")
        raw = []
    for i, f in enumerate(raw):
        e, clean = validate_finding(f, i, changed)
        errs += e
        if clean:
            findings.append(clean)
    declined = res.get("declined", [])
    if not isinstance(declined, list) or not all(isinstance(d, dict) and d.get("scope") and d.get("reason")
                                                 for d in declined):
        errs.append("declined must be a list of {scope, reason} objects")
        declined = []
    children = None
    if status == "NEEDS_EXPANSION":
        children = res.get("children")
        if not isinstance(children, list) or len(children) < 2:
            errs.append("NEEDS_EXPANSION requires a children list with at least 2 entries")
    if status == "BLOCKED" and not isinstance(res.get("blocked_reason"), str):
        errs.append("BLOCKED requires blocked_reason")
    if errs:
        return errs, None
    findings.sort(key=lambda f: (SEV_RANK[f["severity"]], -f["confidence"]))
    dropped = max(0, len(findings) - caps["max_findings_per_node"])
    return [], {"status": status, "summary": summary.strip()[: caps["summary_chars"] * 2],
                "findings": findings[: caps["max_findings_per_node"]], "dropped_over_cap": dropped,
                "declined": declined, "children": children, "blocked_reason": res.get("blocked_reason")}


def validate_verify_result(res, n):
    errs = []
    if not isinstance(res, dict):
        return ["result must be a JSON object"], None
    if res.get("node_id") != n["id"]:
        errs.append(f"node_id must be {n['id']!r}")
    verdicts = res.get("verdicts")
    if not isinstance(verdicts, list):
        return errs + ["verdicts must be a list"], None
    got = {}
    for i, v in enumerate(verdicts):
        if not isinstance(v, dict):
            errs.append(f"verdicts[{i}] is not an object")
            continue
        fid = v.get("finding_id")
        if not isinstance(fid, str) or fid not in n["finding_ids"]:
            errs.append(f"verdicts[{i}].finding_id {fid!r} was not assigned to this node")
            continue
        if not isinstance(v.get("verdict"), str) or v.get("verdict") not in VERDICTS:
            errs.append(f"verdicts[{i}].verdict must be one of {sorted(VERDICTS)}")
        if not isinstance(v.get("evidence"), str) or not v["evidence"].strip():
            errs.append(f"verdicts[{i}].evidence must explain what you checked")
        for k in ("check", "suggested_fix"):
            if v.get(k) is not None and not isinstance(v.get(k), str):
                errs.append(f"verdicts[{i}].{k} must be a string")
        if v.get("severity") is not None and (not isinstance(v.get("severity"), str)
                                              or v.get("severity") not in SEVERITIES):
            errs.append(f"verdicts[{i}].severity must be one of {SEVERITIES} or omitted")
        got[fid] = {k: v.get(k) for k in ("verdict", "evidence", "severity", "check", "suggested_fix")
                    if v.get(k) is not None}
    missing = [f for f in n["finding_ids"] if f not in got]
    if missing:
        errs.append(f"missing verdicts for: {', '.join(missing)}")
    return (errs, None) if errs else ([], got)


def retry_or_fail(st, n, error, count_attempt=True):
    if not count_attempt:
        n["attempts"] = max(0, n["attempts"] - 1)
    n["last_error"] = error if isinstance(error, str) else "\n".join(error)
    if n["attempts"] < st["caps"]["max_attempts"]:
        n["status"] = "pending"
        return "pending"
    n["status"] = "failed"
    return "failed"


def expand(st, ctx, n, children):
    """ADaPT-style as-needed decomposition: split one node into leaf children at runtime."""
    caps = st["caps"]
    nodes = st["nodes"]
    if not n["allow_expand"] or n["kind"] not in ("leaf", "cluster") \
            or n["expansion_depth"] >= caps["max_expansion_depth"]:
        return "expansion is not allowed for this node; review the whole scope yourself and return DONE"
    review_count = sum(1 for x in nodes.values() if x["kind"] in REVIEW_KINDS)
    budget = int(caps["max_nodes"] * 1.5)
    if review_count + len(children) > budget:
        return (f"expansion refused: the graph would exceed its node budget ({budget}); review the whole scope "
                "yourself, prioritising the riskiest hunks, and list anything you could not cover under `declined`")
    parent_paths = {split_path_range(f)[0] for f in n["files"]}
    covered = set()
    new = []
    for i, c in enumerate(children, 1):
        if not isinstance(c, dict) or not isinstance(c.get("files"), list) or not c["files"] \
                or not all(isinstance(s, str) for s in c["files"]):
            return f"children[{i - 1}] needs a non-empty files list of path strings"
        for spec in c["files"]:
            p, _ = split_path_range(spec)
            if p not in parent_paths:
                return f"children[{i - 1}] lists {p!r}, which is outside this node's scope"
            covered.add(p)
        new.append({"id": f"{n['id']}.{i}", "kind": "leaf", "title": str(c.get("title") or f"{n['title']} / part {i}"),
                    "deps": [n["id"]], "files": c["files"], "focus": str(c.get("focus") or ""),
                    "lens": None, "redact_description": True, "model": n.get("model"),
                    "status": "pending", "attempts": 0, "expansion_depth": n["expansion_depth"] + 1,
                    "allow_expand": True, "last_error": None})
    missing = parent_paths - covered
    if missing:
        return f"children must cover every file in scope; missing: {', '.join(sorted(missing))}"
    for c in new:
        if c["id"] in nodes:
            return f"child id collision {c['id']!r}"
    # rewire: anything waiting on the parent now waits on the children too
    for x in nodes.values():
        if n["id"] in x["deps"]:
            x["deps"] = x["deps"] + [c["id"] for c in new]
    for c in new:
        nodes[c["id"]] = c
    cyc = find_cycle(nodes)
    if cyc:  # cannot happen with the rules above, but never leave a cyclic graph behind
        for c in new:
            del nodes[c["id"]]
        for x in nodes.values():
            x["deps"] = [d for d in x["deps"] if d not in {c["id"] for c in new}]
        return f"expansion would create a cycle among {cyc}"
    return [c["id"] for c in new]


def cmd_complete(a, run: Run):
    st, ctx = run.state(), run.context()
    out = []
    for nid in a.ids:
        n = st["nodes"].get(nid)
        if not n:
            out.append({"id": nid, "ok": False, "error": "unknown node"})
            continue
        if n["status"] != "running" and not a.force:
            out.append({"id": nid, "ok": False, "error": f"node is {n['status']}, not running (use --force)"})
            continue
        path = Path(a.result) if a.result and len(a.ids) == 1 else run.result_file(nid)
        try:
            res = read_json(path)
        except FileNotFoundError:
            new = retry_or_fail(st, n, f"no result file was written at {path}")
            out.append({"id": nid, "ok": False, "status": new, "error": n["last_error"]})
            continue
        except json.JSONDecodeError as e:
            new = retry_or_fail(st, n, f"result file is not valid JSON: {e}")
            out.append({"id": nid, "ok": False, "status": new, "error": n["last_error"]})
            continue
        n["finished"] = int(time.time())
        if n["kind"] == "verify":
            errs, verdicts = validate_verify_result(res, n)
            if errs:
                new = retry_or_fail(st, n, errs)
                out.append({"id": nid, "ok": False, "status": new, "errors": errs})
                continue
            n["verdicts"] = verdicts
            n["status"] = "done"
            out.append({"id": nid, "ok": True, "status": "done",
                        "verdicts": {k: v["verdict"] for k, v in verdicts.items()}})
            continue
        errs, r = validate_review_result(res, n, ctx, st["caps"])
        if errs:
            new = retry_or_fail(st, n, errs)
            out.append({"id": nid, "ok": False, "status": new, "errors": errs})
            continue
        n["summary"] = r["summary"]
        n["findings"] = r["findings"]
        n["declined"] = r["declined"]
        n["result_status"] = r["status"]
        if r["dropped_over_cap"]:
            n["declined"] = n["declined"] + [{"scope": f"{r['dropped_over_cap']} lower-severity findings",
                                              "reason": "over the per-node finding cap"}]
        if r["status"] == "NEEDS_EXPANSION":
            res_exp = expand(st, ctx, n, r["children"])
            if isinstance(res_exp, str):
                first_refusal = n["allow_expand"]
                n["allow_expand"] = False
                # refund the attempt only the first time; a node that keeps asking must eventually fail
                new = retry_or_fail(st, n, res_exp, count_attempt=not first_refusal)
                out.append({"id": nid, "ok": False, "status": new, "error": res_exp})
            else:
                n["status"] = "expanded"
                out.append({"id": nid, "ok": True, "status": "expanded", "added_nodes": res_exp})
            continue
        if r["status"] == "BLOCKED":
            new = retry_or_fail(st, n, f"BLOCKED: {r['blocked_reason']}")
            out.append({"id": nid, "ok": False, "status": new, "error": n["last_error"]})
            continue
        n["status"] = "done"
        out.append({"id": nid, "ok": True, "status": "done", "findings": len(r["findings"])})
    run.save_state(st)
    emit({"ok": all(o.get("ok") for o in out), "results": out,
          "next": "call `next` (rejected nodes are re-queued automatically until max_attempts)"})


def cmd_fail(a, run: Run):
    st = run.state()
    n = st["nodes"].get(a.id)
    if not n:
        raise DagError(f"unknown node {a.id}")
    new = retry_or_fail(st, n, a.reason or "subagent did not finish")
    run.save_state(st)
    emit({"ok": True, "id": a.id, "status": new})


def cmd_reclaim(a, run: Run):
    """After a crash or context reset: return running nodes to the queue without charging an attempt."""
    st = run.state()
    back = []
    for k, n in st["nodes"].items():
        if n["status"] == "running":
            if run.result_file(k).exists():
                continue  # finished but never completed; `complete` it instead
            n["status"] = "pending"
            n["attempts"] = max(0, n["attempts"] - 1)
            back.append(k)
    finished = [k for k, n in st["nodes"].items() if n["status"] == "running"]
    run.save_state(st)
    emit({"ok": True, "requeued": back, "have_results_run_complete": finished})


# --------------------------------------------------------------------------- collect / verify

def _overlap(a, b, slack=3):
    return a["file"] == b["file"] and a["line_start"] <= b["line_end"] + slack and b["line_start"] <= a["line_end"] + slack


def _similar(a, b):
    if a["category"] == b["category"]:
        return True
    return difflib.SequenceMatcher(None, a["title"].lower(), b["title"].lower()).ratio() >= 0.55


def dedupe(findings):
    merged = []
    for f in sorted(findings, key=lambda x: (x["file"], x["line_start"], SEV_RANK[x["severity"]])):
        for m in merged:
            if _overlap(m, f) and _similar(m, f):
                lo = min(m["line_start"], f["line_start"])
                hi = max(m["line_end"], f["line_end"])
                better = (SEV_RANK[f["severity"]], -f["confidence"]) < (SEV_RANK[m["severity"]], -m["confidence"])
                carried = {"sources": sorted(set(m["sources"]) | set(f["sources"])),
                           "lenses": sorted(set(m["lenses"]) | set(f["lenses"])),
                           "also_reported_as": list(m["also_reported_as"]),
                           "confidence": max(m["confidence"], f["confidence"]),
                           "line_start": lo, "line_end": hi}
                alt = m["title"] if better else f["title"]
                if better:  # replace wholesale so evidence/fix/check all describe the same finding
                    m.clear()
                    m.update(f)
                m.update(carried)
                if alt not in m["also_reported_as"] and alt != m["title"]:
                    m["also_reported_as"].append(alt)
                break
        else:
            merged.append({**f, "also_reported_as": []})
    return merged


def cmd_collect(a, run: Run):
    st = run.state()
    if st["phase"] != "review":
        raise DagError(f"collect runs once, at the end of the review phase (phase is {st['phase']})")
    if not phase_complete(st) and not a.force:
        pend = [k for k, n in st["nodes"].items() if n["status"] not in TERMINAL]
        raise DagError(f"review phase not finished; unfinished nodes: {', '.join(pend)}")
    caps = st["caps"]
    raw = []
    for k, n in st["nodes"].items():
        for f in n.get("findings", []) or []:
            raw.append({**f, "sources": [k], "lenses": [n.get("lens") or n["kind"]]})
    discarded = [f for f in raw if f["confidence"] < caps["min_confidence"]]
    kept = [f for f in raw if f["confidence"] >= caps["min_confidence"]]
    merged = dedupe(kept)
    merged.sort(key=lambda f: (SEV_RANK[f["severity"]], -len(f["sources"]), -f["confidence"], f["file"], f["line_start"]))
    findings = {}
    for i, f in enumerate(merged, 1):
        fid = f"F{i:03d}"
        f["id"] = fid
        f["corroborated"] = len(f["sources"]) > 1
        f["verification"] = "pending"
        findings[fid] = f
    # one verifier per critical/major finding; minor findings batched per file (<=4); nits never verified
    groups = []
    minor_by_file = {}
    for fid, f in findings.items():
        if f["severity"] in ("critical", "major"):
            groups.append([fid])
        elif f["severity"] == "minor":
            minor_by_file.setdefault(f["file"], []).append(fid)
        else:
            f["verification"] = "skipped-nit"
    for fids in minor_by_file.values():
        for i in range(0, len(fids), 4):
            groups.append(fids[i:i + 4])
    overflow = groups[caps["max_verify"]:]
    groups = groups[:caps["max_verify"]]
    for g in overflow:
        for fid in g:
            findings[fid]["verification"] = "not-verified-budget"
    for i, g in enumerate(groups, 1):
        vid = f"verify-{i:03d}"
        st["nodes"][vid] = {
            "id": vid, "kind": "verify", "title": f"Verify {', '.join(g)}", "deps": [],
            "files": sorted({findings[f]["file"] for f in g}), "focus": "", "lens": None,
            "redact_description": True, "model": None, "finding_ids": g,
            "status": "pending", "attempts": 0, "expansion_depth": 0, "allow_expand": False, "last_error": None}
    st["findings"] = findings
    st["discarded_low_confidence"] = len(discarded)
    st["phase"] = "verify" if groups else "report"
    run.save_state(st)
    write_json(run.findings_path, {"findings": findings, "discarded_low_confidence": len(discarded)})
    emit({"ok": True, "phase": st["phase"], "raw_findings": len(raw), "after_dedupe": len(findings),
          "discarded_low_confidence": len(discarded), "verify_nodes": len(groups),
          "not_verified_budget": sum(len(g) for g in overflow),
          "next": "run `next` to launch verifiers" if groups else "run `report`"})


# --------------------------------------------------------------------------- report

def cmd_report(a, run: Run):
    st, ctx = run.state(), run.context()
    if st["phase"] == "review":
        raise DagError("run `collect` first")
    if st["phase"] == "verify" and not phase_complete(st) and not a.force:
        raise DagError("verification not finished; keep calling `next` / `complete`, or pass --force")
    findings = st.get("findings", {})
    for n in st["nodes"].values():
        if n["kind"] != "verify":
            continue
        for fid in n["finding_ids"]:
            f = findings[fid]
            v = (n.get("verdicts") or {}).get(fid)
            if v:
                f["verification"] = v["verdict"]
                f["verifier_evidence"] = v.get("evidence")
                if v.get("check"):
                    f["verifier_check"] = v["check"]
                if v.get("suggested_fix") and not f.get("suggested_fix"):
                    f["suggested_fix"] = v["suggested_fix"]
                if v.get("severity") and v["severity"] != f.get("original_severity", f["severity"]):
                    f.setdefault("original_severity", f["severity"])
                    f["severity"] = v["severity"]
            elif n["status"] == "failed":
                f["verification"] = "verifier-failed"
    min_rank = SEV_RANK[a.min_severity]
    order = lambda f: (SEV_RANK[f["severity"]], f["file"], f["line_start"])  # noqa: E731
    confirmed = sorted([f for f in findings.values() if f["verification"] == "confirmed"
                        and SEV_RANK[f["severity"]] <= min_rank], key=order)
    human = sorted([f for f in findings.values()
                    if f["verification"] in ("unverifiable", "not-verified-budget", "verifier-failed")
                    and SEV_RANK[f["severity"]] <= SEV_RANK["major"]], key=order)
    refuted = [f for f in findings.values() if f["verification"] == "refuted"]
    nits = sorted([f for f in findings.values() if f["verification"] == "skipped-nit"], key=order)
    review_nodes = [n for n in st["nodes"].values() if n["kind"] in REVIEW_KINDS]
    failed = [n for n in st["nodes"].values() if n["status"] == "failed"]
    declined = [(n["id"], d) for n in review_nodes for d in (n.get("declined") or [])]
    intent = next((n for n in review_nodes if n["kind"] == "intent"), None)
    sha = ctx["head_sha"]

    def loc(f):
        return f"`{f['file']}:{f['line_start']}" + (f"-{f['line_end']}`" if f["line_end"] != f["line_start"] else "`")

    def block(f):
        lines = [f"#### {f['id']} · {f['severity'].upper()} · {f['title']}", "",
                 f"{loc(f)} - {f['category']} - found by {', '.join(f['sources'])}"
                 + (" (independently corroborated)" if f.get("corroborated") else ""), "", f["rationale"].strip()]
        if f.get("verifier_evidence"):
            lines += ["", f"**Verification:** {f['verifier_evidence'].strip()}"]
        if f.get("verifier_check"):
            lines += ["", f"**Check run:** {f['verifier_check']}"]
        if f.get("original_severity"):
            lines += ["", f"_Severity adjusted by verifier from {f['original_severity']}._"]
        if f.get("suggested_fix"):
            lines += ["", "**Suggested fix:**", "", f["suggested_fix"].strip()]
        return "\n".join(lines) + "\n"

    title = ctx["pr"].get("title") or f"{ctx['base']}...{ctx['head']}"
    L = [f"# Review: {title}", "",
         f"`{ctx['merge_base'][:10]}..{sha[:10]}` · tier **{ctx['tier']}** ({ctx['tier_reason']}) · "
         f"{ctx['totals']['reviewable_files']} files / {ctx['totals']['reviewable_lines']} lines reviewed · "
         f"{len(review_nodes)} review nodes · {sum(1 for n in st['nodes'].values() if n['kind']=='verify')} verifiers", "",
         f"**{len(confirmed)} confirmed issue(s)** · {len(human)} need a human look · "
         f"{len(refuted)} candidate(s) refuted by verification · {st.get('discarded_low_confidence', 0)} discarded as "
         f"low-confidence", ""]
    if intent and intent.get("summary"):
        L += ["## What this change does", "", intent["summary"].strip(), ""]
    L += ["## Confirmed issues", ""]
    if confirmed:
        for sev in SEVERITIES:
            group = [f for f in confirmed if f["severity"] == sev]
            if group:
                L += [f"### {sev.capitalize()}", ""] + [block(f) for f in group]
    else:
        L += ["No issues survived verification.", ""]
    if human:
        L += ["## Needs a human look", "",
              "Plausible, severe enough to matter, but not confirmed: the verifier could not settle it, "
              "ran out of budget, or failed.", ""]
        L += [block(f) for f in human]
    if a.include_nits and nits:
        L += ["## Nits (unverified)", ""] + [f"- {loc(f)} {f['title']}" for f in nits] + [""]
    gaps = []
    for n in failed:
        gaps.append(f"- Node `{n['id']}` ({n['title']}) failed: {str(n.get('last_error') or '')[:300]}")
    for nid, d in declined:
        gaps.append(f"- `{nid}` declined to judge **{d['scope']}**: {d['reason']}")
    for f in ctx["files"]:
        if "skip" in f:
            gaps.append(f"- `{f['path']}` not reviewed line by line: {f['skip']}")
    for s in st.get("skipped", []):
        if not any(s["path"] == f["path"] and "skip" in f for f in ctx["files"]):
            gaps.append(f"- `{s['path']}` skipped by the planner: {s['reason']}")
    L += ["## Coverage gaps", ""] + (gaps or ["None."]) + [""]
    L += ["<sub>Generated by dag-pr-review. Every confirmed issue was independently re-checked against the code by a "
          "verifier that did not see the author's description.</sub>", ""]
    md = "\n".join(L)
    out_md = run.dir / "review.md"
    out_md.write_text(md, encoding="utf-8")
    write_json(run.dir / "review.json", {
        "head_sha": sha, "merge_base": ctx["merge_base"], "tier": ctx["tier"],
        "confirmed": confirmed, "needs_human": human, "refuted": refuted, "nits": nits,
        "failed_nodes": [n["id"] for n in failed], "declined": [{"node": k, **d} for k, d in declined]})
    st["phase"] = "done"
    run.save_state(st)
    emit({"ok": True, "review_md": str(out_md), "review_json": str(run.dir / "review.json"),
          "confirmed": len(confirmed), "needs_human": len(human), "refuted": len(refuted),
          "failed_nodes": len(failed)})


# --------------------------------------------------------------------------- status

def cmd_status(a, run: Run):
    st = run.state()
    counts = {}
    for n in st["nodes"].values():
        counts.setdefault(n["kind"], {}).setdefault(n["status"], 0)
        counts[n["kind"]][n["status"]] += 1
    emit({"ok": True, "phase": st["phase"], "counts": counts,
          "running": [k for k, n in st["nodes"].items() if n["status"] == "running"],
          "failed": {k: n.get("last_error") for k, n in st["nodes"].items() if n["status"] == "failed"},
          "retrying": {k: n.get("last_error") for k, n in st["nodes"].items()
                       if n["status"] == "pending" and n.get("last_error")}})


def cmd_show(a, run: Run):
    st = run.state()
    n = st["nodes"].get(a.id)
    if not n:
        raise DagError(f"unknown node {a.id}")
    emit(n)


# --------------------------------------------------------------------------- cli

def main(argv=None):
    p = argparse.ArgumentParser(prog="dagctl", description=__doc__.split("\n\n")[0])
    p.add_argument("--dir", default=".dag-review", help="run directory (default: .dag-review)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="diff, classify files, choose a risk tier")
    s.add_argument("--base", help="base ref (default: origin/HEAD, origin/main, main ...)")
    s.add_argument("--head", help="head ref (default: HEAD)")
    s.add_argument("--pr-number", type=int)
    s.add_argument("--pr-title")
    s.add_argument("--pr-body-file", help="file holding the PR description (only the intent node sees it)")
    s.add_argument("--tier", choices=list(TIERS), help="override the automatic risk tier")
    s.add_argument("--max-parallel", type=int, help="override the concurrency cap")
    s.add_argument("--force", action="store_true", help="discard an existing run in --dir")
    s.set_defaults(fn=cmd_init)

    s = sub.add_parser("autoplan", help="write a deterministic draft plan.json")
    s.set_defaults(fn=cmd_autoplan)

    s = sub.add_parser("load", help="validate plan.json and create state.json")
    s.add_argument("--plan", help="plan file (default: <dir>/plan.json)")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_load)

    s = sub.add_parser("next", help="claim ready nodes and render their prompts")
    s.add_argument("--max", type=int, help="override max_parallel for this call")
    s.set_defaults(fn=cmd_next)

    s = sub.add_parser("complete", help="ingest result files for finished nodes")
    s.add_argument("ids", nargs="+")
    s.add_argument("--result", help="explicit result path (single id only)")
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_complete)

    s = sub.add_parser("fail", help="record that a node's subagent crashed or gave up")
    s.add_argument("id")
    s.add_argument("--reason")
    s.set_defaults(fn=cmd_fail)

    s = sub.add_parser("reclaim", help="requeue running nodes after an interruption")
    s.set_defaults(fn=cmd_reclaim)

    s = sub.add_parser("collect", help="dedupe findings and create verifier nodes")
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_collect)

    s = sub.add_parser("report", help="write review.md and review.json")
    s.add_argument("--min-severity", choices=SEVERITIES, default="minor")
    s.add_argument("--include-nits", action="store_true")
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_report)

    s = sub.add_parser("status", help="summarise the run")
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("show", help="print one node")
    s.add_argument("id")
    s.set_defaults(fn=cmd_show)

    a = p.parse_args(argv)
    try:
        a.fn(a, Run(a.dir))
    except DagError as e:
        die(str(e))


if __name__ == "__main__":
    main()
