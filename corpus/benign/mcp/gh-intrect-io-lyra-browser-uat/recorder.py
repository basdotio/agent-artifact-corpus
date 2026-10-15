"""The run's memory: every tool call, every finding, every refusal — on disk as it happens.

A persona run is only as trustworthy as its trace, and a trace the model is
asked to remember is not one. So the server records: ``UatMiddleware`` sits in
front of every tool call, numbers it, applies the persona's step budget and
the guards on what it must never do, takes a screenshot after each action, and
appends the result to ``trace.jsonl`` before the model sees it. Findings,
verdicts, notes, policy refusals and the final ``finish`` go to
``events.jsonl``. Both files are append-only JSON lines, written as they
happen, so a run cut off by a timeout or a crashed harness still has
everything up to that moment — and so a harness that drove this server as a
separate process leaves the same files for the report as our own loop does.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Awaitable, Callable
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools.tool import ToolResult
from mcp.types import TextContent

from ..audit import _redact as redact_args
from ..vision import payload_of
from .spec import UAT_TOOLS

ACTION_TOOLS: frozenset[str] = frozenset(
    {
        "navigate",
        "go_back",
        "reload_page",
        "click",
        "type_text",
        "press_key",
        "hover",
        "scroll",
        "select_option",
        "upload_file",
        "handle_dialog",
        "set_editor",
        "save_draft",
        "publish",
    }
)
"""Tools that spend a step of the persona's budget. ``tabs`` joins when it
switches or closes; listing is a read."""

_TAB_ACTIONS = frozenset({"switch", "close"})

NO_ATTEMPT: frozenset[str] = frozenset(
    {
        "not_found",
        "hidden",
        "disabled",
        "needs_approval",
        "session_conflict",
        "browser_unavailable",
        "browser_closed",
        "takeover_active",
        "unattended",
        "error",
        "budget_exhausted",
        "finished",
        "blocked_by_uat_policy",
    }
)
"""Statuses of an action that never reached the page. They are recorded but do
not spend the budget: a wrong selector is a mistake, not a step the persona took."""

RESULT_HEAD_CHARS = 300

_DIGIT_RUN = re.compile(r"(?:\d[ -]?){13,19}")


def luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def looks_like_card_number(text: str) -> bool:
    """A run of 13–19 digits (spaces or dashes allowed) that passes Luhn.

    Every persona brief says "never enter a card number"; this makes it a rule
    of the server rather than a hope about the model. Luhn keeps order numbers
    and phone numbers out of it most of the time.
    """
    for match in _DIGIT_RUN.finditer(text or ""):
        digits = re.sub(r"[ -]", "", match.group(0))
        if 13 <= len(digits) <= 19 and luhn_ok(digits):
            return True
    return False


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def _head(payload: Any) -> str:
    try:
        text = json.dumps(payload, ensure_ascii=False, default=str)
    except TypeError:
        text = str(payload)
    return text[:RESULT_HEAD_CHARS]


@dataclass(slots=True)
class Step:
    n: int
    ts: str
    tool: str
    args: dict[str, Any]
    action: bool
    system: bool = False
    status: str = ""
    counted: bool = False
    url_before: str = ""
    url_after: str = ""
    result_head: str = ""
    screenshot: str | None = None
    duration_ms: int = 0
    error: bool = False


class RunRecorder:
    """Keeps the run's state and writes it down as it changes."""

    def __init__(
        self,
        run_dir: Path,
        *,
        step_budget: int,
        entry_url: str,
        uploads_allowed_dir: Path | None = None,
        auto_screenshot: bool = True,
        prior_finding_ids: tuple[str, ...] | list[str] = (),
    ) -> None:
        self.run_dir = run_dir
        self.trace_path = run_dir / "trace.jsonl"
        self.events_path = run_dir / "events.jsonl"
        self.step_budget = step_budget
        self.entry_url = entry_url
        self.uploads_allowed_dir = (
            uploads_allowed_dir.expanduser().resolve() if uploads_allowed_dir else None
        )
        self.auto_screenshot = auto_screenshot
        self.prior_finding_ids = set(prior_finding_ids)
        # Set by the server builder: takes a screenshot without going through the
        # middleware (``screenshot`` tool's raw function), so a step's own capture
        # is not a step.
        self.screenshot: Callable[[], Awaitable[dict]] | None = None
        # Set by the server builder: the run's network/console observers, flushed
        # after every step so their files keep pace with the trace.
        self.observers: Any | None = None
        # Set by the server builder: what is known of the browser itself (profile
        # mode, driver, observer failures), merged into observations.json.
        self.browser_info: Callable[[], dict[str, Any]] | None = None

        self.steps: list[Step] = []
        self.steps_used = 0
        self.attempts = 0
        self.finding_count = 0
        self.verdicts: dict[str, str] = {}
        self.finished = False
        self.last_url = ""
        self._entry_done = False
        self._system_depth = 0
        self._started = time.monotonic()
        run_dir.mkdir(parents=True, exist_ok=True)

    # --- classification ---------------------------------------------------------

    @staticmethod
    def is_action(tool: str, args: dict[str, Any]) -> bool:
        if tool == "tabs":
            return str(args.get("action", "list")) in _TAB_ACTIONS
        return tool in ACTION_TOOLS

    @contextmanager
    def system(self):
        """Calls made by the runner itself: recorded, never budgeted."""
        self._system_depth += 1
        try:
            yield
        finally:
            self._system_depth -= 1

    def _is_free_entry(self, tool: str, args: dict[str, Any]) -> bool:
        """The persona's first move onto its entry URL is given, not spent."""
        return tool == "navigate" and not self._entry_done and args.get("url") == self.entry_url

    # --- guards -----------------------------------------------------------------

    def guard(self, tool: str, args: dict[str, Any]) -> dict | None:
        """The envelope that stands in for the call, or None to let it through."""
        if tool in UAT_TOOLS:
            return None
        if self.finished:
            return {
                "status": "finished",
                "reason": "finish was already called; the run is over.",
            }
        if self._system_depth:
            return None
        action = self.is_action(tool, args)
        if action and not self._is_free_entry(tool, args) and self.steps_used >= self.step_budget:
            self.policy_event(
                "budget_exhausted",
                f"{tool} refused: {self.steps_used}/{self.step_budget} steps used",
            )
            return {
                "status": "budget_exhausted",
                "steps_used": self.steps_used,
                "step_budget": self.step_budget,
                "reason": "The persona's step budget is spent.",
                "hint": (
                    "Reading tools still work. Report any remaining findings with "
                    "report_finding, then call finish with the outcome so far."
                ),
            }
        if tool in ("type_text", "set_editor"):
            typed = args.get("value") if tool == "type_text" else args.get("content")
            if isinstance(typed, str) and looks_like_card_number(typed):
                self.policy_event(
                    "guard_blocked_input", f"{tool}: value looks like a payment card number"
                )
                return {
                    "status": "blocked_by_uat_policy",
                    "reason": "The value looks like a payment card number; a persona never "
                    "enters one. Record what the checkout asked for and move on.",
                }
        if tool == "upload_file":
            outside = self._paths_outside_allowed(args.get("paths") or [])
            if outside:
                self.policy_event(
                    "guard_blocked_input", f"upload_file: outside allowed dir {outside}"
                )
                return {
                    "status": "blocked_by_uat_policy",
                    "reason": "Only files inside the persona's upload directory may be uploaded.",
                    "allowed_dir": str(self.uploads_allowed_dir)
                    if self.uploads_allowed_dir
                    else None,
                    "rejected": outside,
                }
        return None

    def _paths_outside_allowed(self, paths: list[Any]) -> list[str]:
        if self.uploads_allowed_dir is None:
            return [str(p) for p in paths]
        outside: list[str] = []
        for raw in paths:
            try:
                resolved = Path(str(raw)).expanduser().resolve()
                resolved.relative_to(self.uploads_allowed_dir)
            except (ValueError, OSError):
                outside.append(str(raw))
        return outside

    # --- steps ------------------------------------------------------------------

    def begin(self, tool: str, args: dict[str, Any]) -> Step:
        self.attempts += 1
        step = Step(
            n=len(self.steps) + 1,
            ts=_now(),
            tool=tool,
            args=redact_args(dict(args)),
            action=self.is_action(tool, args),
            system=bool(self._system_depth) or self._is_free_entry(tool, args),
            url_before=self.last_url,
        )
        step.duration_ms = int(time.monotonic() * 1000)  # start mark; replaced in complete()
        self.steps.append(step)
        return step

    def complete(
        self,
        step: Step,
        payload: Any,
        *,
        is_error: bool = False,
        screenshot: str | None = None,
    ) -> None:
        envelope = payload if isinstance(payload, dict) else {}
        status = str(envelope.get("status") or ("error" if is_error else "ok"))
        step.status = status
        step.error = is_error or status == "error"
        step.duration_ms = max(0, int(time.monotonic() * 1000) - step.duration_ms)
        step.result_head = _head(payload)
        step.screenshot = screenshot
        url = envelope.get("url")
        step.url_after = url if isinstance(url, str) and url else self.last_url
        self.last_url = step.url_after
        step.counted = step.action and not step.system and status not in NO_ATTEMPT
        if step.counted:
            self.steps_used += 1
        if step.tool == "navigate" and step.system and not self._entry_done and not step.error:
            self._entry_done = status not in NO_ATTEMPT
        self._append(self.trace_path, asdict(step))

    async def take_screenshot(self) -> str | None:
        """A capture for the trace. Never raises: a missing frame is not a failed step."""
        if self.screenshot is None:
            return None
        try:
            result = await self.screenshot()
        except Exception:  # noqa: BLE001 — evidence is best-effort
            return None
        path = result.get("image_path") if isinstance(result, dict) else None
        return str(path) if path else None

    # --- events -----------------------------------------------------------------

    def _append(self, path: Path, row: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

    def _event(self, event_type: str, **data: Any) -> dict[str, Any]:
        row = {"type": event_type, "ts": _now(), "step": len(self.steps), **data}
        self._append(self.events_path, row)
        return row

    def policy_event(self, kind: str, detail: str) -> None:
        self._event("policy", kind=kind, detail=detail)

    def add_finding(
        self,
        *,
        severity: str,
        url: str,
        step: int | None,
        expected: str,
        actual: str,
        evidence: list[str],
    ) -> str:
        self.finding_count += 1
        finding_id = f"F{self.finding_count}"
        self._event(
            "finding",
            id=finding_id,
            severity=severity,
            url=url,
            at_step=step,
            expected=expected,
            actual=actual,
            evidence=evidence,
        )
        return finding_id

    def add_verdict(self, *, finding_id: str, status: str, evidence: str) -> None:
        self.verdicts[finding_id] = status
        self._event("verdict", finding_id=finding_id, status=status, evidence=evidence)

    def add_note(self, text: str) -> None:
        self._event("note", text=text)

    def set_finish(
        self,
        *,
        outcome: str,
        summary: str,
        what_worked: list[str],
        purchase_path: list[str],
    ) -> None:
        self.finished = True
        self._event(
            "finish",
            outcome=outcome,
            summary=summary,
            what_worked=what_worked,
            purchase_path=purchase_path,
            steps_used=self.steps_used,
            step_budget=self.step_budget,
        )

    def write_observations(self) -> dict[str, Any] | None:
        """The observers' summary as ``observations.json``, rewritten after every
        step and at exit, so a server killed mid-run still leaves a current one."""
        if self.observers is None:
            return None
        summary = self.observers.summary()
        if self.browser_info is not None:
            try:
                summary["browser"] = self.browser_info()
            except Exception as exc:  # noqa: BLE001 — a report note, never a failed step
                summary["browser"] = {"error": f"{type(exc).__name__}: {exc}"}
        path = self.run_dir / "observations.json"
        tmp = path.with_name(path.name + ".part")
        tmp.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
        return summary

    def missing_verdicts(self) -> list[str]:
        return sorted(self.prior_finding_ids - set(self.verdicts))

    def summary(self) -> dict[str, Any]:
        return {
            "steps_used": self.steps_used,
            "step_budget": self.step_budget,
            "attempts": self.attempts,
            "findings": self.finding_count,
            "verdicts": len(self.verdicts),
            "finished": self.finished,
            "last_url": self.last_url,
            "elapsed_s": round(time.monotonic() - self._started, 1),
        }


def _refusal(envelope: dict) -> ToolResult:
    return ToolResult(
        content=[TextContent(type="text", text=json.dumps(envelope, ensure_ascii=False))],
        structured_content=envelope,
    )


class UatMiddleware(Middleware):
    """Numbers, guards, records and illustrates every tool call of a run."""

    def __init__(self, recorder: RunRecorder) -> None:
        self.recorder = recorder

    async def on_call_tool(self, context: MiddlewareContext, call_next) -> ToolResult:
        name = context.message.name
        args = dict(context.message.arguments or {})
        refusal = self.recorder.guard(name, args)
        if refusal is not None:
            step = self.recorder.begin(name, args)
            self.recorder.complete(step, refusal)
            return _refusal(refusal)
        step = self.recorder.begin(name, args)
        try:
            result = await call_next(context)
        except Exception as exc:
            self.recorder.complete(
                step, {"status": "error", "error": type(exc).__name__}, is_error=True
            )
            raise
        payload = payload_of(result)
        shot = None
        status = payload.get("status", "ok") if isinstance(payload, dict) else "ok"
        if step.action and self.recorder.auto_screenshot and status not in NO_ATTEMPT:
            shot = await self.recorder.take_screenshot()
        self.recorder.complete(step, payload, is_error=result.is_error, screenshot=shot)
        self.recorder.write_observations()
        return result
