"""Adversarial Agents MCP server.

Exposes the adversarial review framework as callable MCP tools so any agent
(Claude, Cursor, external runtime, or a custom client) can run a governed review,
check a hard veto, record/query verdicts, and inventory the framework.

The server reads the framework directly from the repo layout:

    ~/adversarial-agents/
      adversarial-<domain>/          # plugin source of truth
        agents/*.md                  # adversary agent definitions
        skills/*/SKILL.md            # stateless skills
        references/constitution.md   # constitutional rules
        references/calibration-ledger.md
      agents/                        # flat namespaced agents (ux-critic, eng-...)
      skills/                        # flat namespaced skills (ux-altitude-check, ...)

Verdicts are appended to a JSONL decision record under runs/ (gitignored), so
real review history never gets committed.
"""

from __future__ import annotations

import hmac
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import setup_wizard
from . import spend as spend_meter
from . import updates as update_check
from .spend import SpendCapExceeded

# ---------------------------------------------------------------------------
# Framework discovery
# ---------------------------------------------------------------------------

# Repo root resolves from this file's own location (mcp/adversarial_mcp/server.py
# → up two parents to the repo root) so the repo can be renamed or cloned
# anywhere without breaking. ADVERSARIAL_ROOT overrides when set.
REPO_ROOT = Path(os.environ.get("ADVERSARIAL_ROOT", Path(__file__).resolve().parents[2]))
DOMAINS = ["ux", "engineer", "qa", "researcher", "universal", "prompt", "security", "privacy", "compliance", "product", "ops", "docs"]
DOMAIN_DIR = {d: REPO_ROOT / f"adversarial-{d}" for d in DOMAINS}

RUNS_DIR = REPO_ROOT / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)
VERDICT_LOG = Path(os.environ.get("VERDICT_LOG", RUNS_DIR / "verdicts.jsonl"))

# A21: retention window (days) for the calibration ledger. Entries older than
# this are summarized to a stub on load (age-out). The operator sets this;
# default 90 days.
RETENTION_DAYS = int(os.environ.get("LEDGER_RETENTION_DAYS", "90"))


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _frontmatter(text: str) -> dict[str, Any]:
    """Parse YAML-ish frontmatter (name:, description:, etc.) leniently."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    out: dict[str, Any] = {}
    if not m:
        return out
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _agents_for(domain: str) -> list[dict[str, str]]:
    d = DOMAIN_DIR.get(domain)
    if not d:
        return []
    out = []
    for f in sorted((d / "agents").glob("*.md")):
        text = _read(f)
        fm = _frontmatter(text)
        out.append(
            {
                "name": fm.get("name", f.stem),
                "file": f.name,
                "description": fm.get("description", ""),
                "body": text,
            }
        )
    return out


def _skills_for(domain: str) -> list[dict[str, str]]:
    d = DOMAIN_DIR.get(domain)
    if not d:
        return []
    out = []
    for f in sorted((d / "skills").glob("*/SKILL.md")):
        text = _read(f)
        fm = _frontmatter(text)
        out.append(
            {
                "name": fm.get("name", f.parent.name),
                "dir": f.parent.name,
                "description": fm.get("description", ""),
                "body": text,
            }
        )
    return out


def _constitution(domain: str) -> str:
    # Per-domain constitutions live in constitution/domains/<domain>.md
    # (moved out of capability folders). See the governance restructure changelog.
    return _read(REPO_ROOT / "constitution" / "domains" / f"{domain}.md")


def _standard(domain: str) -> str:
    # Each plugin ships exactly one standard file under references/ with a
    # domain-specific name. Glob for it and require exactly one match; on zero
    # or several, return an explicit error naming the domain (never silent-empty).
    refs_dir = DOMAIN_DIR.get(domain, Path()) / "references"
    candidates = [
        p for p in sorted(refs_dir.glob("*.md"))
        if p.name not in ("calibration-ledger.md", "personas.md")
    ]
    if len(candidates) == 1:
        return candidates[0].read_text(encoding="utf-8", errors="replace")
    names = [p.name for p in candidates]
    if len(candidates) == 0:
        return f"<STANDARD MISSING for domain '{domain}': no standard file found in {refs_dir}>"
    return (f"<STANDARD AMBIGUOUS for domain '{domain}': expected exactly one standard "
            f"file in {refs_dir}, found {len(candidates)}: {', '.join(names)}>")


def _personas(domain: str) -> str:
    return _read(DOMAIN_DIR.get(domain, Path()) / "references" / "personas.md")


def _ledger(domain: str) -> str:
    return _read(DOMAIN_DIR.get(domain, Path()) / "references" / "calibration-ledger.md")


# ---------------------------------------------------------------------------
# Verdict / decision-record persistence
# ---------------------------------------------------------------------------


def _events_module():
    """Load scripts/events.py (ADR-0009 event log). scripts/ is not a package."""
    import sys

    scripts = str(Path(__file__).resolve().parents[2] / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import events  # noqa: E402

    return events


def _event_log() -> Path:
    return Path(os.environ.get("EVENT_LOG", RUNS_DIR / "events.jsonl"))


def _append_verdict(record: dict[str, Any]) -> None:
    ev_mod = _events_module()
    record.setdefault("status", "active")
    record.setdefault("provenance", "")
    # ADR-0009: every verdict is also an event in the append-only log. The
    # event_id is copied onto the verdict record so telemetry can dedupe on it.
    ev = ev_mod.emit(
        "verdict.recorded",
        path=_event_log(),
        ticket=record.get("ticket") or None,
        role=record.get("domain") or None,
        outcome=record.get("verdict"),
        data={
            "summary": record.get("summary", ""),
            "rule": record.get("rule", ""),
            "case_tag": record.get("case_tag", ""),
            "source": record.get("source", ""),
        },
    )
    record.setdefault("ts", ev["ts"])
    record.setdefault("event_id", ev["event_id"])
    # A22: every ruling carries a status (active by default) and a provenance
    # field linking the artifact to the ruling that permitted it.
    ev_mod.append_jsonl(VERDICT_LOG, record)


def _load_verdicts(domain: str | None = None, limit: int = 50, source: str | None = None) -> list[dict[str, Any]]:
    if not VERDICT_LOG.exists():
        return []
    rows = []
    for line in VERDICT_LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if domain and r.get("domain") != domain:
            continue
        if source is not None and r.get("source") != source:
            continue
        rows.append(r)
    # A21 age-out: entries older than the retention window are summarized to a
    # stub (kept, but flagged) so the ledger does not grow without bound. The
    # retention window is in days; the operator sets it (default 90).
    rows = [_age_out(r) for r in rows]
    return rows[-limit:]


def _age_out(record: dict[str, Any]) -> dict[str, Any]:
    """A21: summarize an entry older than the retention window to a stub.

    The full record is retained on disk (append-only); the stub is what a
    consumer sees for old entries, so the load cost stays bounded while the
    history is preserved.
    """
    ts = record.get("ts")
    if not ts:
        return record
    age_days = (time.time() * 1000 - ts) / 86400000.0
    if age_days <= RETENTION_DAYS:
        return record
    return {
        "kind": record.get("kind", "verdict"),
        "domain": record.get("domain", ""),
        "verdict": record.get("verdict", ""),
        "summary": "[aged out] " + (record.get("summary", "") or "")[:80],
        "ticket": record.get("ticket", ""),
        "rule": record.get("rule", ""),
        "case_tag": record.get("case_tag", ""),
        "ts": ts,
        "aged_out": True,
    }


# ---------------------------------------------------------------------------
# Review engine (deterministic structural checks + prompt assembly)
# ---------------------------------------------------------------------------

VETO_KEYWORDS = {
    "ux": [
        "dead end", "accessibility impossible", "silent divergence", "data loss",
        "money loss", "user harm", "screen reader", "no keyboard access",
    ],
    "engineer": [
        "data loss", "security hole", "bricked config", "production outage",
        "credential leak", "security breach", "api key", "secret exposed",
        "leak credential", "expose secret", "sql injection", "remote code execution",
        "privilege escalation", "downtime", "rollback impossible",
    ],
    "qa": [
        "user harm", "data loss", "money loss", "release-blocking defect",
        "crash on launch", "data corruption", "security regression",
    ],
    "researcher": [
        "unsupported claim", "fabricated user", "causal claim from correlation",
        "no source", "made up data", "fabricated data", "no evidence",
    ],
    "universal": [
        "irrecoverable harm", "data loss", "security breach", "credential leak",
        "safety", "api key", "secret exposed", "privacy violation", "legal liability",
    ],
    "prompt": [
        "injected instruction", "safety override", "clear a veto", "exfiltrate data",
        "ignore previous instructions", "role override", "loyalty shift",
        "secret exfiltration", "bypass the human gate",
    ],
    "security": [
        "exploitable vulnerability", "secret exposure", "credential leak", "api key",
        "sql injection", "remote code execution", "privilege escalation", "auth bypass",
        "critical cve", "untrusted dependency", "sensitive data exposed",
    ],
    "privacy": [
        "unlawful data collection", "no consent", "unbounded retention",
        "no subject rights", "unlawful transfer", "pii exposed", "gdpr violation",
        "ccpa violation",
    ],
    "compliance": [
        "regulatory violation", "policy violation", "no evidence of compliance",
        "no audit trail", "non-compliant", "legal liability",
    ],
    "product": [
        "unvalidated market assumption", "fabricated user need",
        "unsupported competitive claim", "unsound business case", "market risk",
    ],
    "ops": [
        "irreversible deployment", "no rollback path", "no disaster recovery",
        "unobservable in production", "downtime", "data loss",
    ],
    "docs": [
        "factually wrong documentation", "missing critical documentation",
        "misleading documentation", "outdated documentation",
    ],
}

# Regex patterns for credential/secret exposure that keyword matching misses.
# Destructive actions, matched on what the plan says it will do rather than on
# whether it names the harm. VETO_KEYWORDS catch "this causes data loss"; these
# catch "drop the production database". Still a word match: a plan that does
# damage in words not listed here passes the scan and the adversary has to
# catch it. Kept narrow on purpose, because every hit is a KICK_BACK that only
# a human can clear.
DESTRUCTIVE_ACTION_PATTERNS = [
    # drop / truncate / wipe something in production
    r"\b(drop|truncate|delete|wipe|purge|destroy|erase)\b.{0,30}\b(prod|production|live)\b"
    r".{0,20}\b(database|db|table|tables|schema|data|bucket|cluster|volume)s?\b",
    r"\b(drop|truncate)\s+(table|database|schema)\b",
    # recursive force delete
    r"\brm\s+-(?=[a-z]*r)(?=[a-z]*f)[a-z]+\b",
    # force-push to a shared branch
    r"\b(force[- ]push|push\s+(-f|--force)\b)[^.\n]{0,40}\b(main|master|prod|production|release)\b",
    # proceeding with no way back
    r"\b(no|without( a)?|skip(ping)?( the)?)\s+(backups?|rollback|roll[- ]back)\b",
    # switching off a protection
    r"\b(disabl\w*|turn(ing)? off|bypass\w*)\s+(the\s+)?(auth\w*|mfa|2fa|tls|ssl|encryption)\b",
]

VETO_PATTERNS = {
    "engineer": [r"(expos|leak|commit).{0,20}(api[ -]?key|secret|credential|token|password)",
                  r"(api[ -]?key|secret|credential|token|password).{0,20}(expos|leak|log|commit)",
                  *DESTRUCTIVE_ACTION_PATTERNS],
    "universal": [r"(expos|leak).{0,20}(api[ -]?key|secret|credential|token|password)",
                  *DESTRUCTIVE_ACTION_PATTERNS],
    "ops": [*DESTRUCTIVE_ACTION_PATTERNS],
}


def _veto_hits(domain: str, text: str) -> list[str]:
    import re as _re

    text_l = text.lower()
    hits = [k for k in VETO_KEYWORDS.get(domain, []) if k in text_l]
    for pat in VETO_PATTERNS.get(domain, []):
        if _re.search(pat, text_l):
            hits.append(f"pattern:{pat}")
    return hits


def _run_structural_review(domain: str, work: str) -> dict[str, Any]:
    """Deterministic first pass: veto scan + basic completeness checks."""
    hits = _veto_hits(domain, work)
    agents = _agents_for(domain)
    return {
        "domain": domain,
        "veto_hits": hits,
        "veto_triggered": bool(hits),
        "agent_count": len(agents),
        "agents": [a["name"] for a in agents],
        "work_chars": len(work),
    }


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP("adversarial-agents")


@mcp.tool()
def setup_wizard_start() -> dict[str, Any]:
    """Begin (or resume) the conversational governance setup wizard (Section 9.3).
    Returns the first/pending question, with labeled options where bounded. Call
    setup_wizard_answer() with the operator's reply."""
    return setup_wizard.start_wizard(REPO_ROOT)


@mcp.tool()
def setup_wizard_answer(answer: str) -> dict[str, Any]:
    """Record the operator's answer to the current wizard question and return the
    next question, or the completion summary when the wizard is done. For bounded
    questions, answer must be one of the offered options; for roster rows, send
    'done' to finish the roster. On completion writes config/setup.md,
    config/roster.md, config/design-system.md + config/design-tokens.json (BYODS), persona blocks under
    config/personas/, and — when a coordinating role is on the roster — an optional
    private-notes folder when a coordinating role is on the roster."""
    return setup_wizard.answer_wizard(REPO_ROOT, answer)


@mcp.tool()
def design_system_palettes() -> dict[str, Any]:
    """Return the curated design-system starter data used by the setup wizard's
    BYODS step: contrast-checked starter palettes, the recommended CVD-safe
    data-viz palette (Okabe-Ito), free Google Font recommendations, brand
    voice styles, predefined codified design systems, neutral ramps, corner
    radius styles, and icon sets. The operator's agent renders these natively
    (swatches, a color-wheel picker, option lists) and passes the operator's
    choice back through setup_wizard_answer(); the framework records the choice
    as config — it does not pixel-enforce it."""
    return {
        "starter_palettes": [
            {
                "id": pid,
                "name": name,
                "primary": phex,
                "secondary": shex,
                "tertiary": thex,
                "note": "Primary is text-safe (>= 4.5:1 on white, WCAG AA); "
                "secondary/tertiary are accent-grade.",
            }
            for pid, (name, phex, shex, thex) in setup_wizard.DS_PALETTES.items()
        ],
        "neutral_ramps": [
            {
                "id": nid,
                "name": name,
                "light": light,
                "dark": dark,
                "note": "bg / surface / text / muted / border.",
            }
            for nid, (name, light, dark) in setup_wizard.DS_NEUTRALS.items()
        ],
        "radius_styles": [
            {"id": rid, "value": value}
            for rid, value in setup_wizard.DS_RADIUS_VALUES.items()
        ],
        "icon_sets": setup_wizard.DS_ICON_SETS,
        "data_viz_cvd_safe": {
            "name": "Okabe-Ito (recommended)",
            "colors": setup_wizard.DS_VIZ_OKABE_ITO,
            "note": "Color-vision-deficiency-safe qualitative palette.",
        },
        "font_recommendations": {
            "primary": setup_wizard.DS_FONTS_PRIMARY,
            "secondary": setup_wizard.DS_FONTS_SECONDARY,
            "note": "All recommendations are free Google Fonts; 'custom' names your own.",
        },
        "brand_voice_styles": setup_wizard.BRAND_VOICES,
        "predefined_design_systems": [
            {"id": pid, "name": name, "url": url}
            for pid, (name, url) in setup_wizard.DS_PRESETS.items()
        ],
    }


@mcp.tool()
def list_domains() -> list[str]:
    """List the adversarial domains available (ux, engineer, qa, researcher, universal)."""
    return DOMAINS


@mcp.tool()
def list_agents(domain: str) -> list[dict[str, str]]:
    """List the adversary agents for a domain (e.g. 'ux' -> ux-critic, ux-cx-advocate, ...)."""
    return [{"name": a["name"], "description": a["description"]} for a in _agents_for(domain)]


@mcp.tool()
def list_skills(domain: str) -> list[dict[str, str]]:
    """List the stateless skills available for a domain."""
    return [{"name": s["name"], "description": s["description"]} for s in _skills_for(domain)]


@mcp.tool()
def get_constitution(domain: str) -> str:
    """Return the constitutional rules (hard gates) for a domain."""
    return _constitution(domain) or f"No constitution found for domain '{domain}'."


@mcp.tool()
def get_standard(domain: str) -> str:
    """Return the domain standard (quality bar) for a domain."""
    return _standard(domain) or f"No standard found for domain '{domain}'."


@mcp.tool()
def get_agent(domain: str, agent_name: str) -> str:
    """Return the full body of a specific adversary agent (e.g. domain='ux', agent_name='ux-critic')."""
    for a in _agents_for(domain):
        if a["name"] == agent_name or a["file"].startswith(agent_name):
            return a["body"]
    return f"Agent '{agent_name}' not found in domain '{domain}'."


@mcp.tool()
def run_review(domain: str, work: str, context: str = "", source: str = "app") -> dict[str, Any]:
    """Run a governed adversarial review on a piece of work.

    Args:
        domain: one of ux, engineer, qa, researcher, universal.
        work: the artifact/decision/claim to review (code, design, plan, message, research).
        context: optional surrounding context (ticket, constraints, prior findings).
        source: provenance tag for the verdict log — "app" for real reviews, or a
            test/automation tag (e.g. "smoke_test") so records can be filtered out.

    Returns a structured verdict: structural scan, veto status, and the review
    prompt assembled for the domain's adversary agents.
    """
    try:
        spend_meter.refuse_if_over_cap(REPO_ROOT, pending_units=1.0)
    except SpendCapExceeded as e:
        return {"status": "refused", "reason": "spend_cap", "error": str(e)}
    spend_meter.record_usage(1.0, source="run_review", note=domain, repo_root=REPO_ROOT)
    structural = _run_structural_review(domain, work)
    agents = _agents_for(domain)
    constitution = _constitution(domain)

    review_prompt = (
        f"# Adversarial review — domain: {domain}\n\n"
        f"## Work under review\n{work}\n\n"
        f"## Context\n{context or '(none provided)'}\n\n"
        f"## Constitutional rules\n{constitution or '(none)'}\n\n"
        f"## Adversary agents to run\n"
        + "\n".join(f"- {a['name']}: {a['description']}" for a in agents)
        + "\n\nFor each agent, produce: findings, severity (blocker/major/minor/nit), "
        "and a verdict of KICK_BACK or ALLOW. If any agent finds a blocker or a "
        "constitutional veto is triggered, the overall verdict is KICK_BACK."
    )

    verdict = "KICK_BACK" if structural["veto_triggered"] else "REVIEW_REQUIRED"
    result = {
        "domain": domain,
        "verdict": verdict,
        "veto_triggered": structural["veto_triggered"],
        "veto_hits": structural["veto_hits"],
        "agents": structural["agents"],
        "review_prompt": review_prompt,
    }
    _append_verdict(
        {
            "kind": "review",
            "domain": domain,
            "verdict": verdict,
            "veto_hits": structural["veto_hits"],
            "work_chars": structural["work_chars"],
            "rule": "constitution-rule-1" if structural["veto_triggered"] else "",
            "case_tag": "veto" if structural["veto_triggered"] else "review",
            "provenance": context or "",  # A22: link the artifact to its ruling
            "source": source,
        }
    )
    return result


# ---------------------------------------------------------------------------
# Deep review (LLM-invoked)
# ---------------------------------------------------------------------------

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEEP_MODEL = os.environ.get("ADVERSARIAL_DEEP_MODEL", "gemma3:12b")


def _ollama_generate(prompt: str, model: str | None = None) -> str:
    """Call Ollama to run the adversary agents on the assembled prompt."""
    import sys
    import urllib.request

    scripts = str(REPO_ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from approval import ApprovalRequired, require_approval

    try:
        require_approval("ollama_generate", REPO_ROOT)
    except ApprovalRequired as e:
        return f"ERROR: {e}"

    payload = json.dumps(
        {
            "model": model or DEEP_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2, "num_ctx": 8192},
        }
    ).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())
        return data.get("response", "")
    except Exception as e:
        return f"ERROR: deep review failed: {e}"


@mcp.tool()
def run_review_deep(domain: str, work: str, context: str = "", model: str = "") -> dict[str, Any]:
    """Run a governed adversarial review, invoking the adversary agents via an LLM.

    Unlike run_review (which assembles the prompt), this actually calls the LLM
    to execute the domain's adversary agents and returns their findings.

    Gated by framework-visible spend metering: refuses when recorded units meet
    the configured cap. Does not observe model-provider dollars.

    Args:
        domain: one of the adversarial domains.
        work: the artifact/decision/claim to review.
        context: optional surrounding context.
        model: optional Ollama model override (default gemma3:12b).

    Returns the structural scan plus the LLM-generated verdict and findings.
    """
    try:
        spend_meter.refuse_if_over_cap(REPO_ROOT, pending_units=1.0)
    except SpendCapExceeded as e:
        return {"status": "refused", "reason": "spend_cap", "error": str(e)}
    spend_meter.record_usage(1.0, source="run_review_deep", note=domain, repo_root=REPO_ROOT)
    structural = _run_structural_review(domain, work)
    agents = _agents_for(domain)
    constitution = _constitution(domain)
    standard = _standard(domain)

    prompt = (
        f"You are the adversarial review team for the '{domain}' domain.\n\n"
        f"## Work under review\n{work}\n\n"
        f"## Context\n{context or '(none provided)'}\n\n"
        f"## Constitution\n{constitution or '(none)'}\n\n"
        f"## Standard\n{standard or '(none)'}\n\n"
        f"## Adversary agents\n"
        + "\n".join(f"- {a['name']}: {a['description']}" for a in agents)
        + "\n\nFor each agent, produce findings with severity "
        "(BLOCKER/CONCERN/NOTE) and a verdict of KICK_BACK or ALLOW. "
        "If any agent finds a BLOCKER or a constitutional veto is triggered, "
        "the overall verdict is KICK_BACK. End with: VERDICT: KICK_BACK|ALLOW"
    )

    llm_out = _ollama_generate(prompt, model or None)
    llm_lower = llm_out.lower()
    llm_verdict = "KICK_BACK" if "kick_back" in llm_lower else "ALLOW"
    # A structural veto overrides the LLM verdict — the veto is absolute.
    final_verdict = "KICK_BACK" if structural["veto_triggered"] else llm_verdict

    result = {
        "domain": domain,
        "verdict": final_verdict,
        "veto_triggered": structural["veto_triggered"],
        "veto_hits": structural["veto_hits"],
        "agents": structural["agents"],
        "model": model or DEEP_MODEL,
        "llm_findings": llm_out,
    }
    _append_verdict(
        {
            "kind": "deep_review",
            "domain": domain,
            "verdict": final_verdict,
            "veto_hits": structural["veto_hits"],
            "rule": "constitution-rule-1" if structural["veto_triggered"] else "",
            "case_tag": "veto" if structural["veto_triggered"] else "deep_review",
            "provenance": context or "",  # A22: link the artifact to its ruling
            "model": model or DEEP_MODEL,
        }
    )
    return result


@mcp.tool()
def check_veto(domain: str, text: str) -> dict[str, Any]:
    """Check whether text trips a hard constitutional veto for a domain.

    Returns the triggered veto keywords and a boolean. A veto means only a human
    can clear it — the work must be kicked back.
    """
    hits = _veto_hits(domain, text)
    return {"domain": domain, "veto_triggered": bool(hits), "veto_hits": hits}


@mcp.tool()
def record_verdict(domain: str, verdict: str, summary: str, ticket: str = "", rule: str = "", case_tag: str = "") -> dict[str, Any]:
    """Record a review verdict to the decision record (calibration ledger).

    Args:
        domain: the domain reviewed.
        verdict: KICK_BACK or ALLOW.
        summary: short human summary of the outcome.
        ticket: optional ticket/issue id.
        rule: the rule cited (A21 structured field — e.g. the constitution rule
            or harness section the verdict turns on).
        case_tag: a short case tag for precedent matching (A21 structured
            field — e.g. "veto-production-harm", "two-approaches").
    """
    rec = {
        "kind": "verdict",
        "domain": domain,
        "verdict": verdict.upper(),
        "summary": summary,
        "ticket": ticket,
        "rule": rule,
        "case_tag": case_tag,
        "source": "app",
    }
    try:
        _append_verdict(rec)
    except Exception as e:  # KeyRequired on a keyed log without the key, lock timeout, ...
        return {"recorded": False, "error": str(e)}
    return {"recorded": True, "record": rec}


@mcp.tool()
def query_verdicts(domain: str = "", limit: int = 50, source: str = "") -> list[dict[str, Any]]:
    """Query recent review verdicts from the decision record. Optionally filter by
    domain and/or source (e.g. source="app" for real reviews, source="smoke_test"
    to inspect test records). An empty source filter matches all sources.

    Verdicts recorded by the ticket chain are returned without their
    ``summary``: a reviewer must not read an earlier reviewer's reasons for
    the ticket it is reviewing (blind review, AGENTS.md rule 1). Operators
    read them with ``ticket.py show`` or the event log."""
    rows = _load_verdicts(domain or None, limit, source or None)
    # Chain copies are the rows chain.py writes with agent_verified.
    return [{k: v for k, v in r.items() if k != "summary"} if "agent_verified" in r else r for r in rows]


@mcp.tool()
def overturn_verdict(ticket: str, reason: str) -> dict[str, Any]:
    """A22: mark a ruling as overturned (status, not deletion).

    Only a human overturns a precedent (matching who clears a veto). The ruling
    keeps its record but is flagged `overturned` so it is no longer citable as
    precedent — a bot that would have cited it must instead escalate (the
    overturned status makes the match "arguable," which already means escalate
    under 10.1).

    Args:
        ticket: the ticket/issue id of the ruling to overturn.
        reason: why it is overturned (recorded for the audit trail).
    """
    if not ticket or not reason:
        return {"status": "error", "error": "ticket and reason are required."}
    _events_module()  # puts scripts/ on sys.path
    from approval import ApprovalRequired, require_approval
    try:
        require_approval("overturn_verdict", REPO_ROOT, consume=True)
    except ApprovalRequired as e:
        return {"status": "refused", "error": f"Only a human overturns a precedent. {e}"}
    if not VERDICT_LOG.exists():
        return {"status": "error", "error": "No verdict log to overturn from."}
    ev_mod = _events_module()
    with ev_mod.file_lock(VERDICT_LOG):
        result = _overturn_locked(ticket, reason)
    if result.get("status") == "overturned":
        ev_mod.emit(
            "verdict.overturned",
            path=_event_log(),
            ticket=ticket,
            outcome="overturned",
            data={"reason": reason},
        )
    return result


def _overturn_locked(ticket: str, reason: str) -> dict[str, Any]:
    """Rewrite the verdict view with the ruling flagged. Caller holds the lock.
    The event log keeps the original verdict event untouched (append-only)."""
    lines = VERDICT_LOG.read_text(encoding="utf-8").splitlines()
    found = False
    out = []
    for line in lines:
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            out.append(line)
            continue
        if r.get("ticket") == ticket and r.get("status") != "overturned":
            r["status"] = "overturned"
            r["overturned_at"] = int(time.time() * 1000)
            r["overturned_reason"] = reason
            found = True
        out.append(json.dumps(r))
    if not found:
        return {"status": "error", "error": f"No active ruling found for ticket '{ticket}'."}
    tmp = VERDICT_LOG.with_name(VERDICT_LOG.name + ".tmp")
    tmp.write_text("\n".join(out) + "\n", encoding="utf-8")
    os.replace(tmp, VERDICT_LOG)
    return {"status": "overturned", "ticket": ticket, "reason": reason}


# ---------------------------------------------------------------------------
# Chain state machine + stuck-ticket recovery (ADR-0010)
#
# Agents run their own loops; these tools govern the edges. Refusals come
# back as {"status": "refused", ...} and are logged to runs/events.jsonl.
# Human-only actions (clear a veto, resolve an escalation, override a close)
# are deliberately NOT exposed over MCP; they live in scripts/ticket.py
# behind operator approval.
# ---------------------------------------------------------------------------


def _chain_store():
    _events_module()  # puts scripts/ on sys.path
    import chain

    ticket_file = Path(os.environ.get("TICKET_FILE", RUNS_DIR / "in_review.json"))
    return chain, chain.Store(ticket_file, VERDICT_LOG, _event_log())


def _chain_call(fn) -> dict[str, Any]:
    chain, _ = _chain_store()
    try:
        return fn()
    except chain.Refused as e:
        return {"status": "refused", "reason": str(e)}
    except chain.CommitPending as e:
        return {"status": "pending", "reason": str(e), "next": "Do not retry; the change applies on the next call."}
    except chain.integrity.KeyRequired as e:
        return {"status": "error", "error": str(e)}
    except chain.integrity.TamperDetected as e:
        return {"status": "tampered", "reason": str(e),
                "next": "All writes are stopped until an operator runs `ticket.py verify` and `ticket.py integrity accept`."}
    except (KeyError, ValueError) as e:
        return {"status": "error", "error": str(e).strip("'")}


@mcp.tool()
def ticket_create(title: str, stage: str = "research", team: str = "", end_stage: str = "", agent_id: str = "", agent_token: str = "") -> dict[str, Any]:
    """Queue a new ticket for the chain (research > pm > ux > engineer > qa).

    Args:
        title: what needs doing.
        stage: first stage (default research). A stage outside the chain makes
            a single-stage ticket.
        team: team that owns it. Only that team's agents can claim it.
        end_stage: last chain stage (default qa).
        agent_id: self-reported id of the caller.
    """
    _, store = _chain_store()
    return _chain_call(lambda: {"status": "created", "ticket": store.create(
        title, stage, team, queued=True, end_stage=end_stage or None, agent=agent_id or None,
        token=agent_token or None, require_token=True)})


@mcp.tool()
def ticket_claim_next(role: str, team: str = "", agent_id: str = "", mode: str = "work", agent_token: str = "") -> dict[str, Any]:
    """Claim the oldest ticket for your stage and team. Runs stuck-ticket
    recovery first. mode="work" claims queued work; mode="review" claims work
    awaiting review (never your own). The claim holds a lease; call
    ticket_heartbeat to extend it or it returns to the queue.

    mode="work": the ticket carries ``lastVerdict`` after any verdict, so a
    worker reclaiming a kicked-back ticket reads the reasons there.
    mode="review": the ticket carries ``submission.deliverable`` (the work).
    Review is blind: the worker's summary and earlier verdicts are removed.

    When the operator has registered agents (ADR-0011), pass agent_token (or
    start this server with AG_AGENT_TOKEN set). The token decides your id,
    team, and allowed stages; agent_id and team may then be left empty."""
    _, store = _chain_store()

    def go():
        t = store.claim_next(role, team, agent_id or None, mode, token=agent_token or None)
        return {"status": "claimed", "ticket": t} if t else {"status": "empty", "role": role, "team": team, "mode": mode}
    return _chain_call(go)


@mcp.tool()
def ticket_heartbeat(ticket: str, agent_id: str = "", agent_token: str = "") -> dict[str, Any]:
    """Extend the lease on a ticket you hold."""
    _, store = _chain_store()
    return _chain_call(lambda: {"status": "ok", "lease_expires_at": store.heartbeat(ticket, agent_id or None, token=agent_token or None)["leaseExpiresAt"]})


@mcp.tool()
def ticket_submit(ticket: str, agent_id: str = "", summary: str = "", agent_token: str = "", deliverable: str = "") -> dict[str, Any]:
    """Submit work you claimed for review. Only the claimant can submit.

    Args:
        summary: one line on what you did.
        deliverable: the work itself (text, up to 64K characters) or a path or
            URL to it. The reviewer reads it from the ticket, so put the actual
            output here, not a description of it.
    """
    _, store = _chain_store()
    return _chain_call(lambda: {"status": "submitted", "ticket": store.submit(
        ticket, agent_id or None, summary, token=agent_token or None, deliverable=deliverable)})


@mcp.tool()
def ticket_verdict(ticket: str, verdict: str, agent_id: str = "", veto_hits: str = "", summary: str = "", to_stage: str = "", agent_token: str = "") -> dict[str, Any]:
    """Record a review verdict on a ticket and move it along the chain.

    PASS advances to the next stage (or closes on the last). KICK_BACK requeues
    this stage, or an earlier one via to_stage. Any veto hit blocks the ticket
    until a human clears it. ESCALATE / REVIEW_REQUIRED hand it to a human.
    You must hold the review claim (ticket_claim_next mode="review") and pass
    your agent_id. The worker cannot review its own ticket.
    """
    _, store = _chain_store()
    hits = [h.strip() for h in veto_hits.split(",") if h.strip()]
    return _chain_call(lambda: {"status": "recorded", "ticket": store.verdict(
        ticket, verdict, agent_id or None, hits, to_stage=to_stage or None, summary=summary,
        token=agent_token or None)})


@mcp.tool()
def ticket_recover() -> dict[str, Any]:
    """Run stuck-ticket recovery now: release expired claims, escalate repeat
    failures, and report stalled queues. Safe to call on a schedule."""
    _, store = _chain_store()
    return _chain_call(lambda: {"status": "ok", "events": store.recover()})


@mcp.tool()
def ticket_verify() -> dict[str, Any]:
    """Read-only integrity check (ADR-0012): walks the hash-chained event log
    and compares the ticket store with the last signed commit."""
    chain, store = _chain_store()
    key = chain.integrity.load_key()
    with chain.events.file_lock(store.ticket_file):  # never race an honest commit
        report = chain.integrity.verify_log(store.event_log, key)
        try:
            head = chain.integrity.read_head(store.head_file, key) or {}
        except chain.integrity.TamperDetected as e:
            head = {}
            report["head"] = str(e)
        try:
            store.check_integrity(repair=False)
            report["store"] = "matches last commit"
            store_ok = True
        except chain.integrity.TamperDetected as e:
            report["store"] = str(e)
            store_ok = False
    open_problems = chain.integrity.unaccepted(report["problems"], head.get("accepted_problems"))
    report["accepted_problems"] = [p for p in report["problems"] if p not in open_problems]
    report["problems"] = open_problems
    report["ok"] = store_ok and not open_problems and "head" not in report
    report["mode"] = "keyed" if key else "unkeyed"
    return report


@mcp.tool()
def ticket_list(team: str = "", state: str = "") -> list[dict[str, Any]]:
    """List tickets, optionally filtered by team and state. Shown blind
    (no worker summaries or verdict reasons), since any agent can call it."""
    chain_mod, store = _chain_store()
    rows = store.load()
    if team:
        rows = [t for t in rows if t.get("team") == team]
    if state:
        rows = [t for t in rows if t.get("state") == state]
    return [chain_mod.review_view(t) for t in rows]


@mcp.tool()
def framework_status() -> dict[str, Any]:
    """Return a health summary of the framework: domains, agent/skill counts, verdict log size."""
    return {
        "root": str(REPO_ROOT),
        "domains": DOMAINS,
        "agents_per_domain": {d: len(_agents_for(d)) for d in DOMAINS},
        "skills_per_domain": {d: len(_skills_for(d)) for d in DOMAINS},
        "verdict_log": str(VERDICT_LOG),
        "verdict_count": sum(1 for _ in VERDICT_LOG.open() if _.strip()) if VERDICT_LOG.exists() else 0,
        "spend": spend_meter.spend_status(REPO_ROOT),
        "version": update_check.CURRENT_VERSION,
    }


@mcp.tool()
def get_version() -> dict[str, Any]:
    """Return the framework's own version (single source of truth)."""
    return {
        "version": update_check.CURRENT_VERSION,
        "changelog_url": update_check.CHANGELOG_URL,
        "releases_url": update_check.RELEASES_URL,
    }


@mcp.tool()
def check_updates(force: bool = False) -> dict[str, Any]:
    """Check whether a newer framework version is published.

    Opt-in: only runs when the operator explicitly enabled update checks
    (AG_UPDATE_CHECK=allow, or "## Update checks" / "- allow" in
    config/setup.md) AND their network permission is "allow". Otherwise
    returns checked=False with a reason. Results are cached for 24h unless
    force=True. Never raises.
    """
    return update_check.check_for_updates(force=force, repo_root=REPO_ROOT)


LOOPBACK_BIND_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


def _normalize_bind_host(host: str) -> str:
    h = (host or "").strip().lower()
    if h.startswith("[") and h.endswith("]"):
        return h[1:-1]
    return h


def is_loopback_bind(host: str) -> bool:
    """True for 127.0.0.1, ::1, and localhost (bracketed IPv6 accepted)."""
    return _normalize_bind_host(host) in LOOPBACK_BIND_HOSTS


def http_auth_token() -> str:
    """Non-empty MCP_AUTH_TOKEN, or empty string if unset or whitespace."""
    return os.environ.get("MCP_AUTH_TOKEN", "").strip()


def refuse_http_without_token(host: str, token: str) -> bool:
    """True when HTTP must not start: token missing and bind is off loopback."""
    return not token and not is_loopback_bind(host)


def refuse_http_with_agent_token() -> bool:
    """True when a shared HTTP server would inherit one agent's identity.

    AG_AGENT_TOKEN as a server-side fallback is meant for stdio, where each
    agent host runs its own server process. On HTTP it would let every
    caller act as that agent."""
    return bool(os.environ.get("AG_AGENT_TOKEN"))


def bearer_token_matches(authorization: str, token: str) -> bool:
    """Constant-time compare of Authorization against Bearer <token>."""
    expected = f"Bearer {token}".encode("utf-8")
    provided = authorization.encode("utf-8")
    if len(provided) != len(expected):
        hmac.compare_digest(expected, expected)
        return False
    return hmac.compare_digest(provided, expected)


def main() -> None:
    """Run the MCP server.

    Transport defaults to stdio (the standard for MCP clients). For remote
    deployments, pass --transport streamable-http (and optionally --port /
    --mount-path) to expose the server over HTTP.
    """
    import argparse
    ap = argparse.ArgumentParser(description="Adversarial MCP server")
    ap.add_argument("--transport", choices=["stdio", "sse", "streamable-http"],
                    default="stdio", help="MCP transport (default stdio)")
    ap.add_argument("--port", type=int, default=8000, help="HTTP port (streamable-http/sse)")
    ap.add_argument("--mount-path", default="/mcp", help="HTTP mount path (streamable-http/sse)")
    ap.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP bind address (default 127.0.0.1). Use --host 0.0.0.0 only when "
             "you intentionally expose the server on the LAN; that requires "
             "MCP_AUTH_TOKEN and prints a warning.",
    )
    args = ap.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
        return

    # streamable-http / sse: run the server over HTTP. FastMCP's run()
    # with a non-stdio transport serves the server on the given port.
    import sys
    import uvicorn

    if refuse_http_with_agent_token():
        print(
            "ERROR: AG_AGENT_TOKEN is set for an HTTP server. Every caller would act "
            "as that one agent. Unset it; HTTP callers pass agent_token per call (ADR-0011).",
            file=sys.stderr,
        )
        raise SystemExit(2)

    # HTTP transport: require a bearer token off loopback. Loopback may omit
    # MCP_AUTH_TOKEN only with a loud warning. Non-loopback without a token
    # is refused (0.0.0.0 / :: and any other non-loopback bind).
    auth_token = http_auth_token()
    if refuse_http_without_token(args.host, auth_token):
        print(
            "ERROR: MCP_AUTH_TOKEN is required when the HTTP transport binds "
            f"off loopback (host={args.host}). Set a non-empty MCP_AUTH_TOKEN "
            "or bind 127.0.0.1, ::1, or localhost.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if not auth_token:
        print(
            "WARNING: MCP_AUTH_TOKEN is unset. HTTP transport is bound to "
            f"{args.host} without a bearer token. Set MCP_AUTH_TOKEN for any "
            "shared or remote use.",
            file=sys.stderr,
        )

    app = mcp.streamable_http_app() if args.transport == "streamable-http" else mcp.sse_app()
    if auth_token:
        app = _auth_middleware(app, auth_token)
    if not is_loopback_bind(args.host):
        print(
            "WARNING: binding MCP HTTP transport to "
            f"{args.host} exposes it on a non-loopback interface (LAN/WAN "
            "reachable if the host is). Prefer 127.0.0.1 behind a reverse proxy.",
            file=sys.stderr,
        )
    uvicorn.run(app, host=args.host, port=args.port)


def _auth_middleware(app, token: str):
    """Wrap an ASGI app with bearer-token auth and optional rate limiting.

    Every request must carry `Authorization: Bearer <token>`. Requests without
    a valid token get 401. When MCP_RATE_LIMIT is set (requests per minute per
    IP), requests over the limit get 429. This is a lightweight gate for remote
    deployments; it does not replace a full auth layer (e.g. mTLS or an API
    gateway) for production.
    """
    rate_limit = int(os.environ.get("MCP_RATE_LIMIT", "0"))  # 0 = disabled
    # per-IP sliding window: {ip: [timestamps]}
    hits: dict[str, list[float]] = {}

    async def auth_app(scope, receive, send):
        if scope["type"] != "http":
            await app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        auth = headers.get(b"authorization", b"").decode("utf-8", "ignore")
        if not bearer_token_matches(auth, token):
            await send({
                "type": "http.response.start",
                "status": 401,
                "headers": [(b"content-type", b"text/plain")],
            })
            await send({"type": "http.response.body", "body": b"unauthorized"})
            return
        # Rate limit per client IP (best-effort; behind a proxy use X-Forwarded-For).
        if rate_limit > 0:
            ip = scope.get("client", ("unknown", 0))[0]
            now = time.time()
            window = hits.setdefault(ip, [])
            window[:] = [t for t in window if now - t < 60]
            if len(window) >= rate_limit:
                await send({
                    "type": "http.response.start",
                    "status": 429,
                    "headers": [(b"content-type", b"text/plain")],
                })
                await send({"type": "http.response.body", "body": b"rate limited"})
                return
            window.append(now)
        await app(scope, receive, send)

    return auth_app


if __name__ == "__main__":
    main()
