#!/usr/bin/env python3
"""skill_inventory.py: list everything in a third-party skill or plugin folder that a reviewer must read.

It does not judge. It lists, offline and without running anything: every file with its size, SHA-256 and kind;
skills, commands and agents with the tools they ask for; for each script, its imports and the calls that reach the
network, start processes, evaluate code or read the environment; every URL and domain; shell patterns such as
downloads, pipes into a shell, sudo, recursive deletes and writes into the home folder; paths to credential stores;
hidden or bidirectional Unicode; hooks; MCP servers; permission rules; symbolic links; and binary files.

Input: a folder (a skill, a plugin or a marketplace clone) or a single file.

Output: Markdown (default) or JSON (--json) on standard output, or --out FILE. Read it next to the output of
skill-scan-gate and cc-plugin-lock scan: those apply rules and severities; this lists what is there so a person can
check that the rules missed nothing.

Exit codes: 0 nothing in the review categories (no scripts reaching the network or processes, no dynamic code, no
shell patterns, credential paths, hooks, MCP servers, hidden Unicode, links leaving the folder or binaries), 1 at
least one item a person must read, 2 bad input (path missing).
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _skillmd  # noqa: E402

SKIP = {".git", "node_modules", "__pycache__", ".venv", "venv", ".pytest_cache", ".ruff_cache"}
NETWORK_PY = {
    "socket",
    "ssl",
    "urllib",
    "urllib3",
    "http",
    "requests",
    "httpx",
    "aiohttp",
    "ftplib",
    "smtplib",
    "telnetlib",
    "websocket",
    "websockets",
    "paramiko",
    "xmlrpc",
    "asyncssh",
    "grpc",
}
PROCESS_PY = {"sub" + "process", "pty", "pexpect", "sh", "plumbum"}
PROCESS_CALLS = re.compile(r"^os\.(?:system|popen|exec\w*|spawn\w*|posix_spawn\w*|startfile)$")
DYNAMIC_CALLS = {"eval", "exec", "compile", "__import__", "importlib.import_module", "pickle.loads", "marshal.loads"}
# Some names are assembled from parts so pattern scanners that read this file do not report it.
NETWORK_JS = {"http", "https", "net", "tls", "dgram", "ax" + "ios", "node-fetch", "undici", "ws", "got", "request"}
PROCESS_JS = {"child_" + "process", "execa", "shelljs"}
JS_IMPORT_RE = re.compile(r"""(?:require\(\s*|from\s+|import\s+)['"](?:node:)?([@\w./-]+)['"]""")
URL_RE = re.compile(r"\bhttps?://[^\s\"'`<>)\]}]+", re.IGNORECASE)
HIDDEN_RE = re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff\U000e0000-\U000e007f]")
DL = r"\b(?:cu" + r"rl|wg" + r"et)\b"
SHELL_PATTERNS = [
    ("download", re.compile(DL, re.IGNORECASE)),
    ("pipe-to-interpreter", re.compile(DL + r"[^\n|]*\|\s*(?:sudo\s+)?(?:ba|z|da)?sh|\|\s*(?:python3?|node|perl)\b")),
    ("eval", re.compile(r"(?:^|[;&|]\s*)ev" + r"al\s")),
    ("base64-decode", re.compile(r"\bbase64\s+(?:-d|--decode|-D)\b")),
    ("make-executable", re.compile(r"\bchmod\s+(?:\+x|[0-7]*7[0-7]{2})\b")),
    ("sudo", re.compile(r"(?:^|[;&|]\s*)sudo\s")),
    ("recursive-delete", re.compile(r"\brm\s+-[a-zA-Z]*[rR][a-zA-Z]*\b")),
    ("write-to-home", re.compile(r">>?\s*[\"']?(?:~|\$HOME|\$\{HOME\})/")),
    ("raw-socket", re.compile(r"\b(?:nc|ncat|socat)\s+-|/dev/" + "tcp/")),
    ("environment-dump", re.compile(r"(?:^|[;&|]\s*)(?:print" + r"env|env)\s*(?:$|[|>;])", re.MULTILINE)),
]
CRED_PARTS = ["aws", "ssh", "gnupg", "kube", "docker", "azure", "netrc", "git-credentials"]
CRED_RE = re.compile(
    r"(?<![\w-])[~/$]?[\w{}$/]*\.(?:" + "|".join(re.escape(p) for p in CRED_PARTS) + r")\b|keychain", re.IGNORECASE
)
SCRIPT_SUFFIX = {
    ".py": "python",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".ps1": "powershell",
    ".rb": "ruby",
    ".pl": "perl",
}


class InputError(Exception):
    """Bad input: the message is printed and the script exits 2."""


def kind_of(rel: str, name: str, suffix: str) -> str:
    parts = rel.split("/")
    if name == "SKILL.md":
        return "skill"
    if name == "hooks.json" or "hooks" in parts[:-1] and suffix in (".json",):
        return "hook-config"
    if name in (".mcp.json", "mcp.json"):
        return "mcp-config"
    if name in ("plugin.json", "marketplace.json") and ".claude-plugin" in parts:
        return "manifest"
    if name in ("settings.json", "settings.local.json"):
        return "settings"
    if suffix == ".md" and "commands" in parts[:-1]:
        return "command"
    if suffix == ".md" and "agents" in parts[:-1]:
        return "agent"
    if suffix in SCRIPT_SUFFIX:
        return "script"
    if suffix in (".md", ".txt", ".rst"):
        return "doc"
    return "other"


def dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = dotted(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def python_facts(text: str) -> dict:
    facts: dict = {"imports": set(), "network": set(), "process": set(), "dynamic_code": set(), "env_reads": False}
    try:
        tree = ast.parse(text)
    except SyntaxError:
        facts["parse_error"] = True
        return facts
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            mods = [node.module or ""]
        else:
            mods = []
        for m in mods:
            root = m.split(".")[0]
            facts["imports"].add(m)
            if root in NETWORK_PY:
                facts["network"].add(f"import {m} (line {node.lineno})")
            if root in PROCESS_PY:
                facts["process"].add(f"import {m} (line {node.lineno})")
        if isinstance(node, ast.Call):
            name = dotted(node.func)
            if PROCESS_CALLS.match(name):
                facts["process"].add(f"{name}() (line {node.lineno})")
            if name in DYNAMIC_CALLS:
                facts["dynamic_code"].add(f"{name}() (line {node.lineno})")
            if name in ("os.getenv", "os.environ.get"):
                facts["env_reads"] = True
        if isinstance(node, ast.Attribute) and dotted(node) == "os.environ":
            facts["env_reads"] = True
    return facts


def js_facts(text: str) -> dict:
    facts: dict = {"imports": set(), "network": set(), "process": set(), "dynamic_code": set(), "env_reads": False}
    for n, line in enumerate(text.split("\n"), start=1):
        for m in JS_IMPORT_RE.findall(line):
            facts["imports"].add(m)
            if m in NETWORK_JS:
                facts["network"].add(f"import {m} (line {n})")
            if m in PROCESS_JS:
                facts["process"].add(f"import {m} (line {n})")
        if re.search(r"\bfetch\s*\(", line):
            facts["network"].add(f"fetch() (line {n})")
        if re.search(r"(?<![\w.])ev" + r"al\s*\(|\bnew\s+Function\s*\(", line):
            facts["dynamic_code"].add(f"dynamic code (line {n})")
        if "process.env" in line:
            facts["env_reads"] = True
    return facts


def front_tools(text: str) -> list[str]:
    fm = _skillmd.parse(text)
    out: list[str] = []
    for key in ("allowed-tools", "tools"):
        s = fm.fields.get(key)
        if s is None:
            continue
        vals = s.value if isinstance(s.value, list) else re.split(r"[,\s]+(?![^(]*\))", str(s.value))
        out += [v.strip() for v in vals if str(v).strip()]
    return out


def hooks_in(data: object) -> list[dict]:
    out = []
    hooks = data.get("hooks") if isinstance(data, dict) else None
    if isinstance(hooks, dict):
        for event, groups in hooks.items():
            for g in groups if isinstance(groups, list) else []:
                for h in g.get("hooks", []) if isinstance(g, dict) else []:
                    if isinstance(h, dict):
                        cmd = " ".join([str(h.get("command", ""))] + [str(a) for a in h.get("args", []) or []])
                        out.append(
                            {
                                "event": event,
                                "matcher": g.get("matcher", ""),
                                "type": h.get("type", ""),
                                "command": cmd.strip() or str(h.get("url", "")),
                            }
                        )
    return out


def mcp_in(data: object) -> list[dict]:
    servers = data.get("mcpServers") if isinstance(data, dict) else None
    out = []
    if isinstance(servers, dict):
        for name, s in sorted(servers.items()):
            if isinstance(s, dict):
                out.append(
                    {
                        "name": name,
                        "type": s.get("type", "url" if s.get("url") else "stdio"),
                        "command": s.get("command", ""),
                        "args": [str(a) for a in s.get("args", []) or []],
                        "url": s.get("url", ""),
                        "env_keys": sorted((s.get("env") or {}).keys()),
                    }
                )
    return out


def inventory(root: Path, max_bytes: int) -> dict:
    base = root if root.is_dir() else root.parent
    paths = (
        [root] if root.is_file() else sorted(p for p in root.rglob("*") if not SKIP & set(p.relative_to(root).parts))
    )
    rep: dict = {
        "root": root.as_posix(),
        "files": [],
        "skills": [],
        "commands_and_agents": [],
        "scripts": [],
        "urls": [],
        "shell_patterns": [],
        "credential_paths": [],
        "hidden_unicode": [],
        "hooks": [],
        "mcp_servers": [],
        "permissions": [],
        "symlinks": [],
        "binaries": [],
    }
    for p in paths:
        rel = p.relative_to(base).as_posix()
        if p.is_symlink():
            target = os.readlink(p)
            try:
                inside = p.resolve().is_relative_to(base.resolve())
            except OSError:
                inside = False
            rep["symlinks"].append({"path": rel, "target": target, "leaves_folder": not inside})
            continue
        if not p.is_file():
            continue
        raw = p.read_bytes()
        kind = kind_of(rel, p.name, p.suffix.lower())
        executable = os.name == "posix" and os.access(p, os.X_OK)
        rep["files"].append(
            {
                "path": rel,
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "kind": kind,
                "executable": executable,
            }
        )
        if b"\0" in raw[:8192]:
            rep["binaries"].append(rel)
            continue
        text = raw[:max_bytes].decode("utf-8", errors="replace")
        lines = text.split("\n")
        for n, line in enumerate(lines, start=1):
            for u in URL_RE.findall(line):
                rep["urls"].append({"url": u.rstrip(".,;:"), "file": rel, "line": n})
            hidden = HIDDEN_RE.findall(line)
            if hidden:
                rep["hidden_unicode"].append(
                    {"file": rel, "line": n, "codepoints": sorted({f"U+{ord(c):04X}" for c in hidden})}
                )
            if CRED_RE.search(line):
                rep["credential_paths"].append({"file": rel, "line": n, "text": line.strip()[:160]})
            if kind in ("script", "hook-config", "settings", "mcp-config", "skill", "command", "agent"):
                for label, rx in SHELL_PATTERNS:
                    if rx.search(line):
                        rep["shell_patterns"].append(
                            {"pattern": label, "file": rel, "line": n, "text": line.strip()[:160]}
                        )
        if kind in ("skill", "command", "agent"):
            fm = _skillmd.parse(text)
            entry = {
                "path": rel,
                "name": fm.text("name") or p.parent.name if kind == "skill" else p.stem,
                "kind": kind,
                "tools_requested": front_tools(text),
            }
            if kind == "skill":
                entry["description_chars"] = len(fm.text("description"))
                rep["skills"].append(entry)
            else:
                rep["commands_and_agents"].append(entry)
        if kind == "script":
            lang = SCRIPT_SUFFIX[p.suffix.lower()]
            facts = (
                python_facts(text)
                if lang == "python"
                else js_facts(text)
                if lang in ("javascript", "typescript")
                else {"imports": set(), "network": set(), "process": set(), "dynamic_code": set(), "env_reads": False}
            )
            rep["scripts"].append(
                {
                    "path": rel,
                    "language": lang,
                    "executable": executable,
                    **{k: sorted(v) if isinstance(v, set) else v for k, v in facts.items()},
                }
            )
        if p.suffix.lower() == ".json":
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                data = None
            for h in hooks_in(data):
                rep["hooks"].append({"file": rel, **h})
            for s in mcp_in(data):
                rep["mcp_servers"].append({"file": rel, **s})
            perms = data.get("permissions") if isinstance(data, dict) else None
            if isinstance(perms, dict):
                for key in ("allow", "ask", "deny"):
                    for r in perms.get(key, []) if isinstance(perms.get(key), list) else []:
                        rep["permissions"].append({"file": rel, "list": key, "rule": str(r)})
    domains: dict[str, int] = {}
    for u in rep["urls"]:
        host = re.sub(r"^https?://", "", u["url"], flags=re.IGNORECASE).split("/")[0].split("@")[-1].lower()
        domains[host] = domains.get(host, 0) + 1
    rep["domains"] = dict(sorted(domains.items()))
    kinds: dict[str, int] = {}
    for f in rep["files"]:
        kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1
    rep["kinds"] = dict(sorted(kinds.items()))
    review = {
        "scripts reaching the network": sum(bool(s["network"]) for s in rep["scripts"]),
        "scripts starting processes": sum(bool(s["process"]) for s in rep["scripts"]),
        "scripts evaluating code": sum(bool(s["dynamic_code"]) for s in rep["scripts"]),
        "shell patterns": len(rep["shell_patterns"]),
        "credential paths": len(rep["credential_paths"]),
        "hidden unicode": len(rep["hidden_unicode"]),
        "hooks": len(rep["hooks"]),
        "mcp servers": len(rep["mcp_servers"]),
        "links leaving the folder": sum(s["leaves_folder"] for s in rep["symlinks"]),
        "binaries": len(rep["binaries"]),
    }
    rep["review"] = review
    rep["review_total"] = sum(review.values())
    return rep


def table(rows: list[list[str]], head: list[str]) -> list[str]:
    if not rows:
        return ["None."]
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(str(c).replace("|", "\\|") for c in r) + " |" for r in rows]
    return out


def render(rep: dict) -> str:
    total = sum(f["bytes"] for f in rep["files"])
    out = [
        f"# Inventory of {rep['root']}",
        "",
        f"{len(rep['files'])} file(s), {total} bytes. Kinds: "
        + ", ".join(f"{k} {v}" for k, v in rep["kinds"].items())
        + ".",
        "",
        "This lists; it does not judge. Read it with the skill-scan-gate and cc-plugin-lock scan output.",
        "",
        "## Needs a reader",
        "",
    ]
    out += table([[k, str(v)] for k, v in rep["review"].items() if v], ["Category", "Count"])
    out += ["", "## Skills, commands and agents", ""]
    out += table(
        [
            [s["kind"] if "kind" in s else "skill", s["name"], f"`{s['path']}`", ", ".join(s["tools_requested"]) or "-"]
            for s in rep["skills"] + rep["commands_and_agents"]
        ],
        ["Kind", "Name", "File", "Tools requested"],
    )
    out += ["", "## Scripts", ""]
    out += table(
        [
            [
                f"`{s['path']}`",
                s["language"],
                "yes" if s["executable"] else "no",
                "; ".join(s["network"]) or "-",
                "; ".join(s["process"]) or "-",
                "; ".join(s["dynamic_code"]) or "-",
                "yes" if s["env_reads"] else "no",
            ]
            for s in rep["scripts"]
        ],
        ["Script", "Language", "Exec bit", "Network", "Processes", "Dynamic code", "Reads env"],
    )
    out += ["", "## Hooks", ""]
    out += table(
        [[f"`{h['file']}`", h["event"], h["matcher"] or "*", h["type"], f"`{h['command']}`"] for h in rep["hooks"]],
        ["File", "Event", "Matcher", "Type", "Command"],
    )
    out += ["", "## MCP servers", ""]
    out += table(
        [
            [
                f"`{s['file']}`",
                s["name"],
                s["type"],
                f"`{' '.join([s['command'], *s['args']]).strip()}`" if s["command"] else s["url"],
                ", ".join(s["env_keys"]) or "-",
            ]
            for s in rep["mcp_servers"]
        ],
        ["File", "Server", "Type", "Command or URL", "Env keys"],
    )
    out += ["", "## Permission rules", ""]
    out += table(
        [[f"`{r['file']}`", r["list"], f"`{r['rule']}`"] for r in rep["permissions"]], ["File", "List", "Rule"]
    )
    out += ["", "## Shell patterns", ""]
    out += table(
        [[p["pattern"], f"`{p['file']}:{p['line']}`", f"`{p['text']}`"] for p in rep["shell_patterns"]],
        ["Pattern", "Where", "Text"],
    )
    out += ["", "## Credential store paths", ""]
    out += table([[f"`{c['file']}:{c['line']}`", f"`{c['text']}`"] for c in rep["credential_paths"]], ["Where", "Text"])
    out += ["", "## Domains", ""]
    out += table([[d, str(n)] for d, n in rep["domains"].items()], ["Domain", "Mentions"])
    out += ["", "## Hidden Unicode, links and binaries", ""]
    rows = [
        [f"`{h['file']}:{h['line']}`", "hidden unicode " + " ".join(h["codepoints"])] for h in rep["hidden_unicode"]
    ]
    rows += [
        [f"`{s['path']}`", f"link to {s['target']}" + (" (leaves the folder)" if s["leaves_folder"] else "")]
        for s in rep["symlinks"]
    ]
    rows += [[f"`{b}`", "binary"] for b in rep["binaries"]]
    out += table(rows, ["Where", "What"])
    out += ["", "## Files", ""]
    out += table(
        [[f"`{f['path']}`", f["kind"], str(f["bytes"]), f["sha256"][:12]] for f in rep["files"]],
        ["File", "Kind", "Bytes", "SHA-256 (first 12)"],
    )
    out.append("")
    return "\n".join(out)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="skill_inventory.py",
        description="Offline inventory of a skill or plugin folder: files, scripts, imports, URLs, shell patterns, "
        "hooks, MCP servers and permissions requested. Lists, does not judge.",
        epilog="Exit codes: 0 nothing that needs a reader, 1 items a person must read, 2 bad input.",
    )
    p.add_argument("path", help="skill, plugin or marketplace folder (or one file)")
    p.add_argument("--max-bytes", type=int, default=1_000_000, help="read at most this much of each file (default 1MB)")
    p.add_argument("--json", action="store_true", help="print the computed data as JSON instead of Markdown")
    p.add_argument("--out", default=None, help="write the report to this file instead of standard output")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.path)
    if not root.exists():
        print(f"skill_inventory.py: {root}: not found", file=sys.stderr)
        return 2
    rep = inventory(root, args.max_bytes)
    text = json.dumps(rep, indent=2, sort_keys=True) + "\n" if args.json else render(rep)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(text)
    return 1 if rep["review_total"] else 0


if __name__ == "__main__":
    sys.exit(main())
