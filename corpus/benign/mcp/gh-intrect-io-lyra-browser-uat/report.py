"""``report.json``: one shape for every brain, assembled from the run's files.

Nothing in here comes from the model's memory. The trace is ``trace.jsonl``,
findings and verdicts are ``events.jsonl``, approved sends come from the
browser's own audit log, and the outcome is whatever ``finish`` said — or
``unknown`` when it was never called, which the report says plainly.
"""

from __future__ import annotations

import json
import os
import platform
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .. import __version__
from .spec import Persona, PriorFinding, RunSpec, Severity, Verdict

SCHEMA_VERSION = "1"

RunStatus = Literal["completed", "incomplete", "error"]
ExitReason = Literal[
    "finish",
    "budget_exhausted",
    "wall_timeout",
    "brain_error",
    "browser_error",
    "harness_exit",
    "hook_failed",
    "no_finish",
    "interrupted",
]
OutcomeStatus = Literal["reached_goal", "partial", "blocked", "unknown"]

# Audit capabilities that are side effects worth a line in the ledger.
_SIDE_EFFECT_CAPABILITIES = {
    "submit": "submits",
    "upload": "uploads",
    "download": "downloads",
    "publish": "publishes",
}


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RunInfo(Model):
    id: str
    started_at: str
    finished_at: str
    duration_s: float
    status: RunStatus
    exit_reason: ExitReason
    lyra_browser_version: str = __version__
    host: str = ""


class TargetInfo(Model):
    trusted_origins: list[str]
    trusted_send_origins: list[str]
    proxy: bool


class BrainInfo(Model):
    backend: str
    model: str | None = None
    turns: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float | None = None
    session_id: str | None = None
    exit_code: int | None = None
    error: str | None = None


class OutcomeInfo(Model):
    status: OutcomeStatus
    summary: str = ""
    steps_used: int
    step_budget: int
    attempts: int


class TraceStep(Model):
    n: int
    ts: str
    tool: str
    args: dict[str, Any]
    status: str
    action: bool
    counted: bool
    system: bool
    url_before: str
    url_after: str
    result_head: str
    screenshot: str | None = None
    duration_ms: int = 0
    error: bool = False


class Finding(Model):
    id: str
    severity: Severity
    url: str
    step: int | None
    expected: str
    actual: str
    evidence: list[str]
    reported_at: str


class VerdictRow(Model):
    finding_id: str
    status: Verdict
    evidence: str
    step: int
    prior: PriorFinding | None = None


class Note(Model):
    step: int
    ts: str
    text: str


class PolicyEvent(Model):
    step: int
    kind: str
    detail: str
    ts: str


class Policy(Model):
    enforced: list[str]
    prompt_only: list[str]
    events: list[PolicyEvent]


class SideEffect(Model):
    ts: str
    tool: str
    capability: str
    origin: str | None = None
    consent_channel: str | None = None


class SideEffects(Model):
    """Approved sends, uploads, downloads and publishes from the browser's audit
    log — what a ledger of production writes starts from. A grant is an approval
    to send, so cross-check with the trace step that spent it."""

    submits: list[SideEffect] = Field(default_factory=list)
    uploads: list[SideEffect] = Field(default_factory=list)
    downloads: list[SideEffect] = Field(default_factory=list)
    publishes: list[SideEffect] = Field(default_factory=list)


class Observations(Model):
    network_file: str | None = None
    console_file: str | None = None
    counts: dict[str, int] = Field(default_factory=dict)
    matched: list[dict[str, Any]] = Field(default_factory=list)
    pages: int = 0
    # What the server knows about the browser it drove: profile_mode ("shared" or
    # "instance"), driver, channel, observer_errors.
    browser: dict[str, Any] = Field(default_factory=dict)


class Metrics(Model):
    """How the persona moved, from the trace: what it did, not what it said."""

    actions_by_tool: dict[str, int] = Field(default_factory=dict)
    clicks: int = 0
    direct_navigations: int = 0


class HookResult(Model):
    cmd: str
    exit_code: int | None
    stdout_tail: str = ""
    stderr_tail: str = ""
    duration_s: float = 0.0
    timed_out: bool = False


class Hooks(Model):
    before: HookResult | None = None
    after: HookResult | None = None


class Artifacts(Model):
    dir: str
    captures_dir: str
    audit_log: str
    trace_file: str
    events_file: str
    run_file: str | None = None
    report_json: str | None = None
    report_md: str | None = None


class Report(Model):
    schema_version: str = SCHEMA_VERSION
    run: RunInfo
    target: TargetInfo
    persona: Persona
    brain: BrainInfo
    outcome: OutcomeInfo
    trace: list[TraceStep]
    findings: list[Finding]
    verdicts: list[VerdictRow]
    what_worked: list[str]
    purchase_path: list[str]
    notes: list[Note]
    side_effects: SideEffects
    policy: Policy
    observations: Observations | None = None
    metrics: Metrics = Field(default_factory=Metrics)
    warnings: list[str] = Field(default_factory=list)
    hooks: Hooks
    artifacts: Artifacts

    def severity_counts(self) -> dict[str, int]:
        counts = Counter(f.severity for f in self.findings)
        return {s: counts.get(s, 0) for s in ("blocker", "major", "minor")}

    def one_line(self) -> str:
        sev = self.severity_counts()
        verdicts = Counter(v.status for v in self.verdicts)
        parts = [
            f"{self.persona.id}: {self.outcome.status}",
            f"run {self.run.status}/{self.run.exit_reason}",
            f"steps {self.outcome.steps_used}/{self.outcome.step_budget}",
            f"findings {len(self.findings)} (B{sev['blocker']} M{sev['major']} m{sev['minor']})",
        ]
        if self.verdicts:
            parts.append(
                "verdicts "
                + " ".join(
                    f"{k}={verdicts[k]}" for k in ("FIXED", "STILL_THERE", "COULD_NOT_CHECK")
                )
            )
        parts.append(f"brain {self.brain.backend}/{self.brain.model or '-'}")
        return " | ".join(parts)


# --- reading the run's files ----------------------------------------------------------


def _rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue  # a line cut by a crash: everything before it still counts
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _side_effects(audit_path: Path) -> SideEffects:
    effects = SideEffects()
    for row in _rows(audit_path):
        args = row.get("args") or {}
        capability = args.get("capability") if isinstance(args, dict) else None
        if row.get("status") != "allowed" or capability not in _SIDE_EFFECT_CAPABILITIES:
            continue
        bucket = getattr(effects, _SIDE_EFFECT_CAPABILITIES[capability])
        bucket.append(
            SideEffect(
                ts=str(row.get("ts", "")),
                tool=str(row.get("tool", "")),
                capability=str(capability),
                origin=row.get("origin"),
                consent_channel=args.get("consent_channel"),
            )
        )
    return effects


def enforced_policies(spec: RunSpec) -> list[str]:
    """What the server, not the prompt, guarantees for this run."""
    rules = [
        f"step_budget={spec.persona.step_budget} (actions beyond it are refused)",
        *(
            [
                "consent=autonomous (any site may be navigated to; a declared SUBMIT/UPLOAD/"
                "DOWNLOAD is approved and audited as autonomous; PUBLISH and file:/data: "
                "are refused)"
            ]
            if spec.target.policy == "autonomous"
            else [
                "trusted_origins (navigation outside the target is refused; nobody can approve it)",
                "consent=elicit (the model's confirm=true is not an approval)",
            ]
        ),
        *(
            [f"deny_origins={spec.target.deny_origins} (refused whatever else says yes)"]
            if spec.target.deny_origins
            else []
        ),
        "card_number_input (a value that looks like a payment card is never typed)",
    ]
    if spec.persona.uploads_allowed_dir is not None:
        rules.append(f"uploads_allowed_dir={spec.persona.uploads_allowed_dir}")
    else:
        rules.append("no uploads (upload_file is not offered)")
    if spec.target.policy == "autonomous":
        rules.append("DOWNLOAD and UPLOAD are approved when declared; PUBLISH is refused")
    elif spec.target.trusted_send_origins:
        rules.append("sends only on trusted_send_origins; PUBLISH and DOWNLOAD are refused")
    else:
        rules.append("no sends (SUBMIT/UPLOAD are refused everywhere)")
    return rules


def build_report(
    spec: RunSpec,
    run_dir: Path,
    *,
    run_id: str,
    started_at: datetime,
    finished_at: datetime,
    brain: BrainInfo,
    hooks: Hooks,
    audit_path: Path,
    exit_reason: ExitReason | None = None,
    observations: dict[str, Any] | None = None,
    run_file: Path | None = None,
) -> Report:
    """Assemble the report from what the run wrote. ``exit_reason`` is what the
    runner knows (a timeout, a crashed brain); a ``finish`` on disk outranks it."""
    trace = [TraceStep.model_validate(row) for row in _rows(run_dir / "trace.jsonl")]
    events = _rows(run_dir / "events.jsonl")
    priors = {p.id: p for p in spec.prior_findings}

    findings = [
        Finding(
            id=str(e["id"]),
            severity=e.get("severity", "minor"),
            url=str(e.get("url", "")),
            step=e.get("at_step"),
            expected=str(e.get("expected", "")),
            actual=str(e.get("actual", "")),
            evidence=[str(x) for x in e.get("evidence", [])],
            reported_at=str(e.get("ts", "")),
        )
        for e in events
        if e.get("type") == "finding"
    ]
    # One verdict per finding: the last call wins, as the tool promises.
    verdict_rows: dict[str, VerdictRow] = {}
    for e in events:
        if e.get("type") == "verdict":
            fid = str(e["finding_id"])
            verdict_rows[fid] = VerdictRow(
                finding_id=fid,
                status=e["status"],
                evidence=str(e.get("evidence", "")),
                step=int(e.get("step", 0)),
                prior=priors.get(fid),
            )
    notes = [
        Note(step=int(e.get("step", 0)), ts=str(e.get("ts", "")), text=str(e.get("text", "")))
        for e in events
        if e.get("type") == "note"
    ]
    policy_events = [
        PolicyEvent(
            step=int(e.get("step", 0)),
            kind=str(e.get("kind", "")),
            detail=str(e.get("detail", "")),
            ts=str(e.get("ts", "")),
        )
        for e in events
        if e.get("type") == "policy"
    ]
    finish = next((e for e in reversed(events) if e.get("type") == "finish"), None)

    steps_used = sum(1 for s in trace if s.counted)
    if finish is not None:
        status: RunStatus = "completed"
        reason: ExitReason = "finish"
    else:
        if exit_reason is None or exit_reason == "finish":
            budget_hit = any(p.kind == "budget_exhausted" for p in policy_events)
            reason = "budget_exhausted" if budget_hit else "no_finish"
        else:
            reason = exit_reason
        status = (
            "error" if reason in ("brain_error", "browser_error", "hook_failed") else "incomplete"
        )

    counted = Counter(s.tool for s in trace if s.counted)
    metrics = Metrics(
        actions_by_tool=dict(sorted(counted.items())),
        clicks=counted.get("click", 0),
        direct_navigations=counted.get("navigate", 0),
    )
    observations_model = Observations.model_validate(observations) if observations else None
    warnings: list[str] = []
    browser = observations_model.browser if observations_model else {}
    if spec.persona.account == "preseeded" and browser.get("profile_mode") == "instance":
        # Another browser held the profile the login lives in, and the server stepped
        # aside to an empty one. Whatever this persona saw, it saw as a stranger: the run
        # is not evidence about the signed-in experience, finish or not.
        warnings.append(
            "preseeded persona ran in an empty instance profile (the shared profile was held "
            "by another browser): it was not signed in; the run is invalid"
        )
        status, reason = "error", "browser_error"
    if browser.get("observer_errors"):
        warnings.append(
            "page observers failed to attach on some tabs; network and console records may be "
            f"incomplete: {browser['observer_errors'][:3]}"
        )
    if metrics.direct_navigations and not metrics.clicks:
        warnings.append(
            f"the persona moved by URL ({metrics.direct_navigations} navigate) and never "
            "clicked: broken links and buttons cannot have been found by this run"
        )
    if finish is None and not trace:
        warnings.append("no tool call was recorded: this is not a clean run")

    captures_dir = run_dir / "captures"
    return Report(
        run=RunInfo(
            id=run_id,
            started_at=started_at.isoformat(timespec="seconds"),
            finished_at=finished_at.isoformat(timespec="seconds"),
            duration_s=round((finished_at - started_at).total_seconds(), 1),
            status=status,
            exit_reason=reason,
            host=platform.node(),
        ),
        target=TargetInfo(
            trusted_origins=spec.all_trusted_origins(),
            trusted_send_origins=list(spec.target.trusted_send_origins),
            proxy=spec.target.proxy is not None,
        ),
        persona=spec.persona,
        brain=brain,
        outcome=OutcomeInfo(
            status=finish["outcome"] if finish else "unknown",
            summary=str(finish.get("summary", "")) if finish else "",
            steps_used=steps_used,
            step_budget=spec.persona.step_budget,
            attempts=len(trace),
        ),
        trace=trace,
        findings=findings,
        verdicts=list(verdict_rows.values()),
        what_worked=[str(x) for x in (finish or {}).get("what_worked", [])],
        purchase_path=[str(x) for x in (finish or {}).get("purchase_path", [])],
        notes=notes,
        side_effects=_side_effects(audit_path),
        policy=Policy(
            enforced=enforced_policies(spec),
            prompt_only=list(spec.persona.must_not),
            events=policy_events,
        ),
        observations=observations_model,
        metrics=metrics,
        warnings=warnings,
        hooks=hooks,
        artifacts=Artifacts(
            dir=str(run_dir),
            captures_dir=str(captures_dir),
            audit_log=str(audit_path),
            trace_file=str(run_dir / "trace.jsonl"),
            events_file=str(run_dir / "events.jsonl"),
            run_file=str(run_file) if run_file else None,
        ),
    )


# --- writing -------------------------------------------------------------------------


def _write_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".part")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_report(report: Report, run_dir: Path) -> tuple[Path, Path]:
    """``report.json`` and ``report.md``, written whole or not at all."""
    json_path = run_dir / "report.json"
    md_path = run_dir / "report.md"
    report.artifacts.report_json = str(json_path)
    report.artifacts.report_md = str(md_path)
    _write_atomic(json_path, report.model_dump_json(indent=2, exclude_none=False))
    _write_atomic(md_path, render_markdown(report))
    return json_path, md_path


# --- rendering -----------------------------------------------------------------------

_ARG_OF = {
    "navigate": "url",
    "click": "selector",
    "type_text": "selector",
    "hover": "selector",
    "select_option": "selector",
    "upload_file": "selector",
    "read_image": "selector",
    "press_key": "key",
    "wait_for": "text",
}


def _short_args(step: TraceStep) -> str:
    key = _ARG_OF.get(step.tool)
    if key and key in step.args:
        return f"{key}={step.args[key]!s}"[:90]
    if not step.args:
        return ""
    text = json.dumps(step.args, ensure_ascii=False, default=str)
    return text if len(text) <= 90 else text[:87] + "..."


def render_markdown(report: Report) -> str:
    p, o, r = report.persona, report.outcome, report.run
    lines = [
        f"# {p.id} — {p.name}",
        "",
        f"Outcome: **{o.status}** · run {r.status} ({r.exit_reason}) · "
        f"steps {o.steps_used}/{o.step_budget} ({o.attempts} calls) · {r.duration_s}s",
        f"Brain: {report.brain.backend}"
        + (f" / {report.brain.model}" if report.brain.model else "")
        + f" · turns {report.brain.turns} · tokens in {report.brain.input_tokens}"
        + f" (cache {report.brain.cache_read_tokens}) out {report.brain.output_tokens}"
        + (f" · ${report.brain.cost_usd:.4f}" if report.brain.cost_usd is not None else ""),
        f"Entry: {p.entry_url} · {p.viewport} · {p.locale} · account {p.account}",
    ]
    if report.warnings:
        lines += ["", "**Warnings**", ""] + [f"- {w}" for w in report.warnings]
    if o.summary:
        lines += ["", o.summary]
    if report.brain.error:
        lines += ["", f"Brain error: {report.brain.error}"]
    if report.metrics.actions_by_tool:
        moves = ", ".join(f"{k} {v}" for k, v in report.metrics.actions_by_tool.items())
        lines += ["", f"Actions: {moves}"]

    lines += ["", "## Trace", ""]
    for s in report.trace:
        flags = []
        if s.system:
            flags.append("free")
        if s.action and not s.counted and not s.system:
            flags.append("not counted")
        flag = f" ({', '.join(flags)})" if flags else ""
        shot = f" [{s.screenshot}]" if s.screenshot else ""
        where = s.url_after or s.url_before
        lines.append(f"{s.n}. `{s.tool}` {_short_args(s)} → {s.status}{flag} — {where}{shot}")

    lines += ["", "## Findings", ""]
    if report.findings:
        for f in report.findings:
            evidence = f" Evidence: {'; '.join(f.evidence)}" if f.evidence else ""
            step = f" step {f.step}" if f.step is not None else ""
            lines.append(
                f"- **[{f.severity}]** {f.id} {f.url}{step}: expected {f.expected or '—'}, "
                f"got {f.actual}.{evidence}"
            )
    else:
        lines.append(
            "- none reported" + ("" if report.trace else " (and no trace: not a clean run)")
        )

    if report.verdicts:
        lines += [
            "",
            "## Verdicts on earlier findings",
            "",
            "| finding | verdict | evidence |",
            "|---|---|---|",
        ]
        for v in report.verdicts:
            what = f" — {v.prior.actual}" if v.prior else ""
            lines.append(f"| {v.finding_id}{what} | {v.status} | {v.evidence} |")

    if report.what_worked:
        lines += ["", "## What worked", ""] + [f"- {w}" for w in report.what_worked]
    if report.purchase_path:
        lines += ["", "## Purchase path", ""] + [
            f"{i}. {w}" for i, w in enumerate(report.purchase_path, 1)
        ]
    if report.notes:
        lines += ["", "## Notes", ""] + [f"- (step {n.step}) {n.text}" for n in report.notes]

    if report.policy.events:
        lines += ["", "## Policy events", ""] + [
            f"- step {e.step}: {e.kind} — {e.detail}" for e in report.policy.events
        ]
    effects = report.side_effects
    if any((effects.submits, effects.uploads, effects.downloads, effects.publishes)):
        lines += ["", "## Approved sends (ledger draft)", ""]
        for name in ("submits", "uploads", "downloads", "publishes"):
            for e in getattr(effects, name):
                lines.append(
                    f"- {e.ts} {e.tool} {e.capability} on {e.origin or '?'} ({e.consent_channel})"
                )
    if report.observations:
        c = report.observations.counts
        lines += [
            "",
            "## Observations",
            "",
            f"- requests {c.get('requests', 0)}, failed {c.get('failed', 0)}, "
            f"http errors {c.get('http_errors', 0)}, console errors {c.get('console_errors', 0)}, "
            f"page errors {c.get('page_errors', 0)}",
        ]
        for m in report.observations.matched:
            lines.append(f"- matched `{m.get('pattern')}`: {m.get('count')}")
    for name in ("before", "after"):
        hook = getattr(report.hooks, name)
        if hook is not None:
            tail = hook.stdout_tail.strip().splitlines()
            last = tail[-1] if tail else ""
            lines += [
                "",
                f"Hook {name}: `{hook.cmd}` exit {hook.exit_code}" + (f" — {last}" if last else ""),
            ]
    lines += ["", "## Artifacts", "", f"- {report.artifacts.dir}"]
    return "\n".join(lines) + "\n"
