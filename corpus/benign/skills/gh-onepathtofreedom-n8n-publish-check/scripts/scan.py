#!/usr/bin/env python3
"""n8n publish check: scan exported n8n workflow JSON for sensitive data
before it is committed or shared.

Heuristic scanner, standard library only. A clean result is NOT a guarantee.

Usage:
  scan.py workflow.json [more.json ...]
  scan.py workflow.json --sanitize workflow.public.json
  scan.py --only-workflows --fail-on medium a.json b.json   (pre-commit use)

Exit codes: 0 = nothing at/above --fail-on, 1 = findings, 2 = unreadable/invalid JSON.
Raw secret values are never printed in full.
"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path

SEV_RANK = {"low": 1, "medium": 2, "high": 3}

# --- detectors -------------------------------------------------------------

TOKEN_PATTERNS = [
    ("Anthropic API key", r"\bsk-ant-[A-Za-z0-9_\-]{20,}"),
    ("OpenAI-style API key", r"\bsk-(?:proj-|live-|test-)?[A-Za-z0-9_\-]{20,}"),
    ("GitHub token", r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}"),
    ("Slack token", r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    ("Slack webhook URL", r"https://hooks\.slack\.com/services/[A-Za-z0-9/]+"),
    ("Discord webhook URL", r"https://(?:discord|discordapp)\.com/api/webhooks/\d+/[\w-]+"),
    ("AWS access key ID", r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    ("Google API key", r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    ("Telegram bot token", r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b"),
    ("Stripe key", r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}"),
    ("Notion secret", r"\bsecret_[A-Za-z0-9]{30,}"),
    ("Airtable token", r"\bpat[A-Za-z0-9]{14}\.[a-f0-9]{64}"),
    ("JWT", r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    ("Private key block", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ("Bearer/Basic auth value", r"\b(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=\-]{16,}"),
]
TOKEN_RES = [(n, re.compile(p)) for n, p in TOKEN_PATTERNS]

# Key names that usually hold a secret when the value is a literal.
SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|apikey|secret|token|password|passwd|pwd|authorization|"
    r"bearer|private[_-]?key|client[_-]?secret|access[_-]?key)", re.I)
# ...but not when the key is clearly metadata about the secret.
SECRET_KEY_EXCLUDE_RE = re.compile(
    r"(url|uri|type|name|scope|field|expiry|expires|endpoint|header|location|prefix)$", re.I)
PLAIN_WORD_VALUES = {"none", "true", "false", "genericcredentialtype",
                     "predefinedcredentialtype", "oauth2api", "keypair"}

# Keys that point at resources in the author's real accounts.
RESOURCE_ID_KEY_RE = re.compile(
    r"^(chat|channel|document|spreadsheet|folder|file|database|base|table|list|"
    r"project|workspace|team|user|calendar|board|sheet|drive)_?id$", re.I)
RESOURCE_LABEL_KEYS = {"cachedResultName", "cachedResultUrl"}
WRAPPER_KEYS = {"value"} | RESOURCE_LABEL_KEYS

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
PLACEHOLDER_EMAIL_DOMAINS = {"example.com", "example.org", "example.net", "test.com",
                             "n8n.io", "domain.com", "yourdomain.com", "email.com"}
PHONE_RE = re.compile(r"(?<![\w.])\+\d[\d\s().\-]{8,16}\d")
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,7}(?:\s?[A-Z0-9]{1,4})?\b")
IPV4_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
URL_CRED_RE = re.compile(r"https?://[^/\s:@\"']+:[^/\s@\"']+@")
URL_SECRET_PARAM_RE = re.compile(
    r"[?&](?:api[_-]?key|apikey|key|token|access_token|secret|password|sig|signature)="
    r"(?![{$=])([^&\s\"']{6,})", re.I)
GDOC_RE = re.compile(
    r"(?:docs|drive)\.google\.com/[A-Za-z]+(?:/[A-Za-z]+)?/d/([A-Za-z0-9_\-]{20,})")


def is_expression_only(s):
    """True for n8n expressions that pull from env/credentials/vars instead of holding a literal."""
    return bool(re.search(r"\$(env|credentials|secrets|vars)\b", s)) and not any(
        rx.search(s) for _, rx in TOKEN_RES)


def iban_ok(s):
    s = re.sub(r"\s", "", s)
    if not (15 <= len(s) <= 34):
        return False
    r = s[4:] + s[:4]
    digits = "".join(str(int(c, 36)) for c in r)
    return int(digits) % 97 == 1


def mask(v):
    v = str(v)
    if len(v) <= 8:
        return "*" * len(v) + f" (len {len(v)})"
    return f"{v[:3]}…{v[-2:]} (len {len(v)})"


class Finding:
    def __init__(self, sev, label, path, match, whole=False, note=""):
        self.sev, self.label, self.path, self.match = sev, label, tuple(path), match
        self.whole, self.note = whole, note

    def key(self):
        return (self.path, str(self.match))


class Scanner:
    def __init__(self, cfg):
        self.deny = [t.lower() for t in cfg.get("deny_terms", []) if t]
        self.allow = [a.lower() for a in cfg.get("allow_values", []) if a]
        self.findings = {}

    def allowed(self, value):
        v = str(value).lower()
        return any(a in v for a in self.allow)

    def add(self, sev, label, path, match, whole=False, note=""):
        if match is not None and self.allowed(match):
            return
        if isinstance(match, str) and (match.strip() == "REPLACE_ME" or match.strip().startswith("<REDACTED")):
            return
        f = Finding(sev, label, path, match, whole, note)
        old = self.findings.get(f.key())
        if old is None or SEV_RANK[sev] > SEV_RANK[old.sev]:
            self.findings[f.key()] = f

    # -- string-level checks
    def scan_string(self, s, path, ctx_key):
        if not s.strip():
            return
        for label, rx in TOKEN_RES:
            for m in rx.finditer(s):
                self.add("high", label, path, m.group(0))
        for m in URL_CRED_RE.finditer(s):
            self.add("high", "Credentials inside URL", path, m.group(0))
        for m in URL_SECRET_PARAM_RE.finditer(s):
            self.add("high", "Secret in URL query parameter", path, m.group(1))
        for m in GDOC_RE.finditer(s):
            self.add("medium", "Google Docs/Drive/Sheets ID in URL", path, m.group(1))
        for m in EMAIL_RE.finditer(s):
            domain = m.group(0).split("@", 1)[1].lower()
            if domain not in PLACEHOLDER_EMAIL_DOMAINS:
                self.add("medium", "Email address", path, m.group(0))
        for m in PHONE_RE.finditer(s):
            self.add("medium", "Phone number", path, m.group(0))
        for m in IBAN_RE.finditer(s):
            if iban_ok(m.group(0)):
                self.add("high", "IBAN", path, m.group(0))
        for m in IPV4_RE.finditer(s):
            parts = [int(x) for x in m.group(0).split(".")]
            if all(p <= 255 for p in parts) and parts[0] not in (0, 127):
                self.add("medium", "IP address", path, m.group(0))
        low = s.lower()
        for term in self.deny:
            i = low.find(term)
            while i != -1:
                self.add("high", "Custom deny-list term", path, s[i:i + len(term)], note=f"matches '{term}'")
                i = low.find(term, i + len(term))

    # -- key/value checks
    def check_key_value(self, key, value, path, real_key=None):
        real_key = real_key or key
        if isinstance(value, str) and SECRET_KEY_RE.search(key) and not SECRET_KEY_EXCLUDE_RE.search(key):
            v = value.strip()
            if len(v) >= 6 and v.lower() not in PLAIN_WORD_VALUES and not is_expression_only(v):
                if not (v.startswith("=") and "{{" in v and not any(rx.search(v) for _, rx in TOKEN_RES)):
                    self.add("high", f"Literal value under secret-like key '{key}'", path, v, whole=True)
        if RESOURCE_ID_KEY_RE.match(key) and real_key not in RESOURCE_LABEL_KEYS:
            if isinstance(value, (str, int)) and not isinstance(value, bool):
                v = str(value)
                if v and not v.startswith("=") and "{{" not in v and len(v) >= 5:
                    self.add("medium", f"Resource ID '{key}' (points at your real account)", path, v, whole=True)
        if real_key in RESOURCE_LABEL_KEYS and isinstance(value, str) and value.strip():
            self.add("medium", f"Cached resource label '{real_key}' (may reveal names/IDs)", path, value, whole=True)

    def walk(self, node, path, ctx_key=""):
        if isinstance(node, dict):
            # {"name": "Authorization", "value": "Bearer ..."} pairs (headers, query params)
            if isinstance(node.get("name"), str) and isinstance(node.get("value"), str):
                nm = node["name"]
                if SECRET_KEY_RE.search(nm) and not SECRET_KEY_EXCLUDE_RE.search(nm):
                    v = node["value"].strip()
                    if len(v) >= 6 and not is_expression_only(v) and not (v.startswith("=") and "{{" in v):
                        self.add("high", f"Literal value for secret-like parameter '{nm}'",
                                 path + ["value"], v, whole=True)
            for k, v in node.items():
                eff = ctx_key if k in WRAPPER_KEYS and ctx_key else k
                self.check_key_value(eff if k in WRAPPER_KEYS else k, v, path + [k], k)
                self.walk(v, path + [k], eff)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                self.walk(v, path + [i], ctx_key)
        elif isinstance(node, str):
            self.scan_string(node, path, ctx_key)

    # -- n8n specific structure
    def scan_workflow(self, wf):
        if not isinstance(wf, dict):
            self.walk(wf, [])
            return
        for k, v in wf.items():
            if k == "pinData":
                if v:
                    self.add("high", "pinData present (real sample data from executions)", [k], "pinData", whole=True,
                             note="often contains real customer/API data")
                continue
            if k == "staticData":
                if v:
                    self.add("medium", "staticData present (can hold tokens/state)", [k], "staticData", whole=True)
                continue
            if k in ("shared", "homeProject") and v:
                self.add("medium", f"'{k}' block (contains project/owner names, often an email)", [k], k, whole=True)
                continue
            if k == "meta" and isinstance(v, dict) and v.get("instanceId"):
                self.add("low", "meta.instanceId (identifies your n8n instance)", [k, "instanceId"],
                         str(v["instanceId"]), whole=True)
            if k == "nodes" and isinstance(v, list):
                for i, n in enumerate(v):
                    self.scan_node(n, [k, i])
                continue
            self.walk(v, [k], k)

    def scan_node(self, n, path):
        if not isinstance(n, dict):
            self.walk(n, path)
            return
        ntype = str(n.get("type", "")).lower()
        for k, v in n.items():
            p = path + [k]
            if k == "credentials" and isinstance(v, dict) and v:
                for ctype, cval in v.items():
                    if isinstance(cval, dict):
                        for f in ("id", "name"):
                            if cval.get(f):
                                self.add("low", f"Credential {f} reference ({ctype})", p + [ctype, f],
                                         str(cval[f]), whole=True)
                continue
            if k == "webhookId" and v:
                self.add("low", "webhookId", p, str(v), whole=True)
                continue
            if k == "parameters" and isinstance(v, dict):
                if ("webhook" in ntype or "formtrigger" in ntype) and isinstance(v.get("path"), str) and v["path"]:
                    self.add("medium", "Webhook path (acts as a secret URL)", p + ["path"], v["path"], whole=True)
                self.walk(v, p, k)
                continue
            self.walk(v, p, k)


# --- helpers ---------------------------------------------------------------

def fmt_path(path):
    out = ""
    for p in path:
        out += f"[{p}]" if isinstance(p, int) else (("." if out else "") + str(p))
    return out


def node_name(wf, path):
    try:
        if path and path[0] == "nodes":
            return wf["nodes"][path[1]].get("name", "")
    except Exception:
        pass
    return ""


def looks_like_workflow(d):
    return isinstance(d, dict) and "nodes" in d and "connections" in d


def get_at(root, path):
    cur = root
    for p in path[:-1]:
        cur = cur[p]
    return cur, path[-1]


def sanitize(wf, findings):
    out = copy.deepcopy(wf)
    if isinstance(out, dict):
        out.pop("pinData", None)
        out.pop("staticData", None)
        out.pop("shared", None)
        out.pop("homeProject", None)
        if isinstance(out.get("meta"), dict):
            out["meta"].pop("instanceId", None)
        for n in out.get("nodes", []) if isinstance(out.get("nodes"), list) else []:
            if isinstance(n, dict):
                n.pop("webhookId", None)
                if isinstance(n.get("credentials"), dict):
                    for cval in n["credentials"].values():
                        if isinstance(cval, dict):
                            for f in ("id", "name"):
                                if f in cval:
                                    cval[f] = "REPLACE_ME"
    # apply string/value findings, longest paths first so indices stay valid
    for f in sorted(findings, key=lambda x: -len(x.path)):
        if f.path and f.path[0] in ("pinData", "staticData", "shared", "homeProject"):
            continue
        try:
            container, last = get_at(out, list(f.path))
            cur = container[last]
        except (KeyError, IndexError, TypeError):
            continue
        if "Credential" in f.label or f.label == "webhookId" or "instanceId" in f.label:
            continue
        tag = "REPLACE_ME" if f.whole else f"<REDACTED:{f.label}>"
        if f.whole or not isinstance(cur, str):
            container[last] = tag if isinstance(cur, str) else "REPLACE_ME"
        else:
            container[last] = cur.replace(f.match, tag)
    return out


def load_config(explicit):
    for cand in ([explicit] if explicit else []) + [".n8n-publish-check.json"]:
        if cand and Path(cand).is_file():
            try:
                return json.loads(Path(cand).read_text(encoding="utf-8"))
            except Exception as e:
                print(f"warning: cannot read config {cand}: {e}", file=sys.stderr)
    return {}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--sanitize", metavar="OUT", help="write a sanitized copy (single input file only)")
    ap.add_argument("--fail-on", choices=["low", "medium", "high"], default="medium")
    ap.add_argument("--only-workflows", action="store_true", help="silently skip JSON that is not an n8n workflow")
    ap.add_argument("--config", help="path to config JSON (default: ./.n8n-publish-check.json)")
    args = ap.parse_args()
    if args.sanitize and len(args.files) != 1:
        ap.error("--sanitize needs exactly one input file")

    cfg = load_config(args.config)
    exit_code = 0
    for fp in args.files:
        try:
            wf = json.loads(Path(fp).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"ERROR {fp}: not valid JSON ({e})")
            exit_code = max(exit_code, 2)
            continue
        wfs = wf if isinstance(wf, list) else [wf]
        if args.only_workflows and not any(looks_like_workflow(w) for w in wfs):
            continue
        if not any(looks_like_workflow(w) for w in wfs):
            print(f"note: {fp} does not look like an n8n workflow export; scanning anyway")
        sc = Scanner(cfg)
        for w in wfs:
            sc.scan_workflow(w)
        fnd = sorted(sc.findings.values(), key=lambda f: (-SEV_RANK[f.sev], fmt_path(f.path)))
        counts = {s: sum(1 for f in fnd if f.sev == s) for s in ("high", "medium", "low")}
        print(f"\n=== {fp}: {counts['high']} high, {counts['medium']} medium, {counts['low']} low ===")
        base = wfs[0] if len(wfs) == 1 else {}
        for f in fnd:
            nm = node_name(base, f.path)
            where = f" (node '{nm}')" if nm else ""
            shown = f.note or mask(f.match)
            print(f"[{f.sev.upper():6}] {fmt_path(f.path)}{where}\n         {f.label}: {shown}")
        if not fnd:
            print("no findings (heuristic check; not a guarantee)")
        if any(SEV_RANK[f.sev] >= SEV_RANK[args.fail_on] for f in fnd):
            exit_code = max(exit_code, 1)
        if args.sanitize:
            clean = sanitize(wf, fnd)
            Path(args.sanitize).write_text(json.dumps(clean, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"\nsanitized copy written to {args.sanitize} (original untouched); re-run the scan on it")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
