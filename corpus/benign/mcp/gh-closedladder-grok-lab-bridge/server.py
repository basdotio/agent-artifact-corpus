#!/usr/bin/env python3
"""Grok Lab Bridge v2 — MCP server exposing home-lab machines as tools.

Runs on one lab box (LOCAL_MACHINE) as an unprivileged user. Streamable HTTP on
127.0.0.1:8000, bearer auth. One-way fan-out: this box SSHes out to the lab;
nothing inbound except localhost. (Formerly named grok-mcp-bridge.)

v1: exec, read_file, write_file, list_dir, gpu_status (machine fan-out over SSH)
v2: web_search, web_fetch (research); schedule_job, list_jobs, job_results (scheduling);
    memory_write/read/search/forget (shared memory, SQLite FTS5);
    submit_for_review, review_queue (verification harness)

Config (0600, never in git):
  ~/.config/grok-lab-bridge/token        bearer token (auto-generated)
  ~/.config/grok-lab-bridge/bridge_key   dedicated ed25519 SSH key (you generate it)
  ~/.config/grok-lab-bridge/known_hosts  bridge-only known hosts
  ~/.config/grok-lab-bridge/audit.log    append-only audit log (rotated by maintenance)
  ~/.config/grok-lab-bridge/memory.db    shared memory + reviews (FTS5)
  ~/.config/grok-lab-bridge/jobs.db      scheduled jobs + search cache + meta
  ~/.config/grok-lab-bridge/outbox.jsonl job completion outbox (written by job_runner)

Companion scripts (same dir):
  job_runner.py    cron every 5 min: executes due jobs in-process, heartbeat,
                   retries with backoff, dead-letters exhausted jobs
  maintenance.py   cron daily (niced): log rotation, cache/job/memory pruning,
                   stuck-job reaper, VACUUM, health checks -> maintenance-status.json
"""
import base64
import html as html_mod
import ipaddress
import json
import os
import re
import secrets
import socket
import sqlite3
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

CONFIG_DIR = Path.home() / ".config" / "grok-lab-bridge"
TOKEN_FILE = CONFIG_DIR / "token"
KEY_FILE = CONFIG_DIR / "bridge_key"
KNOWN_HOSTS = CONFIG_DIR / "known_hosts"
AUDIT_LOG = CONFIG_DIR / "audit.log"
MEMORY_DB = CONFIG_DIR / "memory.db"
JOBS_DB = CONFIG_DIR / "jobs.db"
OUTBOX = CONFIG_DIR / "outbox.jsonl"

# machine -> (ssh_user, ssh_host, os_family). LOCAL_MACHINE executes locally.
# ADAPT THIS: replace the placeholders with your own users/hosts (Tailscale
# MagicDNS names or IPs). os_family selects the command dialect per machine.
LOCAL_MACHINE = "spark-2"
MACHINES = {
    "spark-1": ("labuser", "<spark-1-host>", "linux"),
    "spark-2": ("labuser", "127.0.0.1", "linux"),  # local subprocess, no SSH
    "spark-3": ("labuser", "<spark-3-host>", "linux"),
    "air": ("macuser", "<mac-air-host>", "darwin"),
    "mbp": ("macuser", "<mac-pro-host>", "darwin"),
    "surface": ("winuser", "<surface-host>", "windows"),
}

DENY_PATTERNS = [
    r":\(\)\s*\{\s*:\|\:&\s*\}\s*;:",          # fork bomb
    r"\bmkfs(\.|\s)",                            # format filesystems
    r"\bdd\b[^\n|;]*\bof=\s*/dev/",              # dd onto block devices
    r"\b(shutdown|reboot|halt|poweroff)\b",       # power control
    r"\brm\s+[^;|&]*-[a-z]*r[a-z]*f[^;|&]*\s+/(?:\s|$|;)",  # rm -rf /
    r"\brm\s+[^;|&]*-[a-z]*r[a-z]*f[^;|&]*\s+/\*",          # rm -rf /*
    r">\s*/dev/(sd|hd|nvme|vd|mmcblk)",          # raw disk writes
    r"\bwipefs\b",
    r"\bchmod\s+-R\s+777\s+/",                   # reckless perms on /
]
DENY_RE = [re.compile(p, re.IGNORECASE) for p in DENY_PATTERNS]

MAX_OUTPUT_BYTES = 1_000_000
DEFAULT_TIMEOUT = 120
MAX_TIMEOUT = 600

# Public Host header the server accepts when fronted by a proxy such as
# Tailscale Funnel, e.g. "<your-host>.<your-tailnet>.ts.net:8443".
# Unset = localhost only.
PUBLIC_HOST = os.environ.get("BRIDGE_PUBLIC_HOST", "")

mcp = FastMCP(
    "grok-lab-bridge",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*"] +
                      ([PUBLIC_HOST] if PUBLIC_HOST else []),
        allowed_origins=[
            "http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*",
        ] + ([f"https://{PUBLIC_HOST}"] if PUBLIC_HOST else []),
    ),
)


def ensure_config():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(CONFIG_DIR, 0o700)
    if not TOKEN_FILE.exists():
        TOKEN_FILE.write_text(secrets.token_urlsafe(32) + "\n")
        os.chmod(TOKEN_FILE, 0o600)
    if KEY_FILE.exists():
        os.chmod(KEY_FILE, 0o600)


def audit(tool: str, machine: str, detail: str, exit_code: int, out_bytes: int):
    line = json.dumps({
        "ts": datetime.now(timezone.utc).isoformat(),
        "tool": tool,
        "machine": machine,
        "detail": detail[:500],
        "exit": exit_code,
        "bytes": out_bytes,
    })
    with open(AUDIT_LOG, "a") as f:
        f.write(line + "\n")


def check_denied(command: str) -> Optional[str]:
    for rx in DENY_RE:
        if rx.search(command):
            return f"blocked by safety denylist: {rx.pattern}"
    return None


def check_secret_path(path: str) -> Optional[str]:
    if CONFIG_DIR.name in path.replace("\\", "/"):
        return "refusing to touch bridge credential directory"
    return None


def run_local(command: str, timeout: int):
    try:
        p = subprocess.run(command, shell=True, capture_output=True,
                           timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        return 124, (e.stdout or b""), (e.stderr or b"") + b"\n[TIMEOUT]\n"


def run_ssh(user: str, host: str, command: str, timeout: int):
    cmd = ["ssh", "-i", str(KEY_FILE),
           "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
           "-o", "ConnectTimeout=10",
           "-o", f"UserKnownHostsFile={KNOWN_HOSTS}",
           "-o", "StrictHostKeyChecking=accept-new",
           f"{user}@{host}", command]
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout + 15)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, b"", b"\n[TIMEOUT]\n"


def run_on(machine: str, command: str, timeout: int):
    user, host, _os = MACHINES[machine]
    timeout = max(1, min(timeout, MAX_TIMEOUT))
    if machine == LOCAL_MACHINE:
        return run_local(command, timeout)
    return run_ssh(user, host, command, timeout)


def shape_result(machine: str, command: str, rc: int, out: bytes, err: bytes,
                 tool: str, detail: str):
    total = out + err
    truncated = len(total) > MAX_OUTPUT_BYTES
    if truncated:
        total = total[:MAX_OUTPUT_BYTES]
    # best-effort text decode
    text = total.decode("utf-8", errors="replace")
    audit(tool, machine, detail, rc, len(out) + len(err))
    return {"machine": machine, "exit": rc, "truncated": truncated,
            "output": text}


def os_family(machine: str) -> str:
    return MACHINES[machine][2]


# ---------------------------------------------------------------- v1: machines
@mcp.tool()
def exec(machine: str, command: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Run a shell command on a lab machine. Denylist enforced, output capped."""
    if machine not in MACHINES:
        return {"error": f"unknown machine '{machine}'", "machines": sorted(MACHINES)}
    denied = check_denied(command)
    if denied:
        audit("exec", machine, command, -1, 0)
        return {"error": denied}
    rc, out, err = run_on(machine, command, timeout)
    return shape_result(machine, command, rc, out, err, "exec", command)


@mcp.tool()
def read_file(machine: str, path: str) -> dict:
    """Read a text file from a lab machine (UTF-8, output capped at 1MB)."""
    if machine not in MACHINES:
        return {"error": f"unknown machine '{machine}'"}
    blocked = check_secret_path(path)
    if blocked:
        return {"error": blocked}
    fam = os_family(machine)
    if fam == "windows":
        cmd = f'type "{path}"'
    else:
        # shlex.quote is POSIX-only; simple double-quote wrap is enough here
        cmd = f'cat "{path}"'
    rc, out, err = run_on(machine, cmd, 60)
    return shape_result(machine, cmd, rc, out, err, "read_file", path)


@mcp.tool()
def write_file(machine: str, path: str, content: str) -> dict:
    """Write text content to a file on a lab machine (base64 transport)."""
    if machine not in MACHINES:
        return {"error": f"unknown machine '{machine}'"}
    blocked = check_secret_path(path)
    if blocked:
        return {"error": blocked}
    b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
    fam = os_family(machine)
    if fam == "windows":
        ps = ("[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName('PATHX')) | Out-Null; "
              "[IO.File]::WriteAllBytes('PATHX', [Convert]::FromBase64String('B64X'))")
        cmd = ("powershell -NoProfile -Command \"" +
               ps.replace("PATHX", path.replace("'", "''")).replace("B64X", b64) + "\"")
    elif fam == "darwin":
        cmd = (f"mkdir -p \"$(dirname \"{path}\")\" && "
               f"printf '%s' '{b64}' | base64 -D > \"{path}\"")
    else:
        cmd = (f"mkdir -p \"$(dirname \"{path}\")\" && "
               f"printf '%s' '{b64}' | base64 -d > \"{path}\"")
    rc, out, err = run_on(machine, cmd, 60)
    return shape_result(machine, f"write_file {path} ({len(content)} chars)",
                        rc, out, err, "write_file", path)


@mcp.tool()
def list_dir(machine: str, path: str) -> dict:
    """List a directory on a lab machine."""
    if machine not in MACHINES:
        return {"error": f"unknown machine '{machine}'"}
    blocked = check_secret_path(path)
    if blocked:
        return {"error": blocked}
    if os_family(machine) == "windows":
        cmd = f'dir "{path}"'
    else:
        cmd = f'ls -la -- "{path}"'
    rc, out, err = run_on(machine, cmd, 60)
    return shape_result(machine, cmd, rc, out, err, "list_dir", path)


@mcp.tool()
def gpu_status(machine: str) -> dict:
    """GPU status for a lab machine (nvidia-smi where available)."""
    if machine not in MACHINES:
        return {"error": f"unknown machine '{machine}'"}
    fam = os_family(machine)
    if fam == "windows":
        cmd = "nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv"
    elif fam == "darwin":
        cmd = "system_profiler SPDisplaysDataType | head -30"
    else:
        cmd = "nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv"
    rc, out, err = run_on(machine, cmd, 60)
    if rc != 0 and fam != "darwin":
        rc2, out2, err2 = run_on(machine, "nvidia-smi | head -25", 60)
        if rc2 == 0:
            return shape_result(machine, "nvidia-smi", rc2, out2, err2,
                                "gpu_status", "nvidia-smi")
    return shape_result(machine, cmd, rc, out, err, "gpu_status", "gpu")


# ---------------------------------------------------------------- v2: research
_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36"}


def _jobs_db():
    con = sqlite3.connect(str(JOBS_DB))
    con.execute("""CREATE TABLE IF NOT EXISTS jobs(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, run_at TEXT,
        tool TEXT, arguments TEXT, status TEXT DEFAULT 'pending', result TEXT,
        attempts INTEGER DEFAULT 0, max_attempts INTEGER DEFAULT 0,
        started_at TEXT)""")
    # migrate DBs created before attempts/max_attempts/started_at existed
    cols = [r[1] for r in con.execute("PRAGMA table_info(jobs)").fetchall()]
    for coldef in ("attempts INTEGER DEFAULT 0",
                   "max_attempts INTEGER DEFAULT 0",
                   "started_at TEXT"):
        if coldef.split()[0] not in cols:
            con.execute(f"ALTER TABLE jobs ADD COLUMN {coldef}")
    con.execute("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT)")
    con.execute("""CREATE TABLE IF NOT EXISTS search_cache(
        query TEXT PRIMARY KEY, results TEXT, fetched_at TEXT)""")
    con.commit()
    return con


class _DDGParser(HTMLParser):
    """Parse DuckDuckGo html-endpoint results (title/url/snippet triples)."""

    def __init__(self):
        super().__init__()
        self.results = []
        self._mode = None
        self._buf = []
        self._href = ""

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        cls = dict(attrs).get("class", "")
        if "result__a" in cls:
            self._mode = "title"
            self._buf = []
            self._href = dict(attrs).get("href", "")
        elif "result__snippet" in cls:
            self._mode = "snippet"
            self._buf = []

    def handle_data(self, data):
        if self._mode:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag != "a" or not self._mode:
            return
        text = re.sub(r"\s+", " ", html_mod.unescape("".join(self._buf))).strip()
        if self._mode == "title":
            url = self._href
            if "uddg=" in url:  # unwrap DDG redirect wrapper
                q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                url = urllib.parse.unquote(q.get("uddg", [url])[0])
            if url.startswith("//"):
                url = "https:" + url
            self.results.append({"title": text, "url": url, "snippet": ""})
        elif self._mode == "snippet":
            if self.results and not self.results[-1]["snippet"]:
                self.results[-1]["snippet"] = text
        self._mode = None


def _search_cache_get(query: str):
    con = _jobs_db()
    row = con.execute("SELECT results, fetched_at FROM search_cache WHERE query=?",
                      (query,)).fetchone()
    con.close()
    if row:
        try:
            age = time.time() - datetime.fromisoformat(row[1]).timestamp()
            if age < 3600:
                return json.loads(row[0])
        except Exception:
            pass
    return None


@mcp.tool()
def web_search(query: str, count: int = 5) -> dict:
    """Search the web via DuckDuckGo. Returns [{title, url, snippet}]. Cached 1h."""
    count = max(1, min(count, 20))
    query = (query or "").strip()
    if not query:
        return {"error": "empty query"}
    cached = _search_cache_get(query)
    if cached is not None:
        return {"query": query, "results": cached[:count], "cached": True}
    try:
        params = urllib.parse.urlencode({"q": query})
        req = urllib.request.Request(
            "https://html.duckduckgo.com/html/?" + params, headers=_UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read(2_000_001)
        html_text = raw.decode("utf-8", "replace")
        if "anomaly" in html_text.lower() and "result__a" not in html_text:
            # DuckDuckGo bot challenge page (transient IP rate-limit)
            audit("web_search", "-", query, -1, 0)
            return {"error": "search provider temporarily rate-limited "
                             "(bot challenge); retry in a few minutes"}
        parser = _DDGParser()
        parser.feed(html_text)
        results = parser.results[:count]
        if results:  # never cache empty/transient-block responses
            con = _jobs_db()
            con.execute(
                "INSERT OR REPLACE INTO search_cache(query, results, fetched_at) VALUES (?,?,?)",
                (query, json.dumps(results),
                 datetime.now(timezone.utc).isoformat()))
            con.commit()
            con.close()
        audit("web_search", "-", query, 0, len(json.dumps(results)))
        return {"query": query, "results": results, "cached": False}
    except Exception as e:
        audit("web_search", "-", query, -1, 0)
        return {"error": f"search failed: {str(e)[:200]}"}


def _ssrf_check(url: str) -> Optional[str]:
    """Return a block reason, or None if the URL is safe to fetch.

    NOTE: hostname is resolved before fetch, but a re-resolve at connect time
    (TOCTOU) is not pinned. Acceptable for this threat model; the guard stops
    accidental/direct SSRF, not a determined DNS-rebinding adversary.
    """
    try:
        parts = urllib.parse.urlparse(url)
    except Exception:
        return "unparseable URL"
    if parts.scheme not in ("http", "https"):
        return f"scheme '{parts.scheme}' not allowed (http/https only)"
    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        return "no hostname"
    if host == "localhost" or host.endswith(".local") or host.endswith(".internal"):
        return f"hostname '{host}' blocked"
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return f"DNS resolution failed for '{host}'"
    for _fam, _typ, _proto, _canon, sockaddr in infos:
        try:
            ip = ipaddress.ip_address(sockaddr[0])
        except ValueError:
            return f"unparseable resolved address for '{host}'"
        # is_global=False covers private, loopback, link-local, multicast,
        # reserved, unspecified, and CGNAT/shared space (e.g. Tailscale 100.x)
        if not ip.is_global:
            return f"resolved IP {ip} is in a blocked range"
    return None


class _TextExtractor(HTMLParser):
    """Strip scripts/styles/nav/etc, keep title + visible text."""

    SKIP = {"script", "style", "nav", "noscript", "header", "footer", "aside"}

    def __init__(self):
        super().__init__()
        self._skip = 0
        self._title = []
        self._in_title = False
        self._chunks = []

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t in self.SKIP:
            self._skip += 1
        elif t == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        t = tag.lower()
        if t in self.SKIP:
            self._skip = max(0, self._skip - 1)
        elif t == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self._title.append(data)
        elif not self._skip:
            self._chunks.append(data)


@mcp.tool()
def web_fetch(url: str, max_chars: int = 20000) -> dict:
    """Fetch a URL, return {title, text}. SSRF-guarded, 30s timeout, 2MB cap."""
    max_chars = max(100, min(max_chars, 200000))
    blocked = _ssrf_check(url)
    if blocked:
        audit("web_fetch", "-", url[:200], -1, 0)
        return {"error": f"blocked by SSRF guard: {blocked}"}
    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            ctype = r.headers.get("Content-Type", "")
            raw = r.read(2_000_001)
        if len(raw) > 2_000_000:
            return {"error": "response exceeds 2MB cap"}
        text_in = raw.decode("utf-8", "replace")
        if "html" in ctype.lower() or "<html" in text_in[:2000].lower():
            ex = _TextExtractor()
            ex.feed(text_in)
            title = html_mod.unescape(
                re.sub(r"\s+", " ", "".join(ex._title)).strip())
            text = html_mod.unescape(re.sub(r"[ \t\xa0]+", " ", "".join(ex._chunks)))
            text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
        else:
            title, text = "", text_in
        text = text[:max_chars]
        audit("web_fetch", "-", url[:200], 0, len(text))
        return {"url": url, "title": title, "text": text}
    except Exception as e:
        audit("web_fetch", "-", url[:200], -1, 0)
        return {"error": f"fetch failed: {str(e)[:200]}"}


# ---------------------------------------------------------------- v2: scheduling
ALLOWED_JOB_TOOLS = {"exec", "web_search", "web_fetch", "memory_write", "gpu_status"}


@mcp.tool()
def schedule_job(name: str, run_at_iso: str, tool: str, arguments: dict,
                 retries: int = 0) -> dict:
    """Schedule a tool call for a future time. run_at_iso must be future, <=30 days out.

    retries (0-5): on transient failure the job is requeued with exponential
    backoff (5min * 2^attempt). Exhausted jobs land in 'error' (dead-letter),
    visible via job_results/list_jobs."""
    if tool not in ALLOWED_JOB_TOOLS:
        return {"error": f"tool '{tool}' not allowed for scheduled jobs",
                "allowed": sorted(ALLOWED_JOB_TOOLS)}
    if not isinstance(arguments, dict):
        return {"error": "arguments must be a JSON object"}
    retries = max(0, min(int(retries or 0), 5))
    try:
        run_at = datetime.fromisoformat(run_at_iso.replace("Z", "+00:00"))
    except Exception:
        return {"error": "run_at_iso is not valid ISO-8601"}
    if run_at.tzinfo is None:
        run_at = run_at.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if run_at <= now:
        return {"error": "run_at_iso must be in the future"}
    if (run_at - now).total_seconds() > 30 * 86400:
        return {"error": "run_at_iso must be within 30 days"}
    con = _jobs_db()
    cur = con.execute(
        "INSERT INTO jobs(name, run_at, tool, arguments, max_attempts) VALUES (?,?,?,?,?)",
        (name[:200], run_at.isoformat(), tool, json.dumps(arguments), retries))
    job_id = cur.lastrowid
    con.commit()
    con.close()
    audit("schedule_job", "-", f"{name[:200]} -> {tool} @ {run_at.isoformat()}", 0, job_id)
    return {"job_id": job_id, "name": name[:200],
            "run_at": run_at.isoformat(), "tool": tool, "status": "pending",
            "retries": retries}


@mcp.tool()
def list_jobs(limit: int = 20) -> dict:
    """List pending jobs plus recently completed ones."""
    limit = max(1, min(limit, 100))
    con = _jobs_db()
    pend = con.execute(
        "SELECT id, name, run_at, tool, status FROM jobs "
        "WHERE status IN ('pending','running') ORDER BY run_at").fetchall()
    done = con.execute(
        "SELECT id, name, run_at, tool, status FROM jobs "
        "WHERE status IN ('done','error') ORDER BY run_at DESC LIMIT ?",
        (limit,)).fetchall()
    con.close()
    jobs = [{"id": r[0], "name": r[1], "run_at": r[2], "tool": r[3], "status": r[4]}
            for r in pend + done]
    return {"jobs": jobs[:limit]}


@mcp.tool()
def job_results(job_id: int) -> dict:
    """Status + result JSON of a job."""
    con = _jobs_db()
    row = con.execute(
        "SELECT id, name, run_at, tool, status, result FROM jobs WHERE id=?",
        (job_id,)).fetchone()
    con.close()
    if not row:
        return {"error": f"no job {job_id}"}
    result = None
    if row[5]:
        try:
            result = json.loads(row[5])
        except Exception:
            result = {"raw": row[5][:2000]}
    return {"id": row[0], "name": row[1], "run_at": row[2],
            "tool": row[3], "status": row[4], "result": result}


# ---------------------------------------------------------------- v2: shared memory
def _mem_db():
    con = sqlite3.connect(str(MEMORY_DB))
    con.execute("""CREATE TABLE IF NOT EXISTS memories(
        bot TEXT, namespace TEXT, key TEXT, value TEXT, tags TEXT, updated TEXT,
        PRIMARY KEY (bot, namespace, key))""")
    # migrate DBs created before the opt-in TTL column existed
    mcols = [r[1] for r in con.execute("PRAGMA table_info(memories)").fetchall()]
    if "expires_at" not in mcols:
        con.execute("ALTER TABLE memories ADD COLUMN expires_at TEXT")
    con.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
        USING fts5(bot, namespace, key, value,
                   content='memories', content_rowid='rowid')""")
    con.execute("""CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
        INSERT INTO memories_fts(rowid, bot, namespace, key, value)
        VALUES (new.rowid, new.bot, new.namespace, new.key, new.value); END""")
    con.execute("""CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
        INSERT INTO memories_fts(memories_fts, rowid, bot, namespace, key, value)
        VALUES ('delete', old.rowid, old.bot, old.namespace, old.key, old.value); END""")
    con.execute("""CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
        INSERT INTO memories_fts(memories_fts, rowid, bot, namespace, key, value)
        VALUES ('delete', old.rowid, old.bot, old.namespace, old.key, old.value);
        INSERT INTO memories_fts(rowid, bot, namespace, key, value)
        VALUES (new.rowid, new.bot, new.namespace, new.key, new.value); END""")
    con.execute("""CREATE TABLE IF NOT EXISTS reviews(
        id INTEGER PRIMARY KEY AUTOINCREMENT, bot TEXT, task TEXT,
        verdict TEXT, reasons TEXT, checks TEXT, time TEXT)""")
    con.commit()
    return con


@mcp.tool()
def memory_write(bot: str, namespace: str, key: str, value: str, tags: list = None,
                 expires_at_iso: str = None) -> dict:
    """Upsert a memory. namespace is the bot's own name or 'shared'.

    expires_at_iso (optional): ISO-8601 timestamp after which the memory is
    pruned by daily maintenance. Use for ephemeral context; omit for durable
    facts. Existing memories are never deleted except via memory_forget or
    an explicit expires_at."""
    if not all([bot, namespace, key]):
        return {"error": "bot, namespace, and key are all required"}
    value = value or ""
    if len(value) > 200000:
        return {"error": "value exceeds 200KB"}
    expires_at = None
    if expires_at_iso:
        try:
            exp = datetime.fromisoformat(expires_at_iso.replace("Z", "+00:00"))
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp <= datetime.now(timezone.utc):
                return {"error": "expires_at_iso must be in the future"}
            expires_at = exp.isoformat()
        except Exception:
            return {"error": "expires_at_iso is not valid ISO-8601"}
    tags = tags or []
    con = _mem_db()
    con.execute(
        """INSERT INTO memories(bot, namespace, key, value, tags, updated, expires_at)
           VALUES (?,?,?,?,?,?,?)
           ON CONFLICT(bot, namespace, key) DO UPDATE SET
             value=excluded.value, tags=excluded.tags, updated=excluded.updated,
             expires_at=excluded.expires_at""",
        (bot[:100], namespace[:100], key[:200], value, json.dumps(tags),
         datetime.now(timezone.utc).isoformat(), expires_at))
    con.commit()
    con.close()
    audit("memory_write", "-", f"{bot[:100]}/{namespace[:100]}/{key[:200]}", 0, len(value))
    return {"ok": True, "bot": bot[:100], "namespace": namespace[:100],
            "key": key[:200], "expires_at": expires_at}


@mcp.tool()
def memory_read(bot: str, namespace: str, key: str) -> dict:
    """Read a memory value, or null if absent."""
    con = _mem_db()
    row = con.execute(
        "SELECT value FROM memories WHERE bot=? AND namespace=? AND key=?",
        (bot, namespace, key)).fetchone()
    con.close()
    return {"value": row[0] if row else None}


@mcp.tool()
def memory_search(query: str, namespace: str = None, limit: int = 10) -> dict:
    """Full-text search over memories, FTS5-ranked."""
    limit = max(1, min(limit, 50))
    query = (query or "").strip()
    if not query:
        return {"error": "empty query"}
    # quote each term to avoid FTS syntax errors; terms are ANDed
    q = " ".join('"' + w.replace('"', '""') + '"' for w in query.split())
    con = _mem_db()
    base = ("""SELECT m.bot, m.namespace, m.key,
                      snippet(memories_fts, 3, '<<', '>>', '...', 48), m.updated
               FROM memories_fts JOIN memories m ON m.rowid = memories_fts.rowid
               WHERE memories_fts MATCH ?""")
    if namespace:
        rows = con.execute(base + " AND m.namespace = ? ORDER BY rank LIMIT ?",
                           (q, namespace, limit)).fetchall()
    else:
        rows = con.execute(base + " ORDER BY rank LIMIT ?", (q, limit)).fetchall()
    con.close()
    return {"results": [
        {"bot": r[0], "namespace": r[1], "key": r[2],
         "snippet": r[3], "updated": r[4]} for r in rows]}


@mcp.tool()
def memory_forget(bot: str, namespace: str, key: str) -> dict:
    """Delete a memory. Returns {"deleted": true/false}."""
    con = _mem_db()
    cur = con.execute(
        "DELETE FROM memories WHERE bot=? AND namespace=? AND key=?",
        (bot, namespace, key))
    con.commit()
    n = cur.rowcount
    con.close()
    audit("memory_forget", "-", f"{bot}/{namespace}/{key}", 0, n)
    return {"deleted": n > 0}


# ---------------------------------------------------------------- v2: verification harness
SECRET_PATTERNS = [
    ("api_key_pattern", r"api[_-]?\s*key\s*[:=]"),
    ("aws_key_pattern", r"aws[_-](access[_-]?key|secret[_-]?key)"),
    ("password_pattern", r"passw(or)?d\s*[:=]"),
    ("private_key_pattern", r"BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY"),
    ("bearer_token_pattern", r"bearer\s+[A-Za-z0-9\-._~+/]+=*"),
    ("generic_secret_pattern", r"\bsecret\s*[:=]\s*['\"]?[A-Za-z0-9\-._~+/]{8,}"),
]
SECRET_RE = [(name, re.compile(p, re.IGNORECASE)) for name, p in SECRET_PATTERNS]

REVIEW_HEAD_BYTES = 51200
REVIEW_MAX_BYTES = 100 * 1024 * 1024


def _sha256sum(machine: str, path: str) -> Optional[str]:
    fam = os_family(machine)
    q = path.replace("'", "''")
    if fam == "windows":
        cmd = f"powershell -NoProfile -Command \"(Get-FileHash '{q}' -Algorithm SHA256).Hash\""
    elif fam == "darwin":
        cmd = f"shasum -a 256 \"{path}\" | cut -d' ' -f1"
    else:
        cmd = f"sha256sum \"{path}\" | cut -d' ' -f1"
    rc, out, _err = run_on(machine, cmd, 60)
    if rc != 0:
        return None
    h = out.decode("utf-8", "replace").strip().split()
    h = h[0].lower() if h else ""
    return h if re.fullmatch(r"[0-9a-f]{64}", h) else None


def _file_size(machine: str, path: str) -> Optional[int]:
    fam = os_family(machine)
    q = path.replace("'", "''")
    if fam == "windows":
        cmd = f"powershell -NoProfile -Command \"(Get-Item '{q}').Length\""
    elif fam == "darwin":
        cmd = f"stat -f%z \"{path}\""
    else:
        cmd = f"stat -c%s \"{path}\""
    rc, out, _err = run_on(machine, cmd, 60)
    if rc != 0:
        return None
    try:
        return int(out.decode("utf-8", "replace").strip().split()[0])
    except Exception:
        return None


@mcp.tool()
def submit_for_review(bot: str, task: str, artifact_description: str,
                      acceptance_criteria: str, file_manifest: list = None) -> dict:
    """QA-check a bot artifact. Deterministic checks; verdict PASS/FAIL.

    file_manifest entries: {machine, path, sha256}. Checks: file exists, hash
    matches, no credential patterns (pattern names only — matched values are
    NEVER returned), total size within 1B..100MB. FAIL never blocks retry.
    """
    file_manifest = file_manifest or []
    checks = []
    reasons = []
    total_bytes = 0
    corpus = artifact_description or ""
    for entry in file_manifest:
        if not isinstance(entry, dict):
            checks.append({"name": "manifest:entry", "ok": False,
                           "detail": "manifest entry must be an object"})
            reasons.append("malformed manifest entry")
            continue
        machine, path = entry.get("machine"), entry.get("path")
        want = (entry.get("sha256") or "").lower()
        label = f"{machine}:{path}"
        if machine not in MACHINES:
            checks.append({"name": f"manifest:{label}", "ok": False,
                           "detail": "unknown machine"})
            reasons.append(f"unknown machine in manifest: {machine}")
            continue
        got = _sha256sum(machine, path)
        if got is None:
            checks.append({"name": f"exists:{label}", "ok": False,
                           "detail": "file missing or unreadable"})
            reasons.append(f"missing artifact: {label}")
            continue
        checks.append({"name": f"exists:{label}", "ok": True,
                       "detail": "file present"})
        if got == want:
            checks.append({"name": f"sha256:{label}", "ok": True,
                           "detail": "hash matches"})
        else:
            checks.append({"name": f"sha256:{label}", "ok": False,
                           "detail": "hash mismatch"})
            reasons.append(f"sha256 mismatch: {label}")
        size = _file_size(machine, path)
        if size:
            total_bytes += size
        # head for secret scan via the existing read path (first 50KB)
        head = read_file(machine, path)
        if isinstance(head, dict) and "output" in head:
            corpus += "\n" + head["output"][:REVIEW_HEAD_BYTES]
    secret_hit = False
    for name, rx in SECRET_RE:
        if rx.search(corpus):
            secret_hit = True
            checks.append({"name": f"secret-scan:{name}", "ok": False,
                           "detail": "credential pattern detected"})
            reasons.append(f"credential pattern detected: {name}")
    if not secret_hit:
        checks.append({"name": "secret-scan", "ok": True,
                       "detail": "no credential patterns"})
    if 0 < total_bytes < REVIEW_MAX_BYTES:
        checks.append({"name": "size-sanity", "ok": True,
                       "detail": f"{total_bytes} bytes"})
    else:
        checks.append({"name": "size-sanity", "ok": False,
                       "detail": f"{total_bytes} bytes"})
        reasons.append(
            f"artifact size out of bounds: {total_bytes} bytes (need 1B..100MB)")
    verdict = "PASS" if not reasons else "FAIL"
    now = datetime.now(timezone.utc).isoformat()
    con = _mem_db()
    con.execute(
        "INSERT INTO reviews(bot, task, verdict, reasons, checks, time)"
        " VALUES (?,?,?,?,?,?)",
        (bot[:100], task[:300], verdict, json.dumps(reasons),
         json.dumps(checks), now))
    con.commit()
    con.close()
    # audit carries the task name only — never artifact content
    audit("submit_for_review", "-", f"{bot[:100]}:{task[:200]} -> {verdict}",
          0 if verdict == "PASS" else 1, total_bytes)
    return {"verdict": verdict, "checks": checks, "reasons": reasons}


@mcp.tool()
def review_queue(limit: int = 20) -> dict:
    """Recent reviews for operator triage: [{id, bot, task, verdict, reasons, time}]."""
    limit = max(1, min(limit, 100))
    con = _mem_db()
    rows = con.execute(
        "SELECT id, bot, task, verdict, reasons, time FROM reviews"
        " ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    con.close()
    out = []
    for r in rows:
        try:
            reasons = json.loads(r[4])
        except Exception:
            reasons = []
        out.append({"id": r[0], "bot": r[1], "task": r[2],
                    "verdict": r[3], "reasons": reasons, "time": r[5]})
    return {"reviews": out}


@mcp.tool()
def bridge_status() -> dict:
    """One-call health snapshot: jobs, memory, reviews, cache, service, disk.

    Token-cheap observability: one call replaces polling list_jobs, job_results,
    memory_search, and review_queue separately."""
    now = datetime.now(timezone.utc)
    out = {"ts": now.isoformat()}
    try:
        jc = _jobs_db()
        out["jobs"] = {
            "pending": jc.execute(
                "SELECT COUNT(*) FROM jobs WHERE status='pending'").fetchone()[0],
            "overdue": jc.execute(
                "SELECT COUNT(*) FROM jobs WHERE status='pending' AND run_at < ?",
                (now.isoformat(),)).fetchone()[0],
            "running": jc.execute(
                "SELECT COUNT(*) FROM jobs WHERE status='running'").fetchone()[0],
            "error": jc.execute(
                "SELECT COUNT(*) FROM jobs WHERE status='error'").fetchone()[0],
        }
        row = jc.execute("SELECT v FROM meta WHERE k='last_run'").fetchone()
        out["jobs"]["runner_last_run"] = row[0] if row else None
        out["search_cache_entries"] = jc.execute(
            "SELECT COUNT(*) FROM search_cache").fetchone()[0]
        jc.close()
    except Exception as e:
        out["jobs"] = {"error": str(e)[:200]}
    try:
        mc = _mem_db()
        out["memories"] = mc.execute(
            "SELECT COUNT(*) FROM memories").fetchone()[0]
        out["memories_by_namespace"] = {
            r[0]: r[1] for r in mc.execute(
                "SELECT namespace, COUNT(*) FROM memories GROUP BY namespace")}
        out["reviews_24h"] = {
            r[0]: r[1] for r in mc.execute(
                "SELECT verdict, COUNT(*) FROM reviews WHERE time > ? GROUP BY verdict",
                ((now - timedelta(days=1)).isoformat(),))}
        mc.close()
    except Exception as e:
        out["memories"] = {"error": str(e)[:200]}
    try:
        sizes = {}
        for p in (AUDIT_LOG, MEMORY_DB, JOBS_DB, OUTBOX):
            if p.exists():
                sizes[p.name] = p.stat().st_size
        sizes["config_dir_bytes"] = sum(
            p.stat().st_size for p in CONFIG_DIR.rglob("*") if p.is_file())
        out["disk"] = sizes
    except Exception as e:
        out["disk"] = {"error": str(e)[:200]}
    try:
        r = subprocess.run(
            ["systemctl", "--user", "show", "grok-lab-bridge.service",
             "-p", "ActiveState", "-p", "ActiveEnterTimestamp", "--value"],
            capture_output=True, text=True, timeout=15)
        lines = r.stdout.strip().split("\n")
        out["service"] = {"state": lines[0] if lines else "?"}
        if len(lines) > 1 and lines[1] not in ("", "n/a"):
            out["service"]["since"] = lines[1]
    except Exception as e:
        out["service"] = {"error": str(e)[:200]}
    try:
        st = CONFIG_DIR / "maintenance-status.json"
        if st.exists():
            s = json.loads(st.read_text())
            out["maintenance"] = {"last_run": s.get("ts"),
                                  "anomalies": s.get("anomalies", [])}
        else:
            out["maintenance"] = {"last_run": None}
    except Exception as e:
        out["maintenance"] = {"error": str(e)[:200]}
    return out


class BearerAuth(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path.startswith("/mcp"):
            token = TOKEN_FILE.read_text().strip() if TOKEN_FILE.exists() else ""
            auth = request.headers.get("authorization", "")
            if not token or auth != f"Bearer {token}":
                return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


def build_app():
    ensure_config()
    app = mcp.streamable_http_app()
    app.add_middleware(BearerAuth)
    return app


if __name__ == "__main__":
    import uvicorn
    ensure_config()
    uvicorn.run(build_app(), host="127.0.0.1", port=8000, log_level="warning")
