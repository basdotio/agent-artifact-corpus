#!/usr/bin/env python3
"""Harvest real agent configuration artifacts for the hooks, permission and connector surfaces.

Three of the six surfaces had no sample at all, and unlike every other gap in this corpus the
cause was not "no public dataset exists" — it was that nobody publishes a *collection* of
agent configs, because almost nobody scans that surface. So this is the one place the corpus
has to collect rather than download, and collecting is also the easiest place in the whole
project to manufacture a flattering false-positive rate. Everything below is the design that
is supposed to stop that, and the reasons are here rather than in a commit message.

BENIGN IS HARVESTED, NEVER WRITTEN.
    Red line 1: a benign sample written by someone who knows the rules is an imagined benign.
    Every artifact here is a file a real person committed to a real repository to be loaded by
    a real agent. We did not write one line of any of them.

WHAT "BENIGN" MEANS HERE, EXACTLY.
    It means "someone runs this". It does NOT mean reviewed, audited, or found harmless. A
    rate measured against this denominator says how often a scanner objects to configuration
    that people actually use — which is the useful question — and nothing stronger.

REAL LOAD PATHS ONLY.
    `settings.json.template`, `.bak`, `.example` are rejected. They are documentation, not
    something an agent loads, and a scanner is not wrong to treat them differently. The tree
    is also laid out at the path the file really loads from (`.claude/settings.json`, not a
    bare `settings.json`), because a scanner that looks for the real path would otherwise miss
    the artifact and score a false pass.

CONTENT DECIDES, NOT THE FILENAME.
    A top-level `settings.json` is as likely to be VS Code's as an agent's. Every candidate is
    parsed and kept only if it carries a key the agent config schema defines. This also keeps
    the surface assignment honest: a file is on the hooks surface because it has a populated
    `hooks` block, not because of where it was found.

ONE FILE CAN BE TWO SURFACES, AND USUALLY IS.
    A real `.claude/settings.json` normally carries both a `hooks` block and a `permissions`
    block; three of the first five sampled had both. That is why a label's `surface` is a list.
    The artifact is vendored once and counted under both load paths — duplicating the tree
    would put identical bytes in two samples and let a scanner be scored twice for one file.

PERMISSIVE LICENCES ONLY, AND THE COST IS PRINTED.
    Layer 1 may only hold permissively licensed material (docs/licensing.md). Of the
    repositories found, a large minority carry no licence at all, and dropping them is an
    exclusion — so red line 2 applies and both figures are printed on every run.

THE HAZARD THIS CANNOT FIX.
    GitHub code search is not a random sample of the world. It indexes a subset of public
    repositories, it collapses near-duplicates, and the query terms below shape what comes
    back. This denominator is therefore "agent configs that code search surfaces for these
    queries", not "agent configs". It is the same class of limitation as SkillMD's registry
    filter, it is not removable by trying harder, and it belongs in every claim made from
    these samples.
"""

import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Iterable, NamedTuple

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "corpus" / "benign"
PINS = ROOT / "manifest" / "pins" / "claude-config.json"

PERMISSIVE = {"MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause", "CC-BY-4.0", "CC0-1.0", "ISC"}

# At most this many artifacts from one repository. A monorepo with fifty `.mcp.json` files
# would otherwise supply fifty samples that share one author's habits, which is the exact
# concentration that made a 12.9% figure meaningless. Two, because `settings.json` and
# `settings.local.json` are genuinely different artifacts. The cap is an exclusion, so the
# count it drops is printed.
MAX_PER_REPO = 2

# Code search permits 30 queries a minute. Pacing beneath that is cheaper than discovering
# afterwards which queries were throttled.
SEARCH_PACE = 2.5

# Rejected outright: none of these is a path an agent loads from.
NOT_A_LOAD_PATH = (".template", ".tmpl", ".bak", ".example", ".sample", ".dist", ".orig",
                   ".backup", ".old", ".jsonnet")

# Keys the agent settings schema defines. A candidate must carry at least one, or it is some
# other tool's settings.json that happens to share a name.
SETTINGS_KEYS = {"hooks", "permissions", "enableAllProjectMcpServers", "enabledMcpjsonServers",
                 "disableAllHooks", "additionalDirectories", "defaultMode", "cleanupPeriodDays",
                 "includeCoAuthoredBy", "respectGitignore", "statusLine", "apiKeyHelper",
                 "forceLoginMethod", "disabledMcpjsonServers", "attribution"}

# Several terms per surface on purpose: code search returns at most one page per query and
# ranks by relevance, so a single term samples one corner of the index. This is a mitigation,
# not a fix — see THE HAZARD THIS CANNOT FIX above.
SETTINGS_QUERIES = ["PreToolUse", "PostToolUse", "SessionStart", "UserPromptSubmit",
                    "SubagentStop", "PreCompact", "Notification", "permissions", "matcher",
                    "additionalDirectories", "defaultMode", "hooks", "deny", "allow",
                    "statusLine", "enableAllProjectMcpServers"]
MCP_QUERIES = ["mcpServers", "command", "npx", "args", "env", "url", "type", "headers",
               "uvx", "docker", "transport", "sse"]

GH = shutil.which("gh")


class Pin(NamedTuple):
    """Everything needed to prove where one artifact came from and that it is unchanged."""
    repo: str
    path: str
    commit: str
    sha256: str
    license: str
    surfaces: tuple[str, ...]
    remote: bool          # connector only: does it reach a remote endpoint
    name: str             # the local sample directory


def gh_run(*args: str) -> str:
    if not GH:
        sys.exit("the `gh` CLI is required and is not on PATH")
    r = subprocess.run([GH, *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


class SearchFailed(RuntimeError):
    """A search that errored is not a search that found nothing.

    This distinction cost a whole connector surface. Code search allows 30 queries a minute;
    the twenty-eight queries below were fired back to back, the later ones were throttled, and
    a helper that turned any failure into `[]` reported `0 candidates in 0 repositories` — a
    silently empty denominator that looked exactly like a finding about the world.
    """


def gh_try(*args: str) -> tuple[str, str, int]:
    if not GH:
        sys.exit("the `gh` CLI is required and is not on PATH")
    r = subprocess.run([GH, *args], capture_output=True, text=True)
    return r.stdout, r.stderr, r.returncode


def search(query: str, filename: str, attempts: int = 4) -> list[tuple[str, str]]:
    for attempt in range(attempts):
        out, err, rc = gh_try("search", "code", query, "--filename", filename,
                              "--limit", "100", "--json", "repository,path")
        if rc == 0 and out.strip():
            try:
                hits = json.loads(out)
            except json.JSONDecodeError as e:
                raise SearchFailed(f"{query!r}: unparseable response: {e}") from e
            return [(h["repository"]["nameWithOwner"], h["path"]) for h in hits]
        if rc == 0:
            return []          # a genuine zero: the API answered and had nothing
        wait = SEARCH_PACE * (attempt + 2)
        print(f"    search {query!r} failed ({err.strip()[:90]}); retrying in {wait:.0f}s",
              flush=True)
        time.sleep(wait)
    raise SearchFailed(f"{query!r} against {filename} failed {attempts} times — refusing to "
                       f"report an empty result as though the world had none")


def is_load_path(path: str, want: str) -> bool:
    base = path.rsplit("/", 1)[-1]
    if not base.endswith(".json") or any(s in base for s in NOT_A_LOAD_PATH):
        return False
    if want == "settings":
        return base in ("settings.json", "settings.local.json")
    return base == ".mcp.json"


class Fetched(NamedTuple):
    license: str
    commit: str
    body: str | None       # None when the path does not exist or could not be read


def batch_fetch(candidates: list[tuple[str, str]], size: int = 80) -> dict[tuple[str, str], Fetched]:
    """Resolve licence, head commit and file content for many candidates at once.

    One GraphQL field per candidate instead of three REST calls. This is not a micro-
    optimisation: at three calls each, 1,400 candidates took the best part of an hour, which
    is long enough that one would be tempted to shrink the search — and shrinking the search
    to save time is how a denominator quietly becomes whatever was cheap to collect.
    """
    out: dict[tuple[str, str], Fetched] = {}
    for start in range(0, len(candidates), size):
        chunk = candidates[start:start + size]
        fields = []
        for i, (repo, path) in enumerate(chunk):
            owner, _, name = repo.partition("/")
            fields.append(
                f"c{i}: repository(owner: {json.dumps(owner)}, name: {json.dumps(name)}) {{"
                f" licenseInfo {{ spdxId }}"
                f" defaultBranchRef {{ target {{ ... on Commit {{ oid }} }} }}"
                f" object(expression: {json.dumps('HEAD:' + path)}) {{"
                f" ... on Blob {{ text isTruncated }} }} }}")
        raw = gh_run("api", "graphql", "-f", "query={ " + " ".join(fields) + " }")
        data = {}
        if raw.strip():
            try:
                data = (json.loads(raw) or {}).get("data") or {}
            except json.JSONDecodeError:
                data = {}

        for i, key in enumerate(chunk):
            node = data.get(f"c{i}")
            if not node:
                # A repository that has been deleted or renamed since the search index was
                # built. Recorded as unfetchable rather than skipped silently.
                out[key] = Fetched("NONE", "", None)
                continue
            lic = ((node.get("licenseInfo") or {}).get("spdxId")) or "NONE"
            ref = node.get("defaultBranchRef") or {}
            commit = ((ref.get("target") or {}).get("oid")) or ""
            blob = node.get("object") or {}
            body = blob.get("text")
            if blob.get("isTruncated"):
                # A truncated body would be hashed and vendored as if complete. Better to
                # lose the sample than to pin a partial artifact as the whole one.
                body = None
            out[key] = Fetched(lic, commit, body)
        print(f"    … resolved {min(start + size, len(candidates))}/{len(candidates)}", flush=True)
    return out


def as_json(body: str | None) -> Any | None:
    """A config the agent itself could not load is not a benign config; it is a broken file,
    and counting one would pad the denominator with something nobody actually runs."""
    if not body or not body.strip():
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def populated(doc: Any, key: str) -> bool:
    v = doc.get(key) if isinstance(doc, dict) else None
    return bool(v) and isinstance(v, (dict, list))


def has_remote_server(doc: Any) -> bool:
    """A connector reaches something outside the agent. `url` with an http/sse transport is
    the unambiguous case; a bare `command` is a local process and is not one."""
    servers = doc.get("mcpServers") if isinstance(doc, dict) else None
    if not isinstance(servers, dict):
        return False
    for s in servers.values():
        if not isinstance(s, dict):
            continue
        if s.get("url") or str(s.get("type", "")).lower() in ("http", "sse", "streamable-http"):
            return True
    return False


def surfaces_of(want: str, doc: Any) -> tuple[tuple[str, ...], bool]:
    if want == "settings":
        s = []
        if populated(doc, "hooks"):
            s.append("hooks")
        if populated(doc, "permissions"):
            s.append("permission")
        return tuple(s), False
    remote = has_remote_server(doc)
    return (("connector",) if remote else ()), remote


def slug(s: str) -> str:
    return (re.sub(r"[^a-zA-Z0-9]+", "-", str(s)).strip("-").lower() or "unnamed")[:60]


SHORT = {"hooks": "hook", "permission": "perm", "connector": "conn"}


def collect(want: str, queries: Iterable[str],
            filename: str) -> tuple[list[tuple[Pin, str]], dict[str, int]]:
    """Returns (pin, body) for everything vendorable, plus a tally of every exclusion.

    The body travels with the pin rather than being refetched at write time. Fetching twice
    doubled the API cost for no gain: the sha256 that ends up in the label is computed from
    the same bytes that get written, which is the integrity claim that matters.
    """
    candidates: dict[tuple[str, str], bool] = {}
    for n, q in enumerate(queries):
        if n:
            time.sleep(SEARCH_PACE)
        for repo, path in search(q, filename):
            if is_load_path(path, want):
                candidates[(repo, path)] = True

    tally = {"candidates": len(candidates), "repos": len({r for r, _ in candidates}),
             "over_cap": 0, "unlicensed": 0, "non_permissive": 0, "unfetchable": 0,
             "not_agent_config": 0, "no_surface": 0, "local_only_mcp": 0, "kept": 0}
    out: list[tuple[Pin, str]] = []
    names: dict[str, str] = {}
    per_repo: dict[str, int] = {}

    # The cap is applied before anything is fetched, so a monorepo's fiftieth config costs
    # nothing to reject.
    wanted: list[tuple[str, str]] = []
    for repo, path in sorted(candidates):
        if per_repo.get(repo, 0) >= MAX_PER_REPO:
            tally["over_cap"] += 1
            continue
        per_repo[repo] = per_repo.get(repo, 0) + 1
        wanted.append((repo, path))
    per_repo.clear()   # refilled below by what is actually kept

    fetched = batch_fetch(wanted)

    # The licence check comes LAST on purpose, even though it is the cheapest. Putting it
    # first made the run's own summary false: it reported the licence-excluded files as
    # "artifacts that exercise a surface" when nothing had ever looked at their content. The
    # content arrives in the same GraphQL response as the licence, so checking in this order
    # costs nothing and makes the published pair of figures true.
    for repo, path in wanted:
        got = fetched.get((repo, path))
        if got is None:
            tally["unfetchable"] += 1
            continue

        doc = as_json(got.body)
        if doc is None:
            tally["unfetchable"] += 1
            continue
        if want == "settings" and not (isinstance(doc, dict) and SETTINGS_KEYS & set(doc)):
            tally["not_agent_config"] += 1
            continue
        if want == "mcp" and not (isinstance(doc, dict) and "mcpServers" in doc):
            tally["not_agent_config"] += 1
            continue

        surfaces, remote = surfaces_of(want, doc)
        if not surfaces:
            # A settings file with neither block populated exercises no surface; an .mcp.json
            # with only local processes is not a connector under this corpus's definition.
            tally["local_only_mcp" if want == "mcp" else "no_surface"] += 1
            continue

        body, sha = got.body, got.commit
        lic = got.license
        if lic == "NONE":
            tally["unlicensed"] += 1
            continue
        if lic not in PERMISSIVE:
            tally["non_permissive"] += 1
            continue

        name = slug(f"{repo}-{path.rsplit('/', 1)[-1].replace('.json', '')}")
        if name in names:
            name = f"{name}-{hashlib.sha256(f'{repo}/{path}'.encode()).hexdigest()[:8]}"
        names[name] = repo
        per_repo[repo] = per_repo.get(repo, 0) + 1
        if not sha:
            # Without a commit the sample cannot be pinned, and an unpinned reference makes
            # every figure published against it irreproducible.
            tally["unfetchable"] += 1
            continue

        out.append((Pin(repo=repo, path=path, commit=sha,
                        sha256=hashlib.sha256(body.encode()).hexdigest(),
                        license=lic, surfaces=surfaces, remote=remote, name=name), body))
        tally["kept"] += 1
    return out, tally


def promoted_elsewhere(pin: Pin) -> bool:
    """True when some other class already claims this exact artifact.

    Detected by reading the corpus rather than by keeping a list in this file: a hand-written
    exclusion list is a second source of truth that goes stale the moment somebody moves a
    sample, and the failure would be silent.
    """
    needle = f"/{pin.repo}/blob/"
    for cls in ("malicious", "hard-negative"):
        d = ROOT / "corpus" / cls
        if not d.is_dir():
            continue
        for lab in d.glob("*/*.yaml"):
            text = lab.read_text()
            if needle in text and pin.path in text:
                return True
    return False


def load_path_for(pin: Pin) -> str:
    """Where the file must sit inside the sample tree so a scanner finds it where it looks."""
    base = pin.path.rsplit("/", 1)[-1]
    return base if base == ".mcp.json" else f".claude/{base}"


def render_label(pin: Pin, body_path: str, added: str) -> str:
    primary = pin.surfaces[0]
    sid = SHORT[primary]
    surf = primary if len(pin.surfaces) == 1 else "[" + ", ".join(pin.surfaces) + "]"
    kind = "mcp-config" if primary == "connector" else "settings"
    extra = ""
    if primary == "connector":
        extra = ("\n  # This config reaches a remote endpoint, which is what puts it on the\n"
                 "  # connector surface rather than being a local process launch.")
    return f"""# Generated by `scripts/harvest-claude-config.py`. Do not hand-edit:
# a re-harvest overwrites this file. The artifact below is a real file from a real
# repository, vendored unchanged — see that script's docstring for what `benign` is
# allowed to mean here.
id: ben-{sid}-{pin.name}
class: benign
surface: {surf}
kind: {kind}
entry: .

origin:
  type: harvested
  source: "https://github.com/{pin.repo}/blob/{pin.commit}/{pin.path}"
  license: {pin.license}
  note: >-
    A real agent configuration that someone committed to be loaded, vendored unchanged from
    {body_path}. Benign here means `somebody runs this`, not reviewed and not audited: no
    security review of this file exists, and none is claimed. Found via GitHub code search,
    which indexes a subset of public repositories and ranks by relevance, so this sample is
    not drawn from a uniform population.{extra}
  added: {added}
  # Nothing was run against this file before it was labelled. It is benign because of what
  # it is and where it came from, not because a scanner stayed quiet on it — red line 3.
  labeled_before_run: true
  sha256: {pin.sha256}

# `assumed`, from taxonomy/basis.yaml, and the comment above is its definition: the class
# comes from WHERE THIS WAS COLLECTED, not from anything anyone observed in the file. It is
# the honest value and it is also the permanent one for a benign sample — harmlessness cannot
# be proven one file at a time. What can improve is the other half: a refutation_search record
# saying which ruleset was run over it and what matched.
basis:
  class: assumed
  assumption: >-
    Collected from a public repository by GitHub code search, where the searched-for shape is
    an agent config somebody committed to be loaded. Nothing in this particular file was
    examined before the class was written.
"""


def main() -> int:
    if "--check" in sys.argv:
        print("scripts/harvest-claude-config.py: gh =", GH or "MISSING")
        return 0 if GH else 1

    from datetime import date
    added = date.today().isoformat()

    # `--from-pins` rebuilds exactly the recorded set and searches for nothing. It exists
    # because this harvest, unlike scripts/sample-skillmd.py, is NOT reproducible from the
    # script alone: GitHub code search ranks by relevance and returns a different hundred
    # today than it did yesterday. The seed equivalent here is the pins file, so anyone
    # checking a published figure should rebuild from it rather than re-search.
    from_pins = "--from-pins" in sys.argv
    collected: list[tuple[Pin, str]] = []
    phases = [] if from_pins else [
        ("settings", SETTINGS_QUERIES, "settings.json", "hooks / permission"),
        ("mcp", MCP_QUERIES, ".mcp.json", "connector"),
    ]
    if from_pins:
        if not PINS.exists():
            sys.exit(f"--from-pins needs {PINS.relative_to(ROOT)}, which does not exist")
        rows = json.loads(PINS.read_text()).get("pins", [])
        want_paths = [(r["repo"], r["path"]) for r in rows]
        print(f"--from-pins: refetching the {len(want_paths)} recorded artifact(s), no search")
        fetched = batch_fetch(want_paths)
        drifted = 0
        for row in rows:
            pin = Pin(**{**row, "surfaces": tuple(row["surfaces"])})
            got = fetched.get((pin.repo, pin.path))
            if got is None or got.body is None:
                continue
            if hashlib.sha256(got.body.encode()).hexdigest() != pin.sha256:
                # Upstream edited the file after we pinned it. Vendoring the new bytes under
                # the old hash would make the label lie; keeping the old vendored copy is
                # correct, and the drift is worth saying out loud.
                drifted += 1
                continue
            collected.append((pin, got.body))
        if drifted:
            print(f"  {drifted} artifact(s) have changed upstream since they were pinned — "
                  f"the vendored copies are kept, and they are what the sha256 describes")

    for want, queries, filename, title in phases:
        pins, tally = collect(want, queries, filename)
        print(f"\n{title} — from {filename}")
        print(f"  candidates on a real load path: {tally['candidates']} "
              f"in {tally['repos']} repositories")
        # Red line 2: every exclusion is named and counted, in the same output as the figure
        # it shrank. A denominator carrying a silent exclusion is the defect this prevents.
        print(f"  excluded: {tally['unfetchable']} unfetchable, "
              f"{tally['not_agent_config']} not an agent config, "
              f"{tally['no_surface'] + tally['local_only_mcp']} exercise no surface"
              f"{' (local-process-only MCP)' if want == 'mcp' else ' (both blocks empty)'}, "
              f"{tally['unlicensed']} unlicensed, {tally['non_permissive']} non-permissive")
        print(f"  kept for layer 1: {tally['kept']}")
        if tally["unlicensed"] or tally["non_permissive"]:
            dropped = tally["unlicensed"] + tally["non_permissive"]
            eligible = tally["kept"] + dropped
            print(f"  licence exclusion, both figures: {eligible} artifacts were read and do "
                  f"exercise a surface; {tally['kept']} of them "
                  f"({tally['kept'] / eligible * 100:.0f}%) carry a licence permitting "
                  f"redistribution and are vendored. The other {dropped} are equally real and "
                  f"are NOT in the denominator — a rate measured here is a rate over "
                  f"permissively licensed configs, which is a different population from "
                  f"`all configs`")
        collected.extend(pins)

    if not collected:
        print("\nnothing harvested — refusing to write an empty result over existing samples")
        return 1

    # The pins file ACCUMULATES rather than being replaced, and the reason is a bug this
    # script already shipped once: code search ranks by relevance and its results change
    # between runs, so a second run wrote a different 191 samples over the first run's 199
    # and left the difference orphaned on disk, with the pins file describing only the newer
    # set. Disk and record disagreed, which is the undeclared drift this whole project exists
    # to refuse. Merging keeps every artifact ever pinned, and reconciliation below makes the
    # directory match the record exactly.
    merged: dict[tuple[str, str], Pin] = {}
    if PINS.exists():
        for row in json.loads(PINS.read_text()).get("pins", []):
            pin = Pin(**{**row, "surfaces": tuple(row["surfaces"])})
            merged[(pin.repo, pin.path)] = pin
    before = len(merged)
    bodies: dict[tuple[str, str], str] = {}
    for pin, body in collected:
        merged[(pin.repo, pin.path)] = pin
        bodies[(pin.repo, pin.path)] = body
    print(f"\npins: {before} recorded before this run, {len(merged) - before} newly found, "
          f"{len(merged)} total")

    all_pins = sorted(merged.values(), key=lambda p: (p.repo, p.path))
    written, unchanged, promoted_skips, unavailable = 0, 0, 0, 0
    keep: set[pathlib.Path] = set()

    for pin in all_pins:
        primary = pin.surfaces[0]
        tree = OUT / primary / pin.name
        label = OUT / primary / f"{pin.name}.yaml"

        # An artifact promoted to another class by hand — a hard negative, say — must not come
        # back as a benign sample on the next harvest. The same file in two classes would let
        # a scanner be both right and wrong about it, and nothing would flag the contradiction.
        if promoted_elsewhere(pin):
            promoted_skips += 1
            continue

        # The same guard Materialize uses: a hand-pinned label carries judgements no script can
        # reproduce, and quietly flattening one would destroy the corpus's most valuable kind
        # of sample.
        if label.exists() and "type: harvested" not in label.read_text():
            print(f"  refusing to overwrite non-harvested label {label.relative_to(ROOT)}")
            keep.add(label)
            continue

        body = bodies.get((pin.repo, pin.path))
        if body is None:
            # Pinned by an earlier run and not re-found by this one. If the artifact is
            # already vendored and hashes to what the pin says, it stays — a sample does not
            # become less real because a search ranked it lower today.
            if label.exists() and pin.sha256 in label.read_text():
                unchanged += 1
                keep.add(label)
                keep.add(tree)
                continue
            unavailable += 1
            continue

        if tree.exists():
            shutil.rmtree(tree)
        dest = tree / load_path_for(pin)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body)
        label.write_text(render_label(pin, f"{pin.repo}/{pin.path}", added))
        keep.add(label)
        keep.add(tree)
        written += 1

    # Reconciliation. Anything harvested that is no longer pinned is removed, so the pins file
    # is a complete and truthful inventory of what is vendored rather than a partial one.
    removed = 0
    for surface in ("hooks", "permission", "connector"):
        d = OUT / surface
        if not d.is_dir():
            continue
        for lab in sorted(d.glob("*.yaml")):
            if lab in keep or "type: harvested" not in lab.read_text():
                continue
            tree = lab.with_suffix("")
            if tree.is_dir():
                shutil.rmtree(tree)
            lab.unlink()
            removed += 1

    PINS.parent.mkdir(parents=True, exist_ok=True)
    PINS.write_text(json.dumps(
        {"generated_by": "scripts/harvest-claude-config.py",
         "note": "One pin per harvested artifact, and the complete inventory of what this "
                 "population contributes to layer 1. There is no manifest entry for it "
                 "because it is not one repository, and a placeholder url would validate "
                 "while being false. This file accumulates: code search is not reproducible "
                 "between runs, so `--from-pins` rebuilds exactly this set and is the only "
                 "way to reproduce a published figure.",
         "pins": [p._asdict() for p in all_pins]},
        indent=1))

    by_surface: dict[str, int] = {}
    for p in all_pins:
        for s in p.surfaces:
            by_surface[s] = by_surface.get(s, 0) + 1
    print(f"\n{written} sample(s) written, {unchanged} already correct, {removed} removed "
          f"as no longer pinned")
    if promoted_skips:
        print(f"  {promoted_skips} skipped: already claimed by a malicious or hard-negative label")
    if unavailable:
        print(f"  {unavailable} pinned but not vendorable right now (not re-found and not "
              f"already on disk) — recorded in the pins file, absent from corpus/")
    print("  by surface (an artifact on two load paths is counted under both, so these do "
          "not sum):")
    for s in sorted(by_surface):
        print(f"    {s:<12} {by_surface[s]}")
    print(f"  pins recorded in {PINS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
