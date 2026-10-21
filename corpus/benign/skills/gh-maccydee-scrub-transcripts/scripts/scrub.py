#!/usr/bin/env python3
"""Find and redact credentials in Claude transcripts.

Scans Claude Code / Claude desktop transcript stores for secrets (API keys,
tokens, passwords typed into prompts, private keys, credentials in URLs) and
replaces them in place with [REDACTED:<kind>].

Dry run by default. Nothing is written without --apply.
The report never prints a secret: only its kind, length, a public prefix for
known token formats, and a context snippet taken from the already-redacted text.

Stdlib only. Python 3.9+.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import report  # noqa: E402

HOME = Path.home()


def _desktop_app_dir() -> Path:
    """Where the Claude desktop app keeps its data on this OS."""
    if sys.platform == "darwin":
        return HOME / "Library" / "Application Support" / "Claude"
    if sys.platform.startswith("win"):
        return Path(os.environ.get("APPDATA", HOME / "AppData" / "Roaming")) / "Claude"
    return Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "Claude"


APP_SUPPORT = _desktop_app_dir()

# (label, root, glob, format)
DEFAULT_STORES = [
    ("transcripts", HOME / ".claude" / "projects", "**/*.jsonl", "jsonl"),
    ("prompt-history", HOME / ".claude" / "history.jsonl", None, "jsonl"),
    ("cowork", APP_SUPPORT / "local-agent-mode-sessions", "**/*.jsonl", "jsonl"),
    ("desktop-sessions", APP_SUPPORT / "claude-code-sessions", "**/*.json", "json"),
]
EXTRA_STORES = [
    ("file-history", HOME / ".claude" / "file-history", "**/*", "text"),
    ("shell-snapshots", HOME / ".claude" / "shell-snapshots", "**/*", "text"),
    ("tasks", HOME / ".claude" / "tasks", "**/*.json", "json"),
    ("plans", HOME / ".claude" / "plans", "**/*.md", "text"),
]

REDACTED_PREFIX = "[REDACTED"

# --------------------------------------------------------------------------
# Detectors
# --------------------------------------------------------------------------

# Known token formats. (kind, regex, group-to-redact, public-prefix-length)
# The public prefix is the vendor marker (e.g. "ghp_"), safe to show in reports.
KNOWN = [
    ("private_key",
     r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY(?: BLOCK)?-----(?:[\s\S]*?-----END (?:[A-Z]+ )*PRIVATE KEY(?: BLOCK)?-----|[A-Za-z0-9+/=\s\\]*)",
     0, 11),
    ("anthropic_key", r"(?<![A-Za-z0-9_-])sk-ant-[A-Za-z0-9_-]{20,}", 0, 7),
    ("openai_key", r"(?<![A-Za-z0-9_-])sk-(?:proj-|svcacct-|admin-)?[A-Za-z0-9_-]{32,}", 0, 3),
    ("github_token", r"(?<![A-Za-z0-9_])(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,})", 0, 4),
    ("gitlab_token", r"(?<![A-Za-z0-9_])glpat-[A-Za-z0-9_-]{20,}", 0, 6),
    ("aws_access_key_id", r"(?<![A-Z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])", 0, 4),
    ("google_api_key", r"(?<![A-Za-z0-9_-])AIza[0-9A-Za-z_-]{35}", 0, 4),
    ("google_oauth_token", r"(?<![A-Za-z0-9_-])ya29\.[0-9A-Za-z_-]{20,}", 0, 5),
    ("google_client_secret", r"(?<![A-Za-z0-9_-])GOCSPX-[A-Za-z0-9_-]{20,}", 0, 7),
    ("slack_token", r"(?<![A-Za-z0-9_-])xox[abposre]-[A-Za-z0-9-]{10,}", 0, 5),
    ("slack_webhook", r"https://hooks\.slack\.com/services/T[A-Za-z0-9]+/B[A-Za-z0-9]+/[A-Za-z0-9]+", 0, 0),
    ("discord_webhook", r"https://(?:ptb\.|canary\.)?discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_-]{30,}", 0, 0),
    ("stripe_key", r"(?<![A-Za-z0-9_])(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}", 0, 8),
    ("stripe_webhook_secret", r"(?<![A-Za-z0-9_])whsec_[A-Za-z0-9]{24,}", 0, 6),
    ("telegram_bot_token", r"(?<![0-9A-Za-z])\d{8,10}:AA[A-Za-z0-9_-]{33}(?![A-Za-z0-9_-])", 0, 0),
    ("huggingface_token", r"(?<![A-Za-z0-9_])hf_[A-Za-z0-9]{30,}", 0, 3),
    ("npm_token", r"(?<![A-Za-z0-9_])npm_[A-Za-z0-9]{36}", 0, 4),
    ("pypi_token", r"(?<![A-Za-z0-9_])pypi-[A-Za-z0-9_-]{50,}", 0, 5),
    ("sendgrid_key", r"(?<![A-Za-z0-9_])SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}", 0, 3),
    ("twilio_key", r"(?<![A-Za-z0-9])SK[0-9a-f]{32}(?![0-9a-fA-F])", 0, 2),
    ("digitalocean_token", r"(?<![A-Za-z0-9_])do[por]_v1_[a-f0-9]{64}", 0, 6),
    ("mailgun_key", r"(?<![A-Za-z0-9_-])key-[0-9a-f]{32}(?![0-9a-f])", 0, 4),
    ("jwt", r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", 0, 3),
    # scheme://user:PASSWORD@host  -> redact only the password
    ("url_password", r"\b[a-zA-Z][a-zA-Z0-9+.-]*://[^\s:/@'\"<>]{1,64}:([^\s@/'\"<>]{3,128})@[A-Za-z0-9.-]", 1, 0),
    # Authorization: Bearer X / Basic X / token X
    ("auth_header", r"(?i)\b(?:proxy-)?authorization\\?[\"']?\s*[:=]\s*\\?[\"']?(?:bearer|basic|token|bot)\s+([A-Za-z0-9._~+/=-]{12,})", 1, 0),
    ("bearer_token", r"(?i)\bbearer\s+([A-Za-z0-9._~+/-]{24,}=*)", 1, 0),
]
KNOWN_RE = [(k, re.compile(p), g, pre) for k, p, g, pre in KNOWN]


def _known_ok(kind: str, value: str) -> bool:
    """Reject known-format matches that are obviously not real."""
    if value.startswith(REDACTED_PREFIX):
        return False
    if kind in ("openai_key",):
        body = value.split("-", 1)[1]
        # real keys mix letters and digits; "sk-some-long-css-class-name" does not
        if not (re.search(r"\d", body) and re.search(r"[A-Za-z]", body)):
            return False
        if body.count("-") > 6:
            return False
    if kind in ("url_password", "auth_header", "bearer_token"):
        if _is_placeholder(value):
            return False
        if kind == "bearer_token" and not re.search(r"\d", value):
            return False
    if kind == "jwt":
        return True
    # Masked or example values: long runs of x / * / 0
    if re.search(r"(?i)(x{6,}|\*{4,}|0{12,}|example|placeholder|your[_-]?)", value):
        return False
    return True


# Contextual: <secret-ish key> <separator> <value>
PASSWORD_WORDS = {"password", "passwd", "pwd", "pw", "passphrase", "passcode", "pass"}
KEY_WORDS = PASSWORD_WORDS | {"secret", "token", "apikey", "credential", "credentials"}
KEY_QUALIFIED = {  # "key"/"auth" only count after one of these
    "api", "access", "private", "secret", "signing", "encryption", "master",
    "license", "client", "service", "app", "deploy", "ssh", "admin", "auth",
    "bot", "session", "refresh", "bearer", "webhook", "consumer", "subscription",
}
PASS_QUALIFIED = {  # bare "pass" is ffmpeg pass1, PASS: test, --pass-bg; only count "db_pass" etc.
    "db", "ftp", "sftp", "smtp", "imap", "mail", "email", "sql", "mysql", "postgres", "pg",
    "redis", "user", "admin", "root", "sa", "login", "wifi", "vnc", "rdp", "ssh", "app", "word",
}
PAT_QUALIFIED = {"github", "gh", "gitlab", "personal", "azure", "ado", "access"}
KEY_EXCLUDE = {
    "max", "min", "count", "counts", "limit", "limits", "type", "types", "name",
    "names", "url", "uri", "urls", "path", "paths", "file", "files", "dir", "length",
    "len", "usage", "input", "output", "prompt", "cache", "budget", "policy",
    "reset", "field", "fields", "label", "placeholder", "hint", "env", "var", "required",
    "expires", "expiry", "expiration", "ttl", "endpoint", "header", "prefix",
    "format", "mode", "strategy", "provider", "manager", "store", "scope",
    "scopes", "estimate", "total", "id", "ids", "page", "cursor", "next",
    "continuation", "sync", "hash", "hashed", "digest", "salt", "rotation",
    "location", "source", "ref", "arn", "version", "kind", "status", "error",
    "errors", "valid", "validation", "tokens", "size", "regex", "pattern",
    "last", "used", "created", "updated", "at", "time", "timestamp", "strength",
    "confirm", "confirmation", "forgot", "change", "changed", "form",
    "button", "icon", "class", "style", "test", "tests", "mock", "fake", "dummy",
    "example", "sample", "masked", "redacted", "hidden", "show", "visible",
    "toggle", "enabled", "disabled", "is", "has", "should", "can", "no", "missing",
    "optional", "default", "fixture", "template", "schema", "description", "doc",
    "docs", "help", "note", "notes", "tokenizer", "tokenize", "tokenized",
    "vault", "keychain", "helper", "scanner", "scan", "detector",
    "detect", "patterns", "rule", "rules", "position", "offset",
    "index", "start", "end", "stream", "streaming", "ok", "bool", "flag",
    "public", "publishable", "mark", "bg", "fg", "color", "colour", "soft", "border",
    "overlay", "width", "height", "channels", "with", "without", "if", "not",
}
PLACEHOLDER_RE = re.compile(
    r"""(?ix)^(?:
        x{3,}.*|.*\*{3,}.*|\.{2,}.*|…|-+|_+|
        <[^>]*>|\{[^}]*\}|\[[^\]]*\]|\$\{?.*|%[^%]*%|\$\(.*|`.*|
        \#[0-9a-f]{3,8}|(?:var|rgb|rgba|hsl|calc)\(.*|
        (?:your|my|the|some|a|an|enter|insert|replace|put)[_\s-].*|
        .*(?:example|placeholder|changeme|change[_-]me|dummy|sample|fake|redacted|here|todo|tbd|fixme|x{4,}).*|
        null|none|nil|undefined|true|false|yes|no|on|off|string|str|bool|boolean|int|integer|number|float|object|dict|list|array|any|
        bearer|basic|token|tokens|secret|secrets|password|passwords|passwd|pass|pw|pwd|apikey|api[_-]?key|key|required|optional|
        hidden|masked|unset|empty|missing|invalid|valid|expired|correct|incorrect|wrong|right|same|different|set|not|also|
        include|same-origin|omit|
        process\.env.*|os\.environ.*|os\.getenv.*|getenv.*|environ.*|env\..*|config\..*|settings\..*|self\..*|this\..*|
        req\..*|request\..*|args\..*|kwargs.*|options\..*|opts\..*|params\..*|props\..*|ctx\..*|context\..*|secrets\..*|vars\..*|
        https?://.*|file://.*|/.*|~/.*|\./.*|\.\./.*|[A-Za-z]:\\.*
    )$""")

# Candidate keys are found by keyword first, then KEY_RE is matched anchored at
# the start of the word containing it. Scanning every word start is ~10x slower.
KEYWORD_RE = re.compile(r"(?i)pass|pwd|pw\b|secret|token|key|credential|auth|pat\b")
KEY_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-")
KEY_RE = re.compile(
    r"""(?x)
    (?P<flag>--?)?
    \\?["']?(?P<key>[A-Za-z_][A-Za-z0-9_.-]{0,60})\\?["']?
    (?P<sep>
        [ \t]*(?::=|=|:)[ \t]*                     # key = v, key: v, "key": "v"
      | [ \t]+(?:is|was|=)[ \t]+(?::[ \t]*)?        # password is v
      | (?<=[A-Za-z0-9_])\ (?=[^\s=:])              # --password v (flag form only, checked below)
    )
    (?:
        \\?"(?P<dq>[^"\\\n]{3,200})\\?"
      | \\?'(?P<sq>[^'\\\n]{3,200})\\?'
      | (?P<bare>[^\s"'`,;<>(){}\[\]]{3,200})
    )
    """)

CAMEL_SPLIT = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")


def _key_words(key: str) -> list[str]:
    parts = re.split(r"[_.\-]+", key)
    words: list[str] = []
    for p in parts:
        words.extend(w.lower() for w in CAMEL_SPLIT.findall(p))
    return words


def _key_is_secret(key: str) -> bool:
    words = _key_words(key)
    if not words or len(words) > 6:
        return False
    if any(w in KEY_EXCLUDE for w in words):
        return False
    for i, w in enumerate(words):
        prev = words[i - 1] if i else ""
        nxt = words[i + 1] if i + 1 < len(words) else ""
        if w == "pass":
            if prev in PASS_QUALIFIED or nxt in PASS_QUALIFIED:
                return True
            continue
        if w in KEY_WORDS:
            return True
        if w in ("key", "auth") and prev in KEY_QUALIFIED:
            return True
        if w == "pat" and prev in PAT_QUALIFIED:
            return True
    return False


def _is_placeholder(v: str) -> bool:
    return bool(PLACEHOLDER_RE.match(v.strip()))


def _value_ok(key: str, value: str, quoted: bool, flag: bool, sep: str) -> bool:
    v = value.strip()
    if len(v) < 4 or v.startswith(REDACTED_PREFIX) or "REDACTED" in v:
        return False
    if _is_placeholder(v):
        return False
    passwordish = any(w in PASSWORD_WORDS for w in _key_words(key))
    if v.isdigit():
        return passwordish and len(v) >= 6 and not flag
    if re.fullmatch(r"[\d.,:/\s%+-]+", v):  # numbers, dates, ratios
        return False
    if not quoted:
        if len(v) < 6:
            return False
        if "(" in v or ")" in v:
            return False
        # a bare identifier with no digit is almost always code (password = userInput)
        if re.fullmatch(r"[A-Za-z_][A-Za-z_.]*", v):
            return False
    else:
        # quoted prose, not a secret: "Enter your password"
        if " " in v and re.fullmatch(r"[A-Za-z ,.'!?-]+", v):
            return False
    if sep.strip().startswith(("is", "was")):
        # natural language: require something password-like (digit or symbol or mixed case)
        if not re.search(r"[\d!@#$%^&*+=?~]", v) and not (re.search(r"[a-z]", v) and re.search(r"[A-Z]", v)):
            return False
    return True


def _key_starts(text: str):
    """Start offsets of words that contain a secret keyword."""
    seen = set()
    for m in KEYWORD_RE.finditer(text):
        i = m.start()
        while i > 0 and text[i - 1] in KEY_CHARS and m.start() - i < 60:
            # stop at an escaped control char: "\r\nPasscode" is key "Passcode", not "nPasscode"
            if text[i - 1] in "nrt" and i >= 2 and text[i - 2] == "\\":
                break
            i -= 1
        j = i
        while j < m.start() and text[j] in "-.":
            j += 1
        start = i if text[i:j] in ("-", "--") else j
        if start == j and j > 0 and text[j - 1] in "\"'":
            start = j - 1
            if start > 0 and text[start - 1] == "\\":
                start -= 1
        if start not in seen:
            seen.add(start)
            yield start


def contextual_spans(text: str) -> list[tuple[int, int, str, str]]:
    out = []
    for start in _key_starts(text):
        m = KEY_RE.match(text, start)
        if not m:
            continue
        key = m.group("key")
        sep = m.group("sep")
        flag = bool(m.group("flag"))
        if sep == " " and not flag:
            continue  # "key value" with a bare space only counts for --flags
        if not _key_is_secret(key):
            continue
        in_url = text[max(0, start - 5):start].endswith(("?", "&", ";", "&amp;"))
        for g, quoted in (("dq", True), ("sq", True), ("bare", False)):
            val = m.group(g)
            if val is None:
                continue
            if not quoted:
                val = val.rstrip(".!?:")
                if in_url:
                    val = re.split(r"[&#\"\\]", val, maxsplit=1)[0]
            if _value_ok(key, val, quoted, flag, sep):
                vs = m.start(g)
                if in_url:
                    kind = "url_token"
                elif any(w in PASSWORD_WORDS for w in _key_words(key)):
                    kind = "password"
                else:
                    kind = "secret_assignment"
                out.append((vs, vs + len(val), kind, key))
            break
    return out


def _entropy(s: str) -> float:
    c = Counter(s)
    n = len(s)
    return -sum(v / n * math.log2(v / n) for v in c.values())


LOOSE_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_/.+-])[A-Za-z0-9_+/=!@#$%^&*-]{16,120}(?![A-Za-z0-9_/.+-])")


def entropy_spans(text: str) -> list[tuple[int, int, str, str]]:
    """Aggressive mode: bare high-entropy tokens in text a human typed."""
    out = []
    for m in LOOSE_TOKEN_RE.finditer(text):
        v = m.group(0)
        if re.fullmatch(r"[0-9a-fA-F-]+", v):  # hex hashes, uuids, git shas
            continue
        if not (re.search(r"[a-z]", v) and re.search(r"[A-Z]", v) and re.search(r"\d", v)):
            continue
        if re.search(r"[a-z]{2,}[A-Z][a-z]{2,}[A-Z]", v) and not re.search(r"\d{2,}", v):
            continue  # camelCaseIdentifier
        if _entropy(v) < 3.8:
            continue
        out.append((m.start(), m.end(), "high_entropy", ""))
    return out


@dataclass
class Detector:
    literals: list[str] = field(default_factory=list)
    aggressive: bool = False
    kinds: frozenset | None = None

    def spans(self, text: str, human: bool, all_kinds: bool = False) -> list[tuple[int, int, str, str]]:
        if not _prefilter(text, self, entropy_ok=human):
            return []
        found: list[tuple[int, int, str, str]] = []
        for kind, rx, grp, _pre in KNOWN_RE:
            for m in rx.finditer(text):
                val = m.group(grp)
                if val and _known_ok(kind, val):
                    found.append((m.start(grp), m.end(grp), kind, ""))
        found.extend(contextual_spans(text))
        for lit in self.literals:
            i = text.find(lit)
            while i != -1:
                found.append((i, i + len(lit), "literal", ""))
                i = text.find(lit, i + len(lit))
        if self.aggressive and human:
            found.extend(entropy_spans(text))
        if self.kinds and not all_kinds:
            found = [f for f in found if f[2] in self.kinds]
        return merge_spans(found)


def merge_spans(spans):
    spans = sorted(spans, key=lambda s: (s[0], -(s[1] - s[0])))
    merged: list[list] = []
    for s in spans:
        if merged and s[0] < merged[-1][1]:
            if s[1] > merged[-1][1]:
                merged[-1][1] = s[1]
            continue
        merged.append(list(s))
    return [tuple(m) for m in merged]


def apply_spans(text: str, spans) -> str:
    for start, end, kind, _key in reversed(spans):
        text = text[:start] + f"[REDACTED:{kind}]" + text[end:]
    return text


# --------------------------------------------------------------------------
# Walking transcript records
# --------------------------------------------------------------------------

SKIP_KEYS = {
    "signature", "uuid", "parentUuid", "sessionId", "requestId", "id", "tool_use_id",
    "promptId", "messageId", "leafUuid", "sourceToolAssistantUUID", "timestamp",
}


@dataclass
class Finding:
    file: str
    line: int
    role: str
    kind: str
    length: int
    prefix: str
    key: str
    snippet: str
    store: str = ""


def _prefix_for(kind: str, value: str) -> str:
    for k, _rx, _g, pre in KNOWN_RE:
        if k == kind:
            return value[:pre]
    return ""


def _snippet(redacted: str, spans_after: list[int]) -> str:
    if not spans_after:
        return ""
    pos = spans_after[0]
    a, b = max(0, pos - 50), min(len(redacted), pos + 70)
    s = redacted[a:b].replace("\n", "⏎")
    return ("…" if a else "") + s + ("…" if b < len(redacted) else "")


def redact_string(s: str, det: Detector, human: bool, role: str, file: str, line: int, findings: list):
    spans = det.spans(s, human)
    if not spans:
        return s
    new = apply_spans(s, spans)
    # Snippets come from a copy with EVERY detected secret redacted, not just the
    # kinds being written: with --kinds, a different secret on the same line must
    # still never reach the report.
    full = det.spans(s, human, all_kinds=True) if det.kinds else spans
    shown = apply_spans(s, full)
    marker_pos, shift = [], 0
    for start, end, kind, _k in full:
        marker_pos.append((start, end, start + shift))
        shift += len(f"[REDACTED:{kind}]") - (end - start)
    for start, end, kind, key in spans:
        pos = next((p for a, b, p in marker_pos if a <= start < b), 0)
        findings.append(Finding(file, line, role, kind, end - start,
                                _prefix_for(kind, s[start:end]), key, _snippet(shown, [pos])))
    return new


def _role_of(record: dict) -> str:
    t = record.get("type")
    if "display" in record and "timestamp" in record:
        return "user"  # prompt history
    if t in ("user", "assistant"):
        return t
    if isinstance(record.get("message"), dict):
        return record["message"].get("role", "meta")
    return "meta"


def walk(obj, det: Detector, role: str, file: str, line: int, findings: list, in_tool_result=False, parent=None):
    """Return a redacted copy of obj (or obj itself if unchanged)."""
    if isinstance(obj, str):
        r = "tool_result" if in_tool_result else role
        human = r == "user"
        return redact_string(obj, det, human, r, file, line, findings)
    if isinstance(obj, list):
        changed = False
        out = []
        for item in obj:
            n = walk(item, det, role, file, line, findings, in_tool_result, parent)
            changed |= n is not item
            out.append(n)
        return out if changed else obj
    if isinstance(obj, dict):
        typ = obj.get("type")
        tr = in_tool_result or typ in ("tool_result", "tool_use_result") or "toolUseResult" in (parent or ())
        changed = False
        out = {}
        for k, v in obj.items():
            if k in SKIP_KEYS or (k == "data" and typ == "base64"):
                out[k] = v
                continue
            if isinstance(v, str) and v.startswith("data:") and ";base64," in v[:80]:
                out[k] = v
                continue
            child_tr = tr or k in ("toolUseResult", "tool_use_result")
            # tool_use inputs are what the model sent to a tool: still assistant-authored
            n = walk(v, det, role, file, line, findings, child_tr, (k,))
            changed |= n is not v
            out[k] = n
        return out if changed else obj
    return obj


# Fast prefilter on the raw line: if none of these appear, the line cannot hold a finding.
PREFILTER = re.compile(
    r"(?i)PRIVATE KEY|sk-|gh[pousr]_|github_pat_|glpat-|AKIA|ASIA|AIza|ya29\.|GOCSPX-|xox[abposre]-|hooks\.slack|"
    r"discord(?:app)?\.com/api/webhooks|_live_|_test_|whsec_|:AA|hf_|npm_|pypi-|SG\.|SK[0-9a-f]{32}|do[por]_v1_|key-[0-9a-f]|eyJ|"
    r"://[^\s:/@\"]+:[^\s@/\"]+@|bearer|authorization|pass|\bpw\b|pwd|secret|token(?!s\b)|key|credential|auth|pat\b")


def _prefilter(line: str, det: Detector, entropy_ok: bool = True) -> bool:
    if PREFILTER.search(line):
        return True
    if any(lit in line for lit in det.literals):
        return True
    return det.aggressive and entropy_ok  # entropy mode cannot be prefiltered cheaply


# --------------------------------------------------------------------------
# File processing
# --------------------------------------------------------------------------

def _dump_json_line(obj) -> str:
    try:
        s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
        s.encode("utf-8")
        return s
    except UnicodeEncodeError:  # lone surrogates survive only as \u escapes
        return json.dumps(obj, ensure_ascii=True, separators=(",", ":"))


def _atomic_write(path: Path, data: str, st: os.stat_result):
    tmp = path.with_name(f".{path.name}.scrub-tmp")
    with open(tmp, "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(tmp, st.st_mode & 0o7777)
    # abort if the file changed while we were reading it (live session appending)
    now = path.stat()
    if now.st_mtime_ns != st.st_mtime_ns or now.st_size != st.st_size:
        tmp.unlink()
        raise RuntimeError("file changed during scrub, skipped")
    os.replace(tmp, path)
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns))  # keep session ordering intact


def process_file(args) -> dict:
    path_s, fmt, store, literals, aggressive, apply, kinds = args
    path = Path(path_s)
    det = Detector(literals, aggressive, kinds)
    findings: list[Finding] = []
    try:
        st = path.stat()
        raw = path.read_text(encoding="utf-8", errors="surrogateescape")
    except Exception as e:  # noqa: BLE001
        return {"file": path_s, "error": f"read: {e}", "findings": [], "written": False}

    new_text = raw
    try:
        if fmt == "jsonl":
            lines = raw.split("\n")
            out_lines = []
            changed = False
            for i, line in enumerate(lines, 1):
                if not line or not _prefilter(line, det):
                    out_lines.append(line)
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    # truncated/corrupt line: known-format tokens only, which never contain quotes or backslashes
                    spans = [s for s in det.spans(line, False) if s[2] not in ("password", "secret_assignment")]
                    if spans:
                        red = apply_spans(line, spans)
                        for s in spans:
                            findings.append(Finding(path_s, i, "unparsed", s[2], s[1] - s[0], "", s[3], ""))
                        out_lines.append(red)
                        changed = True
                    else:
                        out_lines.append(line)
                    continue
                role = _role_of(obj) if isinstance(obj, dict) else "meta"
                new = walk(obj, det, role, path_s, i, findings)
                if new is not obj:
                    out = _dump_json_line(new)
                    json.loads(out)  # must still be valid JSON
                    out_lines.append(out)
                    changed = True
                else:
                    out_lines.append(line)
            if changed:
                assert len(out_lines) == len(lines)
                new_text = "\n".join(out_lines)
        elif fmt == "json":
            if _prefilter(raw, det):
                obj = json.loads(raw)
                new = walk(obj, det, "meta", path_s, 0, findings)
                if new is not obj:
                    indent = 2 if raw.lstrip().startswith("{\n") or "\n  " in raw[:200] else None
                    new_text = json.dumps(new, ensure_ascii=False, indent=indent,
                                          separators=None if indent else (",", ":"))
                    json.loads(new_text)
        else:  # text
            if _prefilter(raw, det):
                new_text = redact_string(raw, det, False, "file", path_s, 0, findings)
    except Exception as e:  # noqa: BLE001
        return {"file": path_s, "error": f"parse: {e}", "findings": [], "written": False}

    for f in findings:
        f.store = store
    written = False
    err = None
    if apply and new_text != raw:
        try:
            _atomic_write(path, new_text, st)
            written = True
        except Exception as e:  # noqa: BLE001
            err = f"write: {e}"
    return {"file": path_s, "error": err, "findings": [asdict(f) for f in findings], "written": written}


def is_binary(p: Path) -> bool:
    try:
        with open(p, "rb") as f:
            return b"\0" in f.read(4096)
    except Exception:  # noqa: BLE001
        return True


def rebase_stores(stores, root: Path):
    """Point the default store paths at another home directory (a backup, a copied profile)."""
    out = []
    for label, p, pattern, fmt in stores:
        try:
            rel = p.relative_to(HOME)
        except ValueError:  # APPDATA/XDG pointing outside home: skip rather than scan the wrong tree
            continue
        out.append((label, root / rel, pattern, fmt))
    return out


def collect(stores, paths, since_days, active_minutes, include_active):
    now = time.time()
    targets, skipped_active, seen = [], [], set()
    if paths:
        stores = []
        for p in paths:
            p = Path(p).expanduser()
            fmt = "jsonl" if p.suffix == ".jsonl" or p.is_dir() else ("json" if p.suffix == ".json" else "text")
            stores.append(("custom", p, "**/*.jsonl" if p.is_dir() else None, fmt))
    for label, root, pattern, fmt in stores:
        if not root.exists():
            continue
        files = [root] if pattern is None else [f for f in root.glob(pattern) if f.is_file()]
        for f in files:
            if f.name.endswith(".scrub-tmp") or f.resolve() in seen:
                continue
            seen.add(f.resolve())
            try:
                mt = f.stat().st_mtime
            except OSError:
                continue
            if since_days and now - mt > since_days * 86400:
                continue
            if fmt == "text" and (is_binary(f) or f.stat().st_size > 20_000_000):
                continue
            if not include_active and now - mt < active_minutes * 60:
                skipped_active.append(str(f))
                continue
            targets.append((str(f), fmt, label))
    return targets, skipped_active


def load_literals(path: str | None) -> list[str]:
    if not path:
        return []
    vals = []
    for line in Path(path).expanduser().read_text(encoding="utf-8").splitlines():
        v = line.rstrip("\r")
        if v and not v.startswith("#"):
            if len(v) < 4:
                sys.exit(f"values file: refusing a literal shorter than 4 chars (line would match everywhere)")
            vals.append(v)
    return vals


def short(p: str) -> str:
    return p.replace(str(HOME) + "/", "~/")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="rewrite files in place (default: dry run)")
    ap.add_argument("--all", action="store_true", help="also scan file-history, shell-snapshots, tasks, plans")
    ap.add_argument("--root", help="treat this dir as the home directory (scan a backup or copied profile)")
    ap.add_argument("--path", action="append", default=[], help="scan only this file/dir (repeatable)")
    ap.add_argument("--since", type=float, default=0, help="only files modified in the last N days")
    ap.add_argument("--values-file", help="file of exact values to scrub, one per line (you create it; never paste them in chat)")
    ap.add_argument("--delete-values-file", action="store_true", help="delete --values-file after a successful --apply")
    ap.add_argument("--aggressive", action="store_true", help="also flag bare high-entropy strings in text a human typed")
    ap.add_argument("--active-minutes", type=float, default=10, help="skip files modified within N minutes (live sessions)")
    ap.add_argument("--include-active", action="store_true", help="do not skip recently modified files (unsafe for live sessions)")
    ap.add_argument("--kinds", help="comma list: only report/redact these kinds")
    ap.add_argument("--format", choices=("text", "markdown", "json"), default="text",
                    help="text: box tables for a terminal; markdown: pipe tables for chat; json: raw")
    ap.add_argument("--json", action="store_true", help="same as --format json")
    ap.add_argument("--report", help="also save the report as markdown here (default after --apply: <home>/.claude/scrub-reports/)")
    ap.add_argument("--no-report-file", action="store_true", help="don't save a report file after --apply")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    a = ap.parse_args(argv)
    # Windows consoles default to cp1252, which can't print the table borders or ⏎
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure") and (stream.encoding or "").lower().replace("-", "") != "utf8":
            stream.reconfigure(encoding="utf-8", errors="replace")

    literals = load_literals(a.values_file)
    stores = DEFAULT_STORES + (EXTRA_STORES if a.all else [])
    if a.root:
        stores = rebase_stores(stores, Path(a.root).expanduser().resolve())
    targets, skipped = collect(stores, a.path, a.since, a.active_minutes, a.include_active)

    kinds = frozenset(a.kinds.split(",")) if a.kinds else None

    t0 = time.time()
    results = []
    jobs = [(f, fmt, store, literals, a.aggressive, a.apply, kinds) for f, fmt, store in targets]
    if a.workers > 1 and len(jobs) > 20:
        with ProcessPoolExecutor(a.workers) as ex:
            results = list(ex.map(process_file, jobs, chunksize=8))
    else:
        results = [process_file(j) for j in jobs]

    findings = [f for r in results for f in r["findings"]]
    errors = [r for r in results if r["error"]]
    written = [r["file"] for r in results if r["written"]]
    files_hit = sorted({f["file"] for f in findings})

    if a.apply and a.delete_values_file and a.values_file and not errors:
        Path(a.values_file).expanduser().unlink(missing_ok=True)

    summary = {
        "mode": "apply" if a.apply else "dry-run",
        "files_scanned": len(targets),
        "files_with_findings": len(files_hit),
        "files_rewritten": len(written),
        "findings": len(findings),
        "by_kind": dict(Counter(f["kind"] for f in findings).most_common()),
        "by_role": dict(Counter(f["role"] for f in findings).most_common()),
        "by_store": dict(Counter(f["store"] for f in findings).most_common()),
        "skipped_active": [short(s) for s in skipped],
        "errors": [{"file": short(r["file"]), "error": r["error"]} for r in errors],
        "seconds": round(time.time() - t0, 1),
    }

    fmt = "json" if a.json else a.format
    remaining = 0
    if a.apply and written:
        # prove it: re-scan exactly the files we rewrote
        by_path = {f: (fm, st) for f, fm, st in targets}
        recheck = [process_file((f, by_path[f][0], by_path[f][1], literals, a.aggressive, False, kinds)) for f in written]
        remaining = sum(len(r["findings"]) for r in recheck)
    summary["remaining_after_apply"] = remaining if a.apply else None

    home = Path(a.root).expanduser().resolve() if a.root else HOME
    report_path = None
    if a.report:
        report_path = Path(a.report).expanduser()
    elif a.apply and not a.no_report_file and findings:
        report_path = home / ".claude" / "scrub-reports" / time.strftime("%Y-%m-%d-%H%M%S.md")

    if a.apply:
        render = lambda md, rp: report.applied_report(summary, findings, remaining, rp, md)  # noqa: E731
    else:
        cmd = " ".join(["python3", short(str(Path(__file__).resolve()))]
                       + [x for x in (argv if argv is not None else sys.argv[1:])
                          if x not in ("--json",) and not x.startswith("--format")] + ["--apply"])
        render = lambda md, rp: report.findings_report(summary, findings, cmd, md)  # noqa: E731

    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render(True, short(str(report_path))), encoding="utf-8")
        os.chmod(report_path, 0o600)
        summary["report_file"] = short(str(report_path))

    if fmt == "json":
        for f in findings:
            f["file"] = short(f["file"])
        json.dump({"summary": summary, "findings": findings}, sys.stdout, ensure_ascii=False, indent=1)
        print()
    else:
        print(render(fmt == "markdown", short(str(report_path)) if report_path else None))
    return 1 if findings and not a.apply else 0


if __name__ == "__main__":
    sys.exit(main())
