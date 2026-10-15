"""Architectural security: reachability and blast radius, not CVE matching.

Vulnerability scanning is a solved and crowded problem -- this deliberately
does not attempt it. What no scanner answers, because it needs a resolved
dependency graph, is the *structural* question: given that this module handles
credentials, who can reach it? Given that this one parses untrusted input, can
it reach a subprocess call? How much third-party surface does the auth path
drag in?

Those are graph questions, and Drydock already has the graph.

**Modules are classified by what they import, never by what they are named.**
A file called `auth.py` that imports nothing sensitive is not sensitive; a file
called `helpers.py` that imports `subprocess` and `pickle` is. Naming is a
guess and a guess has no place in a security report -- the whole value here is
that a finding can be checked. Every classification names the exact import that
produced it.

What this cannot do, stated plainly because a security tool that overclaims is
worse than none: it sees imports, not data flow. A path from an ingress module
to a subprocess module means such a path exists in the dependency graph, not
that user input actually reaches that call. It is a place to look, not a
finding of exploitability.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from ..core.models import FileId
from ..core.registry import AnalysisContext
from .graph import DependencyGraph

__all__ = ["SENSITIVITY", "Classification", "classify", "reachable_from", "reaches"]


#: Import markers that put a module in a sensitivity class, per ecosystem.
#: Matched against the *first* segment of an import specifier and against the
#: whole specifier, so both `subprocess` and `os/exec` are caught.
SENSITIVITY: dict[str, tuple[str, ...]] = {
    # Handles keys, tokens, credentials. Strong signal: these libraries have
    # essentially one purpose.
    "secrets": (
        "secrets", "cryptography", "nacl", "jwt", "bcrypt", "passlib",
        "argon2", "keyring", "ssl",
        "crypto/tls", "crypto/rand", "crypto/aes", "golang.org/x/crypto",
        "ring", "rustls", "openssl",
        "bcryptjs", "jsonwebtoken", "node:crypto",
    ),
    # Hashing, which is *often* checksums rather than cryptography. Kept as a
    # separate, weaker class because conflating the two produced obvious false
    # positives -- this project's own diagram module hashes file paths to make
    # node ids, and calling that "handles secrets" would discredit every other
    # finding in the report.
    "hashing": ("hashlib", "hmac", "crypto", "md5", "sha1"),
    # Accepts input from outside the process.
    "ingress": (
        "http.server", "socketserver", "flask", "fastapi", "django", "aiohttp",
        "starlette", "tornado", "bottle", "sanic", "socket", "wsgiref",
        "net/http", "github.com/gin-gonic/gin", "github.com/gorilla/mux",
        "axum", "actix_web", "warp", "hyper", "rocket",
        "express", "koa", "node:http", "node:net",
    ),
    # Can execute code or spawn processes.
    "execution": (
        "subprocess", "ctypes", "multiprocessing", "runpy", "importlib",
        "os/exec", "syscall", "unsafe",
        "std::process", "libc",
        "child_process", "node:child_process", "vm",
    ),
    # Turns bytes back into objects -- historically the richest RCE surface.
    "deserialization": (
        "pickle", "marshal", "shelve", "dill", "cloudpickle", "yaml", "jsonpickle",
        "encoding/gob", "gopkg.in/yaml.v2", "gopkg.in/yaml.v3",
        "serde_pickle", "bincode",
        "node-serialize",
    ),
}

#: Classes whose combination is worth reporting as a path.
DANGEROUS_PATHS: tuple[tuple[str, str, str], ...] = (
    ("ingress", "execution",
     "input from outside the process can reach code execution"),
    ("ingress", "deserialization",
     "input from outside the process can reach a deserializer"),
    ("ingress", "secrets",
     "an externally-reachable module can reach secret handling"),
)


@dataclass(frozen=True, slots=True)
class Classification:
    """Why a module was placed in a sensitivity class."""

    module: FileId
    classes: tuple[str, ...]
    evidence: tuple[tuple[str, str], ...]
    """(class, the exact import specifier that matched)."""

    def as_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "classes": list(self.classes),
            "evidence": [{"class": c, "import": i} for c, i in self.evidence],
        }


def classify(ctx: AnalysisContext, graph: DependencyGraph,
             *, include_tests: bool = False) -> dict[FileId, Classification]:
    """Classify every module by the sensitive imports it actually makes.

    Test modules are excluded by default. They are not deployed, so a test that
    imports `subprocess` is not an attack surface -- and including them filled
    the findings with `*_test.go` files, which is precisely the noise that
    teaches a reader to ignore a security report.
    """
    out: dict[FileId, Classification] = {}

    for fid, sf in graph.modules.items():
        if not include_tests and sf.role == "test":
            continue
        hits: list[tuple[str, str]] = []
        for imp in ctx.imports(sf):
            spec = (imp.raw or "").strip()
            if not spec:
                continue
            head = spec.replace("::", "/").split("/")[0].split(".")[0]
            for cls, markers in SENSITIVITY.items():
                for marker in markers:
                    if spec == marker or head == marker or spec.startswith(marker + "."):
                        hits.append((cls, spec))
                        break
        if hits:
            classes = tuple(sorted({c for c, _ in hits}))
            out[fid] = Classification(
                module=fid,
                classes=classes,
                evidence=tuple(sorted(set(hits))),
            )
    return out


def reachable_from(graph: DependencyGraph, start: Iterable[FileId]) -> set[FileId]:
    """Everything the given modules can reach, following load-time edges."""
    adj: dict[FileId, set[FileId]] = defaultdict(set)
    for e in graph.load_time_edges():
        adj[e.source].add(e.target)

    seen: set[FileId] = set()
    queue = deque(start)
    while queue:
        node = queue.popleft()
        for nxt in adj.get(node, ()):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


def reaches(graph: DependencyGraph, target: Iterable[FileId]) -> set[FileId]:
    """Everything that can reach the given modules -- the blast radius.

    If one of these modules is compromised or changed, this is the set of code
    that could be affected. It is the question "who can get to my auth code?"
    asked in the direction the graph actually answers.
    """
    radj: dict[FileId, set[FileId]] = defaultdict(set)
    for e in graph.load_time_edges():
        radj[e.target].add(e.source)

    seen: set[FileId] = set()
    queue = deque(target)
    while queue:
        node = queue.popleft()
        for prev in radj.get(node, ()):
            if prev not in seen:
                seen.add(prev)
                queue.append(prev)
    return seen


def path_between(
    graph: DependencyGraph, source: FileId, targets: set[FileId], limit: int = 6
) -> list[FileId] | None:
    """Shortest import path from `source` into `targets`, if one exists.

    Returned so a finding can show the actual chain rather than assert that one
    exists. A security claim without the path is not checkable.
    """
    adj: dict[FileId, set[FileId]] = defaultdict(set)
    for e in graph.load_time_edges():
        adj[e.source].add(e.target)

    queue: deque[list[FileId]] = deque([[source]])
    seen = {source}
    while queue:
        path = queue.popleft()
        if len(path) > limit:
            continue
        for nxt in sorted(adj.get(path[-1], ())):
            if nxt in targets:
                return path + [nxt]
            if nxt not in seen:
                seen.add(nxt)
                queue.append(path + [nxt])
    return None


def external_surface(ctx: AnalysisContext, graph: DependencyGraph,
                     modules: Iterable[FileId]) -> set[str]:
    """Third-party packages reachable from `modules`, transitively.

    The supply-chain question: how much code you did not write does this path
    depend on? Counted over the transitive closure, because a direct dependency
    list understates it badly.
    """
    closure = set(modules) | reachable_from(graph, modules)
    packages: set[str] = set()
    index = ctx.index
    for fid in closure:
        sf = graph.modules.get(fid)
        if sf is None:
            continue
        for imp in ctx.imports(sf):
            res = index.resolve(imp, from_file=fid, lang=sf.lang or "")
            if res.external and imp.raw:
                head = imp.raw.replace("::", "/").split("/")[0].split(".")[0]
                if head:
                    packages.add(head)
    return packages
