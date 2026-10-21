"""Framework-visible spend metering and refuse-at-cap.

Honest limits
-------------
This module meters **only units that callers record** (for example one unit per
gated MCP deep-review). It does **not** observe model-provider tokens or
dollars (Claude, Cursor, OpenAI, etc.). Agents that never call these gated
entrypoints are unchecked.

The only hard **dollar** spend limit is at the operator's model-provider
billing console (and any OS/network controls they apply).

Cap source
----------
Reads numeric caps from ``config/setup.md`` written by the setup wizard:

- billed mode: ``total spend cap``
- metered mode: ``allowance per cycle`` (headroom is advisory text only here)

Usage is appended to ``runs/spend-ledger.jsonl``. When recorded usage is at or
over the configured cap, ``refuse_if_over_cap`` raises ``SpendCapExceeded``.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


SPEND_UNIT_QUALIFIER = (
    "This framework cannot see or limit what you spend with your model provider. "
    "Set a hard spending cap in your provider's billing console. "
    "This cap counts framework units only."
)


class SpendCapExceeded(RuntimeError):
    """Raised when recorded framework units meet or exceed the configured cap."""


def _repo_root() -> Path:
    return Path(os.environ.get("ADVERSARIAL_ROOT", Path(__file__).resolve().parents[2]))


def ledger_path(repo_root: Path | None = None) -> Path:
    root = repo_root or _repo_root()
    return root / "runs" / "spend-ledger.jsonl"


def setup_path(repo_root: Path | None = None) -> Path:
    root = repo_root or _repo_root()
    return root / "config" / "setup.md"


def parse_spend_config(repo_root: Path | None = None) -> dict[str, Any]:
    """Parse budget fields from config/setup.md.

    Returns keys: budget_model, cap (float|None), escalation_pct (float|None),
    headroom (float|None). Missing/unparseable → cap None (no refuse).
    """
    cfg: dict[str, Any] = {
        "budget_model": None,
        "cap": None,
        "escalation_pct": None,
        "headroom": None,
    }
    p = setup_path(repo_root)
    if not p.exists():
        return cfg
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except OSError:
        return cfg

    section = ""
    for line in lines:
        s = line.strip()
        if s.startswith("## "):
            section = s[3:].strip().lower()
            continue
        if not s.startswith("- "):
            continue
        body = s[2:].strip()
        if section == "budget model" and cfg["budget_model"] is None:
            if body in ("metered", "billed", "not-yet-known") or body == "(unset)":
                cfg["budget_model"] = None if body == "(unset)" else body
            continue
        if body.startswith("allowance per cycle:"):
            cfg["cap"] = _to_float(body.split(":", 1)[1])
        elif body.startswith("total spend cap:"):
            cfg["cap"] = _to_float(body.split(":", 1)[1])
        elif body.startswith("escalation threshold (% of cap):"):
            cfg["escalation_pct"] = _to_float(body.split(":", 1)[1])
        elif body.startswith("headroom reserved for in-flight work:"):
            cfg["headroom"] = _to_float(body.split(":", 1)[1])
        # Per-epic is advisory for CEO prompts; not a hard refuse here.
    return cfg


def _to_float(raw: str) -> float | None:
    text = (raw or "").strip()
    if not text or text == "(unset)":
        return None
    # allow "100" or "100 units" / "100%"
    token = text.split()[0].rstrip("%")
    try:
        return float(token)
    except ValueError:
        return None


def recorded_usage(repo_root: Path | None = None) -> float:
    """Sum ``units`` from the spend ledger. Missing file → 0."""
    path = ledger_path(repo_root)
    if not path.exists():
        return 0.0
    total = 0.0
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            try:
                total += float(row.get("units", 0) or 0)
            except (TypeError, ValueError):
                continue
    except OSError:
        return total
    return total


def record_usage(
    units: float,
    source: str,
    note: str = "",
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Append a usage row. Returns the row written."""
    root = repo_root or _repo_root()
    path = ledger_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": int(time.time() * 1000),
        "units": float(units),
        "source": source,
        "note": note,
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    _maybe_alert_threshold(root)
    return row


def _maybe_alert_threshold(repo_root: Path) -> None:
    """After-the-fact alert when usage crosses escalation threshold (advisory path)."""
    cfg = parse_spend_config(repo_root)
    cap = cfg.get("cap")
    pct = cfg.get("escalation_pct")
    if cap is None or pct is None or cap <= 0:
        return
    usage = recorded_usage(repo_root)
    threshold = cap * (pct / 100.0)
    if usage < threshold:
        return
    # Best-effort alert; never raise from alert failure.
    try:
        import sys

        scripts = str(repo_root / "scripts")
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        from messaging import send_alert  # type: ignore

        send_alert(
            f"AG spend threshold: recorded units {usage} crossed "
            f"{pct}% of cap {cap}. {SPEND_UNIT_QUALIFIER}"
        )
    except Exception:
        return


def refuse_if_over_cap(repo_root: Path | None = None, pending_units: float = 0.0) -> None:
    """Raise SpendCapExceeded if usage + pending would meet/exceed configured cap.

    If no numeric cap is configured (missing setup, not-yet-known, unparseable),
    this is a no-op — there is nothing enforceable to refuse against.
    """
    cfg = parse_spend_config(repo_root)
    cap = cfg.get("cap")
    if cap is None:
        return
    usage = recorded_usage(repo_root)
    if usage + pending_units >= cap:
        raise SpendCapExceeded(
            f"Framework spend cap reached: recorded={usage} pending={pending_units} "
            f"cap={cap}. {SPEND_UNIT_QUALIFIER} "
            "Refuse gated operation. Set a higher framework-unit ceiling in the wizard "
            "or clear runs/spend-ledger.jsonl after operator review."
        )


def spend_status(repo_root: Path | None = None) -> dict[str, Any]:
    """Snapshot for status tools / tests."""
    cfg = parse_spend_config(repo_root)
    usage = recorded_usage(repo_root)
    cap = cfg.get("cap")
    return {
        "budget_model": cfg.get("budget_model"),
        "cap": cap,
        "usage": usage,
        "remaining": None if cap is None else max(0.0, cap - usage),
        "qualifier": SPEND_UNIT_QUALIFIER,
        "enforcement": (
            "refuse_at_cap_for_recorded_framework_units"
            if cap is not None
            else "no_numeric_cap_configured"
        ),
        "provider_dollars_metered": False,
    }
