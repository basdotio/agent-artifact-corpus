#!/usr/bin/env python3
"""Harvest real MCP server source trees, and real skills from repositories created recently,
from public GitHub repositories — the two benign populations the corpus did not have.

WHY A SECOND HARVEST SCRIPT EXISTS.
    scripts/harvest-claude-config.py collects single JSON files. The artifacts here are source
    TREES: a server is a directory of Python modules, and a skill is a directory around a
    SKILL.md. A tree is vendored by cloning the repository at a pinned commit and copying one
    directory out of it, which is a different mechanism with different bounds, and folding it
    into the config script would have made that script's narrow, well-understood contract
    (one file, one sha256, one load path) false in the ways that matter.

TWO POPULATIONS, THREE PHASES, ONE RECORD.
    `servers`         Python MCP server source found by GitHub CODE search, any age. This is
                      the benign side of the mcp surface for source, where until now every
                      source tree was labelled malicious (cisco) and the only benign samples
                      were tool catalogues (automatelab).
    `servers-recent`  the same artifact, found by REPOSITORY search restricted to repositories
                      CREATED on or after CUTOFF. Code search ranks by relevance and so favours
                      old, starred repositories; this phase reaches the ones nobody has starred
                      yet.
    `skills-recent`   one SKILL.md tree per repository created on or after CUTOFF.

    Every pin records the repository's creation date whatever phase found it, so a consumer can
    split any of this by date. The date matters for one reason: a scanner tuned against this
    corpus between its harvests (2026-09-17..19) and now has, by construction, never seen a
    repository that did not exist then. The split is recorded here and USED somewhere else; the
    corpus does not know or care which scanner was tuned when.

WHAT "BENIGN" MEANS HERE, EXACTLY.
    `somebody published this`. Not reviewed, not audited, not found harmless — red line 1 and
    the config script's docstring apply unchanged. A server that runs shell commands or reads
    arbitrary files by design is as benign under this definition as one that returns the time,
    and a flag on it is a flag on a benign sample, which the corpus's `reviewed` block exists to
    turn into a confirmed false positive or a confirmed catch, one sample at a time.

ONE SAMPLE PER REPOSITORY.
    A monorepo of forty servers shares one author's habits forty times. The cap is one, the
    choice within a repository is the SHALLOWEST hit (ties broken by a seeded shuffle, so a
    rerun from the same search picks the same one), and the count dropped is printed.

FORKS ARE EXCLUDED, AND COUNTED.
    A fork of modelcontextprotocol/servers is the reference server again under another name.
    The denominator would hold the same bytes twice and the per-source rate would be about one
    upstream wearing many names. `isFork` from the API decides; the exclusion is printed.

THE TREE IS BOUNDED, AND EVERY OMISSION IS PRINTED.
    A sample is the directory holding the hit file (the repository root when the hit is at the
    root). Inside it, directories named .git, node_modules, .venv, venv, __pycache__, dist,
    build and the editor/cache directories are not copied; lockfiles (uv.lock, poetry.lock,
    package-lock.json, pnpm-lock.yaml, yarn.lock, Cargo.lock), files over 200 KiB and binary
    files (by extension) are not copied; symlinks are not followed. A tree still over 80 files
    or 1.5 MiB after that is NOT vendored at all, and the count is printed. These are vendoring
    bounds, not transforms: no file that IS copied is altered, and each label says how many
    files its tree left behind. Note the asymmetry with the four derived server entries in
    manifest/corpora.yaml, which vendor their trees whole, lockfiles included: those are 89
    trees from four repositories, these are hundreds from hundreds, and 300 KiB lockfiles
    would have been most of the bytes.

NO sha256 ON A TREE.
    The label schema's `sha256` names the hash of ONE file and the validator refuses it on a
    tree. The pins file carries `tree_sha256` — sha256 over the sorted list of
    `<relative path>\\0<sha256 of content>` — and `--from-pins` recomputes it after rebuilding
    the tree from the pinned commit, which is the integrity claim for a tree.

PERMISSIVE LICENCES ONLY, AND THE COST IS PRINTED.
    As the config harvest: unlicensed and non-permissive repositories are real, they are not
    vendored, and both figures are printed every run (red line 2).

THE HAZARD THIS CANNOT FIX.
    GitHub search is not a random sample of the world; code search returns at most one page
    per query ranked by relevance, repository search by whatever `best match` means that day.
    This denominator is `MCP servers and skills that GitHub search surfaces for these
    queries`, and that limitation belongs in every claim made from it. The pins file, not the
    search, is what a published figure is reproducible from.
"""

import hashlib
import json
import os
import pathlib
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, NamedTuple

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "corpus" / "benign"
PINS = ROOT / "manifest" / "pins" / "mcp-servers.json"
MARKER = "Generated by `scripts/harvest-mcp-servers.py`"

PERMISSIVE = {"MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause", "CC-BY-4.0", "CC0-1.0", "ISC"}

# Repositories created on or after this date are the `recent` population. The corpus's own
# harvests ran 2026-09-17..19; the day after the last one is the first day nothing in layer 1
# could have come from.
CUTOFF = "2026-09-20"

SEED = 20261015            # ties within a repository, and the skills-recent sample below
# The skills-recent search returns far more repositories than the other two phases (2,432 on
# 2026-10-15, 1,383 of them vendorable), and a skill found at a repository's root takes the
# bounded repository with it. Vendoring all of them would add more bytes than the rest of the
# corpus holds, for a population whose use is one held-out reading. So that phase keeps a SEEDED
# SAMPLE of this many repositories, drawn from the vendorable ones sorted by name; the names it
# did not keep are recorded in the pins file under `sampled_out`, so the frame the sample was
# drawn from is on record and both figures are printed (red line 2). The two server phases are
# not capped: they are the denominator, and smaller.
SKILLS_RECENT_CAP = 400
MAX_PER_REPO = 1
MAX_FILES = 80
MAX_BYTES = 1_500_000
MAX_FILE_BYTES = 200_000
SEARCH_PACE = 7.0          # code search allows 10 queries a minute; this stays under it
REPO_SEARCH_PACE = 2.5
CLONE_WORKERS = 4

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "env", "__pycache__", ".mypy_cache",
             ".pytest_cache", ".ruff_cache", ".tox", "dist", "build", ".idea", ".vscode",
             ".eggs", "site-packages"}
LOCKFILES = {"uv.lock", "poetry.lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
             "Cargo.lock", "Pipfile.lock", "bun.lockb"}
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz", ".tgz",
              ".tar", ".whl", ".so", ".dylib", ".dll", ".exe", ".bin", ".mp4", ".mp3", ".wav",
              ".woff", ".woff2", ".ttf", ".otf", ".sqlite", ".db", ".parquet", ".pyc", ".jar",
              ".class", ".o", ".a", ".pkl", ".npy", ".onnx", ".pt", ".safetensors"}
# The extensions a server BODY can live in, across both SDKs. Python plus the TypeScript/
# JavaScript family (authored .ts/.mts/.cts and compiled or hand-written .js/.mjs/.cjs). The
# is_server regex still decides whether a file of one of these is actually a server.
CODE_EXT = (".py", ".ts", ".tsx", ".mts", ".cts", ".js", ".mjs", ".cjs")

# A file is a server when it constructs one AND registers something on it. Importing FastMCP
# in a client or a test is not a server, and the first version of this filter — the import
# alone — kept a dozen of those. Both language families are recognised: the Python SDK
# (FastMCP / low-level Server) and the TypeScript SDK (@modelcontextprotocol/sdk's McpServer /
# Server). A TS file that only imports the SDK but registers no tool is a client, not a server,
# the same way the import-only Python filter let clients through.
SERVER_CONSTRUCT = re.compile(
    r"\bFastMCP\s*\(|\bServer\s*\(\s*[\"'\w]|mcp\.server\.lowlevel|from mcp\.server import Server"
    r"|new\s+McpServer\s*\(|new\s+Server\s*\(|@modelcontextprotocol/sdk")
SERVER_REGISTER = re.compile(
    r"@\w+(?:\.\w+)*\.tool\b|\.add_tool\s*\(|list_tools|call_tool|@\w+\.resource\b|@\w+\.prompt\b"
    r"|\.tool\s*\(|\.registerTool\s*\(|\.registerResource\s*\(|setRequestHandler\s*\(")

# Each query is paired with the GitHub `--language` it is searched under. The Python SDK idioms
# are searched as python; the TypeScript SDK idioms as typescript. repo_search already took a
# language parameter; this is the code-search half, widened so the harvest is no longer
# python-only — which is what made .ts a near-perfect predictor of benign on the mcp surface.
SERVER_CODE_QUERIES = [
    ("python", "from mcp.server.fastmcp import FastMCP"),
    ("python", "from fastmcp import FastMCP"),
    ("python", "FastMCP("),
    ("python", "@mcp.tool()"),
    ("python", "@mcp.tool("),
    ("python", "mcp.server.lowlevel"),
    ("python", "from mcp.server import Server"),
    ("python", "@server.list_tools()"),
    ("python", "@server.call_tool()"),
    ("python", "mcp.run(transport"),
    ("python", "FastMCP(name="),
    ("python", "add_tool("),
    ("python", "stdio_server()"),
    ("typescript", "@modelcontextprotocol/sdk"),
    ("typescript", "new McpServer("),
    ("typescript", "new Server("),
    ("typescript", "server.tool("),
    ("typescript", "server.registerTool("),
    ("typescript", "StdioServerTransport"),
    ("typescript", "setRequestHandler("),
]
SERVER_REPO_QUERIES = ["mcp server", "fastmcp", "model context protocol server", "mcp tools"]
SKILL_REPO_QUERIES = ["claude skills", "agent skills", "SKILL.md", "claude code skill",
                      "skills for claude", "agent skill"]
SKILL_TOPICS = ["claude-skills", "agent-skills", "claude-code-skills", "claude-skill"]

GH = shutil.which("gh")

# Repositories the search found that are NOT a sample of the world this denominator claims to
# describe, each with the reason, applied on every run and under --from-pins and --reconcile.
# The first run vendored all of them; reading the trees is what found them. Two rules decide:
#   - a security benchmark's or a red-team exercise's own fixtures are attacks by declaration
#     (the file is called maliciousadd.py), and a corpus that counts them as benign scores a
#     scanner WRONG for being right — the same line `corpus score` draws between fixture and
#     wild, drawn one step earlier;
#   - a tree holding what look like live third-party credentials is not redistributed, whatever
#     its class. The pattern `live-credential` exists to catch exactly this.
# Offensive-security TOOLING that is published as such (a pentest server, a phishing-campaign
# connector, a malware-analysis VM driver) is NOT dropped: somebody publishes and runs it, a
# flag on it is a flag on a benign sample, and the `reviewed` block is how that is settled.
DROPPED = {
    "AIS2Lab/MCPSecBench": "a security benchmark; the vendored directory ships its attack servers (maliciousadd.py)",
    "arunsanna/AgentDefense-Bench": "a copy of the MCPSecBench attack servers (maliciousadd.py) inside a defence benchmark",
    "ares-hackathon/icarus": "a red-teaming hackathon target; the tree carries malicious_tool.py by its own name",
    "zer0crypt02/Net-C2": "self-described botnet command-and-control tooling, which is the attack, not something it resembles",
    "NanGePlus/LangChain_V1_Test": "08-MCP/utils/llms.py holds three strings shaped like live third-party API keys; not redistributed",
}
DROPPED_LOWER = {k.lower() for k in DROPPED}


class Pin(NamedTuple):
    """Everything needed to say where one tree came from and that it is unchanged."""
    repo: str
    dir: str            # the vendored directory, repository-relative; "" is the root
    hit: str            # the file the search matched, repository-relative
    commit: str
    license: str
    created_at: str     # the repository's creation date, ISO
    stars: int
    phase: str          # servers | servers-recent | skills-recent
    surface: str        # mcp | skills
    files: int          # files vendored
    omitted: int        # files inside the directory left behind by the bounds
    bytes: int
    tree_sha256: str
    name: str           # the local sample directory


class SearchFailed(RuntimeError):
    """A search that errored is not a search that found nothing (see the config harvest)."""


def gh_try(*args: str) -> tuple[str, str, int]:
    if not GH:
        sys.exit("the `gh` CLI is required and is not on PATH")
    r = subprocess.run([GH, *args], capture_output=True, text=True)
    return r.stdout, r.stderr, r.returncode


def gh_json(*args: str, attempts: int = 4, pace: float = SEARCH_PACE) -> Any:
    for attempt in range(attempts):
        out, err, rc = gh_try(*args)
        if rc == 0 and out.strip():
            try:
                return json.loads(out)
            except json.JSONDecodeError as e:
                raise SearchFailed(f"{args[:3]}: unparseable response: {e}") from e
        if rc == 0:
            return []
        wait = pace * (attempt + 2)
        print(f"    {' '.join(args[:3])!r} failed ({err.strip()[:90]}); retrying in {wait:.0f}s", flush=True)
        time.sleep(wait)
    raise SearchFailed(f"{' '.join(args[:4])} failed {attempts} times — refusing to report an "
                       f"empty result as though the world had none")


def code_search(query: str, language: str) -> list[tuple[str, str]]:
    hits = gh_json("search", "code", query, "--language", language, "--limit", "100",
                   "--json", "repository,path")
    return [(h["repository"]["nameWithOwner"], h["path"]) for h in hits]


def repo_search(query: str, topic: str | None, language: str | None) -> list[dict]:
    args = ["search", "repos", "--created", f">={CUTOFF}", "--limit", "300",
            "--json", "fullName,createdAt,isFork,license,stargazersCount"]
    if query:
        args.insert(2, query)
    if topic:
        args += ["--topic", topic]
    if language:
        args += ["--language", language]
    return gh_json(*args, pace=REPO_SEARCH_PACE)


class RepoInfo(NamedTuple):
    license: str
    commit: str
    created_at: str
    stars: int
    fork: bool


def resolve_repos(repos: list[str], size: int = 60) -> dict[str, RepoInfo]:
    """Licence, head commit, creation date, stars and fork status for many repositories in one
    GraphQL request per batch, as the config harvest does."""
    out: dict[str, RepoInfo] = {}
    for start in range(0, len(repos), size):
        chunk = repos[start:start + size]
        fields = []
        for i, repo in enumerate(chunk):
            owner, _, name = repo.partition("/")
            fields.append(
                f"r{i}: repository(owner: {json.dumps(owner)}, name: {json.dumps(name)}) {{"
                f" isFork createdAt stargazerCount licenseInfo {{ spdxId }}"
                f" defaultBranchRef {{ target {{ ... on Commit {{ oid }} }} }} }}")
        raw, _, _ = gh_try("api", "graphql", "-f", "query={ " + " ".join(fields) + " }")
        data = {}
        if raw.strip():
            try:
                data = (json.loads(raw) or {}).get("data") or {}
            except json.JSONDecodeError:
                data = {}
        for i, repo in enumerate(chunk):
            node = data.get(f"r{i}")
            if not node:
                out[repo] = RepoInfo("NONE", "", "", 0, False)
                continue
            lic = ((node.get("licenseInfo") or {}).get("spdxId")) or "NONE"
            ref = node.get("defaultBranchRef") or {}
            commit = ((ref.get("target") or {}).get("oid")) or ""
            out[repo] = RepoInfo(lic, commit, node.get("createdAt") or "", node.get("stargazerCount") or 0,
                                 bool(node.get("isFork")))
        print(f"    … resolved {min(start + size, len(repos))}/{len(repos)} repositories", flush=True)
    return out


def tree_of(repo: str, commit: str) -> list[dict] | None:
    """Every blob in the repository at that commit: path, size. None when the API truncated the
    listing — a repository too large to list is too large to bound honestly."""
    out, _, rc = gh_try("api", f"repos/{repo}/git/trees/{commit}?recursive=1")
    if rc != 0 or not out.strip():
        return None
    try:
        t = json.loads(out)
    except json.JSONDecodeError:
        return None
    if t.get("truncated"):
        return None
    return [e for e in t.get("tree", []) if e.get("type") == "blob"]


def blob_texts(repo: str, commit: str, paths: list[str]) -> dict[str, str | None]:
    """The text of several blobs in one GraphQL request. None for binary or truncated."""
    if not paths:
        return {}
    owner, _, name = repo.partition("/")
    fields = []
    for i, p in enumerate(paths):
        fields.append(f"b{i}: object(expression: {json.dumps(commit + ':' + p)}) {{ ... on Blob {{ text isTruncated isBinary }} }}")
    q = f"{{ repository(owner: {json.dumps(owner)}, name: {json.dumps(name)}) {{ {' '.join(fields)} }} }}"
    raw, _, _ = gh_try("api", "graphql", "-f", "query=" + q)
    out: dict[str, str | None] = {p: None for p in paths}
    try:
        node = ((json.loads(raw) or {}).get("data") or {}).get("repository") or {}
    except json.JSONDecodeError:
        return out
    for i, p in enumerate(paths):
        b = node.get(f"b{i}") or {}
        if b.get("isTruncated") or b.get("isBinary"):
            continue
        out[p] = b.get("text")
    return out


def is_server(text: str | None) -> bool:
    return bool(text) and bool(SERVER_CONSTRUCT.search(text)) and bool(SERVER_REGISTER.search(text))


def vendorable_files(blobs: list[dict], directory: str) -> tuple[list[dict], int]:
    """The blobs inside `directory` that the bounds keep, and how many they leave behind."""
    prefix = directory + "/" if directory else ""
    keep, omitted = [], 0
    for b in blobs:
        p = b["path"]
        if prefix and not p.startswith(prefix):
            continue
        rel = p[len(prefix):]
        parts = rel.split("/")
        base = parts[-1]
        if any(d in SKIP_DIRS for d in parts[:-1]):
            omitted += 1
            continue
        if base in LOCKFILES or os.path.splitext(base)[1].lower() in BINARY_EXT \
                or (b.get("size") or 0) > MAX_FILE_BYTES or b.get("mode") == "120000":
            omitted += 1
            continue
        keep.append(b)
    return keep, omitted


def slug(s: str) -> str:
    return (re.sub(r"[^a-zA-Z0-9]+", "-", str(s)).strip("-").lower() or "unnamed")[:70]


def clone_dir(repo: str, commit: str, directory: str, dest: pathlib.Path) -> tuple[int, int, str] | None:
    """Materialise one directory of the repository at the pinned commit into dest, applying
    the bounds, and return (files, bytes, tree_sha256). None when the clone failed."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="harvest-"))
    try:
        url = f"https://github.com/{repo}.git"
        r = subprocess.run(["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout", url, str(tmp / "r")],
                           capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            return None
        g = ["git", "-C", str(tmp / "r")]
        if directory:
            subprocess.run(g + ["sparse-checkout", "set", "--no-cone", "/" + directory + "/"],
                           capture_output=True, text=True, timeout=120)
        r = subprocess.run(g + ["checkout", "--quiet", commit], capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            return None
        src = tmp / "r" / directory if directory else tmp / "r"
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        files, total = [], 0
        for dirpath, dirnames, filenames in os.walk(src, followlinks=False):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS
                                 and not os.path.islink(os.path.join(dirpath, d)))
            for fn in sorted(filenames):
                fp = pathlib.Path(dirpath) / fn
                if fp.is_symlink() or not fp.is_file():
                    continue
                if fn in LOCKFILES or fp.suffix.lower() in BINARY_EXT or fp.stat().st_size > MAX_FILE_BYTES:
                    continue
                rel = fp.relative_to(src)
                data = fp.read_bytes()
                out = dest / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(data)
                files.append((rel.as_posix(), hashlib.sha256(data).hexdigest()))
                total += len(data)
        h = hashlib.sha256()
        for rel, digest in sorted(files):
            h.update(rel.encode() + b"\0" + digest.encode() + b"\n")
        return len(files), total, h.hexdigest()
    except subprocess.TimeoutExpired:
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def tree_hash_of(dest: pathlib.Path) -> tuple[int, int, str]:
    files, total = [], 0
    for dirpath, dirnames, filenames in os.walk(dest, followlinks=False):
        dirnames.sort()
        for fn in sorted(filenames):
            fp = pathlib.Path(dirpath) / fn
            data = fp.read_bytes()
            files.append((fp.relative_to(dest).as_posix(), hashlib.sha256(data).hexdigest()))
            total += len(data)
    h = hashlib.sha256()
    for rel, digest in sorted(files):
        h.update(rel.encode() + b"\0" + digest.encode() + b"\n")
    return len(files), total, h.hexdigest()


class Candidate(NamedTuple):
    repo: str
    hit: str          # the file that qualified it
    phase: str
    surface: str


def choose_per_repo(cands: dict[str, list[str]]) -> dict[str, str]:
    """One hit per repository: the shallowest, ties broken by a seeded shuffle."""
    rng = random.Random(SEED)
    out = {}
    for repo in sorted(cands):
        paths = sorted(set(cands[repo]))
        rng.shuffle(paths)
        paths.sort(key=lambda p: p.count("/"))
        out[repo] = paths[0]
    return out


def phase_servers() -> tuple[dict[str, list[str]], dict[str, int]]:
    tally = {"hits": 0, "repos": 0}
    cands: dict[str, list[str]] = {}
    for n, (language, q) in enumerate(SERVER_CODE_QUERIES):
        if n:
            time.sleep(SEARCH_PACE)
        for repo, path in code_search(q, language):
            if path.endswith(CODE_EXT):
                cands.setdefault(repo, []).append(path)
                tally["hits"] += 1
    tally["repos"] = len(cands)
    return cands, tally


def recent_repos(queries: list[str], topics: list[str], language: str | None) -> dict[str, dict]:
    repos: dict[str, dict] = {}
    first = True
    for q in queries:
        if not first:
            time.sleep(REPO_SEARCH_PACE)
        first = False
        for r in repo_search(q, None, language):
            repos.setdefault(r["fullName"], r)
    for t in topics:
        time.sleep(REPO_SEARCH_PACE)
        for r in repo_search("", t, language):
            repos.setdefault(r["fullName"], r)
    return repos


def server_hit_in(repo: str, commit: str, blobs: list[dict]) -> str | None:
    """The shallowest server-body file in the repository, in either SDK's language, reading at
    most eight likely candidates: names with server/main/app/mcp/index in them first, then the
    rest by depth."""
    src = [b["path"] for b in blobs if b["path"].endswith(CODE_EXT)
           and not any(d in SKIP_DIRS or d in ("tests", "test") for d in b["path"].split("/")[:-1])
           and (b.get("size") or 0) <= MAX_FILE_BYTES]
    if not src:
        return None
    likely = re.compile(r"(server|main|app|mcp|index|__main__)", re.I)
    src.sort(key=lambda p: (0 if likely.search(p.rsplit("/", 1)[-1]) else 1, p.count("/"), p))
    texts = blob_texts(repo, commit, src[:8])
    for p in src[:8]:
        if is_server(texts.get(p)):
            return p
    return None


def skill_hit_in(blobs: list[dict]) -> str | None:
    rng = random.Random(SEED)
    skills = sorted(b["path"] for b in blobs if b["path"].rsplit("/", 1)[-1] == "SKILL.md"
                    and not any(d in SKIP_DIRS for d in b["path"].split("/")[:-1]))
    if not skills:
        return None
    rng.shuffle(skills)
    skills.sort(key=lambda p: p.count("/"))
    return skills[0]


def render_label(pin: Pin, added: str, single_sha: str) -> str:
    sid = "mcp" if pin.surface == "mcp" else "skill"
    kind = "server" if pin.surface == "mcp" else "skill"
    where = f"{pin.repo}/{pin.dir}" if pin.dir else pin.repo
    found = {
        "servers": "Found via GitHub code search for the shapes a Python MCP server is written in",
        "servers-recent": f"Found via GitHub repository search restricted to repositories created on or after {CUTOFF}",
        "skills-recent": f"Found via GitHub repository search restricted to repositories created on or after {CUTOFF}",
    }[pin.phase]
    what = ("the source of an MCP server somebody published" if pin.surface == "mcp"
            else "a skill somebody published, the directory around its SKILL.md")
    bounds = (f" {pin.omitted} file(s) inside that directory were not vendored (lockfiles, binaries, "
              f"files over 200 KiB, dependency and cache directories), as the script's docstring states."
              if pin.omitted else "")
    sha_line = f"  sha256: {single_sha}\n" if single_sha else "  sha256: \"\"   # a tree, not a file; the pins file carries tree_sha256\n"
    return f"""# {MARKER}. Do not hand-edit:
# a re-harvest overwrites this file. The tree below is real source from a real repository,
# vendored from the pinned commit — see that script's docstring for what `benign` is allowed
# to mean here and for the bounds a vendored tree is cut to.
id: ben-{sid}-{pin.name}
class: benign
surface: {pin.surface}
kind: {kind}
entry: .

origin:
  type: harvested
  source: "https://github.com/{pin.repo}/tree/{pin.commit}/{pin.dir}"
  license: {pin.license}
  note: >-
    {what[0].upper() + what[1:]}, vendored from {where} at the pinned commit. Benign here means
    `somebody published this`, not reviewed and not audited: no security review exists, and
    none is claimed. {found}; search indexes a subset of public repositories and ranks by
    relevance, so this sample is not drawn from a uniform population. The repository was
    created {pin.created_at[:10]}.{bounds}
  added: {added}
  # Nothing was run against this tree before it was labelled. It is benign because of what it
  # is and where it came from, not because a scanner stayed quiet on it — red line 3.
  labeled_before_run: true
{sha_line}
# `assumed`, from taxonomy/basis.yaml: the class comes from WHERE THIS WAS COLLECTED, not from
# anything anyone observed in the tree. See scripts/harvest-claude-config.py for why that is
# the honest and the permanent value for a benign sample.
basis:
  class: assumed
  assumption: >-
    Collected from a public repository by GitHub search, where the searched-for shape is
    {"an MCP server somebody published" if pin.surface == "mcp" else "a skill somebody published"}.
    Nothing in this particular tree was examined before the class was written.
"""


def promoted_elsewhere(pin: Pin) -> bool:
    needle = f"github.com/{pin.repo}/"
    for cls in ("malicious", "hard-negative"):
        d = ROOT / "corpus" / cls
        if not d.is_dir():
            continue
        for lab in d.glob("*/*.yaml"):
            if needle in lab.read_text():
                return True
    return False


def main() -> int:
    if "--check" in sys.argv:
        print("scripts/harvest-mcp-servers.py: gh =", GH or "MISSING")
        return 0 if GH else 1
    from datetime import date
    added = date.today().isoformat()
    from_pins = "--from-pins" in sys.argv
    reconcile = "--reconcile" in sys.argv
    only = [a.split("=", 1)[1] for a in sys.argv if a.startswith("--phase=")]
    phases = [] if (from_pins or reconcile) else (only or ["servers", "servers-recent", "skills-recent"])

    merged: dict[str, Pin] = {}
    dropped_now = []
    if PINS.exists():
        for row in json.loads(PINS.read_text()).get("pins", []):
            pin = Pin(**row)
            if pin.repo.lower() in DROPPED_LOWER:
                # Pinned by an earlier run, dropped since. The tree goes, the pin goes, and the
                # reason is printed, so the inventory and the disk agree and a reader can see
                # what left the denominator and why.
                dropped_now.append(pin)
                tree = OUT / pin.surface / pin.name
                if tree.is_dir():
                    shutil.rmtree(tree)
                lab = tree.with_suffix(".yaml")
                if lab.exists():
                    lab.unlink()
                continue
            merged[pin.name] = pin
    prior_sampled_out: list[str] = []
    if PINS.exists():
        prior_sampled_out = json.loads(PINS.read_text()).get("sampled_out", [])
    recent_skill_pins = sorted(n for n, p in merged.items() if p.phase == "skills-recent")
    if len(recent_skill_pins) > SKILLS_RECENT_CAP:
        # The first run vendored every vendorable repository; the cap came after reading what
        # that weighed. The same seeded draw over the same sorted frame (repository names)
        # picks the sample, and the rest leave disk and pins together.
        frame = sorted(merged[n].repo for n in recent_skill_pins)
        rng = random.Random(SEED)
        keep_repos = set(rng.sample(frame, SKILLS_RECENT_CAP))
        for n in recent_skill_pins:
            pin = merged[n]
            if pin.repo in keep_repos:
                continue
            prior_sampled_out.append(pin.repo)
            tree = OUT / pin.surface / pin.name
            if tree.is_dir():
                shutil.rmtree(tree)
            lab = tree.with_suffix(".yaml")
            if lab.exists():
                lab.unlink()
            del merged[n]
        print(f"skills-recent: {len(frame)} pinned, {SKILLS_RECENT_CAP} kept by the seeded sample (seed {SEED}), "
              f"{len(frame) - SKILLS_RECENT_CAP} removed from disk and pins and recorded under sampled_out")
    if dropped_now:
        print(f"{len(dropped_now)} pinned tree(s) dropped from layer 1 (DROPPED in this script):")
        for pin in dropped_now:
            print(f"  {pin.repo:<45} {DROPPED[next(k for k in DROPPED if k.lower() == pin.repo.lower())]}")
    before = len(merged)

    new_pins: list[Pin] = []
    sampled_out: list[str] = []
    if not from_pins and not reconcile:
        # ---- gather candidates per phase ----------------------------------------------------
        per_phase: dict[str, dict[str, str]] = {}        # phase -> repo -> hit
        info: dict[str, RepoInfo] = {}
        tallies: dict[str, dict[str, int]] = {}

        if "servers" in phases:
            cands, tally = phase_servers()
            print(f"\nservers — code search: {tally['hits']} hits in {tally['repos']} repositories", flush=True)
            chosen = choose_per_repo(cands)
            tally["over_cap"] = tally["hits"] - len(chosen)
            tally["dropped"] = sum(1 for r in chosen if r.lower() in DROPPED_LOWER)
            chosen = {r: h for r, h in chosen.items() if r.lower() not in DROPPED_LOWER}
            info.update(resolve_repos(sorted(set(chosen) - set(info))))
            # The hit must BE a server, not merely import the framework; read it.
            kept: dict[str, str] = {}
            notserver = unfetch = 0
            repos = sorted(chosen)
            for i in range(0, len(repos), 20):
                for repo in repos[i:i + 20]:
                    ri = info.get(repo)
                    if not ri or not ri.commit:
                        unfetch += 1
                        continue
                    t = blob_texts(repo, ri.commit, [chosen[repo]]).get(chosen[repo])
                    if is_server(t):
                        kept[repo] = chosen[repo]
                    else:
                        notserver += 1
                print(f"    … read {min(i + 20, len(repos))}/{len(repos)} hit files", flush=True)
            tally.update(not_a_server=notserver, unfetchable=unfetch)
            per_phase["servers"] = kept
            tallies["servers"] = tally

        for phase, queries, topics, lang in (
                ("servers-recent", SERVER_REPO_QUERIES, [], "python"),
                ("skills-recent", SKILL_REPO_QUERIES, SKILL_TOPICS, None)):
            if phase not in phases:
                continue
            repos = recent_repos(queries, topics, lang)
            # Repositories already chosen by an earlier phase stay there: one sample per
            # repository across the whole harvest, not per phase.
            taken = {r for m in per_phase.values() for r in m}
            repos = {r: v for r, v in repos.items() if r not in taken and v.get("createdAt", "") >= CUTOFF}
            tally = {"repos": len(repos), "fork": 0, "tree_unlistable": 0, "no_hit": 0, "unfetchable": 0,
                     "dropped": sum(1 for r in repos if r.lower() in DROPPED_LOWER)}
            repos = {r: v for r, v in repos.items() if r.lower() not in DROPPED_LOWER}
            info.update(resolve_repos(sorted(set(repos) - set(info))))
            kept = {}
            for n, repo in enumerate(sorted(repos), 1):
                ri = info.get(repo)
                if not ri or not ri.commit:
                    tally["unfetchable"] += 1
                    continue
                if ri.fork:
                    tally["fork"] += 1
                    continue
                if ri.license == "NONE" or ri.license not in PERMISSIVE:
                    # Decided here, before any tree is listed: the licence is known from the
                    # same response as the commit, and listing a tree we could never vendor
                    # spends API quota to learn nothing. The count is still printed below.
                    tally["non_permissive" if ri.license != "NONE" else "unlicensed"] = \
                        tally.get("non_permissive" if ri.license != "NONE" else "unlicensed", 0) + 1
                    continue
                blobs = tree_of(repo, ri.commit)
                if blobs is None:
                    tally["tree_unlistable"] += 1
                    continue
                hit = server_hit_in(repo, ri.commit, blobs) if phase == "servers-recent" else skill_hit_in(blobs)
                if not hit:
                    tally["no_hit"] += 1
                    continue
                kept[repo] = hit
                if n % 25 == 0:
                    print(f"    … {phase}: looked inside {n}/{len(repos)} repositories, {len(kept)} with a hit", flush=True)
            per_phase[phase] = kept
            tallies[phase] = tally
            print(f"\n{phase} — repository search, created >= {CUTOFF}: {len(repos)} repositories; "
                  f"{len(kept)} hold a {'server' if phase == 'servers-recent' else 'SKILL.md'}", flush=True)

        # ---- the skills-recent sample ---------------------------------------------------------
        sampled_out: list[str] = []
        if len(per_phase.get("skills-recent", {})) > SKILLS_RECENT_CAP:
            names = sorted(per_phase["skills-recent"])
            rng = random.Random(SEED)
            keep_names = set(rng.sample(names, SKILLS_RECENT_CAP))
            sampled_out = [n for n in names if n not in keep_names]
            tallies["skills-recent"]["sampled_out"] = len(sampled_out)
            per_phase["skills-recent"] = {r: h for r, h in per_phase["skills-recent"].items() if r in keep_names}
            print(f"\nskills-recent: {len(names)} vendorable repositories, {SKILLS_RECENT_CAP} kept by a seeded sample "
                  f"(seed {SEED}); the other {len(sampled_out)} are named in the pins file and not vendored")

        # ---- licence, fork, size bounds; then clone --------------------------------------------
        jobs: list[tuple[str, str, str, str, RepoInfo, int, list[dict]]] = []
        for phase, chosen in per_phase.items():
            tally = tallies[phase]
            surface = "mcp" if phase.startswith("servers") else "skills"
            for repo, hit in sorted(chosen.items()):
                ri = info[repo]
                if ri.fork:
                    tally["fork"] = tally.get("fork", 0) + 1
                    continue
                if ri.license == "NONE":
                    tally["unlicensed"] = tally.get("unlicensed", 0) + 1
                    continue
                if ri.license not in PERMISSIVE:
                    tally["non_permissive"] = tally.get("non_permissive", 0) + 1
                    continue
                blobs = tree_of(repo, ri.commit)
                if blobs is None:
                    tally["tree_unlistable"] = tally.get("tree_unlistable", 0) + 1
                    continue
                directory = hit.rsplit("/", 1)[0] if "/" in hit else ""
                keep, omitted = vendorable_files(blobs, directory)
                size = sum(b.get("size") or 0 for b in keep)
                if len(keep) > MAX_FILES or size > MAX_BYTES:
                    tally["over_size"] = tally.get("over_size", 0) + 1
                    continue
                jobs.append((phase, surface, repo, hit, ri, omitted, keep))

        print(f"\ncloning {len(jobs)} tree(s) at their pinned commits …", flush=True)
        results: list[Pin | None] = [None] * len(jobs)

        def do(i: int) -> None:
            phase, surface, repo, hit, ri, omitted, keep = jobs[i]
            directory = hit.rsplit("/", 1)[0] if "/" in hit else ""
            name = "gh-" + slug(repo + ("-" + directory.rsplit("/", 1)[-1] if directory else ""))
            dest = OUT / surface / name
            got = clone_dir(repo, ri.commit, directory, dest)
            if got is None:
                shutil.rmtree(dest, ignore_errors=True)
                return
            files, nbytes, th = got
            results[i] = Pin(repo=repo, dir=directory, hit=hit, commit=ri.commit, license=ri.license,
                             created_at=ri.created_at, stars=ri.stars, phase=phase, surface=surface,
                             files=files, omitted=omitted, bytes=nbytes, tree_sha256=th, name=name)

        with ThreadPoolExecutor(CLONE_WORKERS) as ex:
            for n, _ in enumerate(ex.map(do, range(len(jobs))), 1):
                if n % 20 == 0:
                    print(f"    … cloned {n}/{len(jobs)}", flush=True)
        for (phase, *_), pin in zip(jobs, results):
            if pin is None:
                tallies[phase]["clone_failed"] = tallies[phase].get("clone_failed", 0) + 1
            else:
                new_pins.append(pin)

        # ---- the summary, with every exclusion named (red line 2) -----------------------------
        for phase, tally in tallies.items():
            kept = sum(1 for p in new_pins if p.phase == phase)
            print(f"\n{phase}")
            for k in sorted(tally):
                print(f"  {k:<16} {tally[k]}")
            print(f"  kept for layer 1  {kept}")
            dropped = tally.get("unlicensed", 0) + tally.get("non_permissive", 0)
            if dropped:
                eligible = kept + dropped + tally.get("over_size", 0) + tally.get("clone_failed", 0)
                print(f"  licence exclusion, both figures: {eligible} repositories hold the artifact; "
                      f"{dropped} carry no licence or a non-permissive one and are NOT in the denominator — "
                      f"a rate measured here is a rate over permissively licensed repositories")

    # ---- --from-pins: rebuild exactly the recorded set --------------------------------------
    if from_pins:
        rows = list(merged.values())
        print(f"--from-pins: rebuilding the {len(rows)} recorded tree(s), no search")
        drifted = failed = 0

        def rebuild(pin: Pin) -> str:
            dest = OUT / pin.surface / pin.name
            got = clone_dir(pin.repo, pin.commit, pin.dir, dest)
            if got is None:
                return "failed"
            return "ok" if got[2] == pin.tree_sha256 else "drifted"

        with ThreadPoolExecutor(CLONE_WORKERS) as ex:
            for pin, status in zip(rows, ex.map(rebuild, rows)):
                if status == "failed":
                    failed += 1
                elif status == "drifted":
                    drifted += 1
                else:
                    new_pins.append(pin)
        if drifted or failed:
            print(f"  {drifted} tree(s) no longer hash to their pin at the pinned commit and "
                  f"{failed} could not be cloned — neither is rewritten; what is on disk for them "
                  f"is whatever was there before")

    if not new_pins and not from_pins and not reconcile:
        print("\nnothing harvested — refusing to write an empty result over existing samples")
        return 1

    for pin in new_pins:
        merged[pin.name] = pin
    all_pins = sorted(merged.values(), key=lambda p: (p.surface, p.name))
    print(f"\npins: {before} recorded before this run, {len(merged) - before} newly found, {len(merged)} total")

    written = unchanged = promoted_skips = 0
    keep_paths: set[pathlib.Path] = set()
    fresh = {p.name for p in new_pins}
    for pin in all_pins:
        tree = OUT / pin.surface / pin.name
        label = tree.with_suffix(".yaml")
        if promoted_elsewhere(pin):
            promoted_skips += 1
            continue
        if label.exists() and MARKER not in label.read_text():
            print(f"  refusing to overwrite a label this script did not write: {label.relative_to(ROOT)}")
            keep_paths.update((label, tree))
            continue
        if pin.name not in fresh:
            if tree.is_dir() and tree_hash_of(tree)[2] == pin.tree_sha256:
                unchanged += 1
                keep_paths.update((label, tree))
            continue
        single = ""
        if pin.files == 1:
            only_file = next(p for p in tree.rglob("*") if p.is_file())
            single = hashlib.sha256(only_file.read_bytes()).hexdigest()
        label.write_text(render_label(pin, added, single))
        keep_paths.update((label, tree))
        written += 1

    removed = 0
    for surface in ("mcp", "skills"):
        d = OUT / surface
        for lab in sorted(d.glob("gh-*.yaml")):
            if lab in keep_paths or MARKER not in lab.read_text():
                continue
            tree = lab.with_suffix("")
            if tree.is_dir():
                shutil.rmtree(tree)
            lab.unlink()
            removed += 1

    PINS.parent.mkdir(parents=True, exist_ok=True)
    PINS.write_text(json.dumps(
        {"generated_by": "scripts/harvest-mcp-servers.py",
         "cutoff": CUTOFF,
         "note": "One pin per harvested tree, and the complete inventory of what this harvest "
                 "contributes to layer 1. tree_sha256 is sha256 over the sorted list of "
                 "`<relative path>\\0<sha256 of content>\\n` for every file vendored; the label "
                 "cannot carry it because the schema's sha256 names one file. This file "
                 "accumulates: GitHub search is not reproducible between runs, so `--from-pins` "
                 "rebuilds exactly this set and is the only way to reproduce a published figure. "
                 "created_at is the repository's creation date; `cutoff` is the first day after "
                 "the corpus's earlier harvests, and phase says which search found each tree.",
         "dropped": {k: v for k, v in sorted(DROPPED.items())},
         "skills_recent_cap": SKILLS_RECENT_CAP,
         "sampled_out": sorted(set(prior_sampled_out + (sampled_out if not (from_pins or reconcile) else []))),
         "pins": [p._asdict() for p in all_pins]}, indent=1))

    by = {}
    for p in all_pins:
        k = (p.surface, "recent" if p.created_at[:10] >= CUTOFF else "older")
        by[k] = by.get(k, 0) + 1
    print(f"\n{written} label(s) written, {unchanged} already correct, {removed} removed as no longer pinned")
    if promoted_skips:
        print(f"  {promoted_skips} skipped: already claimed by a malicious or hard-negative label")
    print("  by surface and repository age (created on/after the cutoff = recent):")
    for k in sorted(by):
        print(f"    {k[0]:<8} {k[1]:<7} {by[k]}")
    print(f"  pins recorded in {PINS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
