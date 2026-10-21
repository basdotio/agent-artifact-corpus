"""Deterministic rollup of llm_alerts.jsonl into a derived cluster view.

Pure Python, no LLM: exact (source, severity, digit-masked-reason) grouping
alone collapses repeated alerts that differ only in numbers or hex
identifiers into one group.
The rollup is ADDITIVE-ONLY: llm_alerts.jsonl and anything that reads it are
untouched; this writes a separate derived file consumers may PREFER but
never depend on. Counts and exemplars are code-computed; exemplar lines are
quoted byte-verbatim (never paraphrased -- alert lines may contain
identifiers and URLs that must survive exactly).

Import surface: write_rollup(alerts_path, out_path). CLI: py alert_digest.py.
"""

import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

_SEV_RANK = {"high": 0, "medium": 1, "low": 2}
_DEFAULT_WINDOW_DAYS = 3
_EXEMPLAR_MAX = 500

_HEX_RE = re.compile(r"\b[0-9a-f]{8,}\b", re.IGNORECASE)
_NUM_RE = re.compile(r"\d+(?:\.\d+)?")
_WS_RE = re.compile(r"\s+")


def reason_class(reason):
    """Digit/hex-masked, whitespace-collapsed normalization of a reason string.
    'HTTP 429 error at 15:31' and 'HTTP 429 error at 15:35' share a class."""
    masked = _HEX_RE.sub("#", str(reason or ""))
    masked = _NUM_RE.sub("#", masked)
    return _WS_RE.sub(" ", masked).strip()


def _parse_ts(raw):
    """Parse an ISO timestamp; None when unparseable (caller fails OPEN --
    an unparseable timestamp keeps the record in the window, never drops it)."""
    try:
        return datetime.fromisoformat(str(raw))
    except (ValueError, TypeError):
        return None


def build_rollup(alerts_path, window_days=_DEFAULT_WINDOW_DAYS, now=None):
    """Group the window's alert records into clusters. Returns the rollup dict.
    Malformed lines are counted, never fatal. Missing file -> empty rollup."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)
    groups = {}
    total = 0
    malformed = 0

    if os.path.isfile(alerts_path):
        with open(alerts_path, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    rec = json.loads(raw_line)
                except ValueError:
                    malformed += 1
                    continue
                if not isinstance(rec, dict):
                    malformed += 1
                    continue
                ts = _parse_ts(rec.get("timestamp"))
                if ts is not None and ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts is not None and ts < cutoff:
                    continue
                total += 1
                source = str(rec.get("source", ""))
                severity = str(rec.get("severity", "high")).lower()
                if severity not in _SEV_RANK:
                    severity = "high"
                cls = reason_class(rec.get("reason"))
                key = (source, severity, cls)
                grp = groups.get(key)
                ts_iso = ts.isoformat() if ts else None
                if grp is None:
                    groups[key] = grp = {
                        "source": source,
                        "severity": severity,
                        "reason_class": cls,
                        "count": 0,
                        "first_seen": ts_iso,
                        "last_seen": ts_iso,
                        "reasons": Counter(),
                        "exemplar_line": "",
                    }
                grp["count"] += 1
                if ts_iso:
                    if grp["first_seen"] is None or ts_iso < grp["first_seen"]:
                        grp["first_seen"] = ts_iso
                    if grp["last_seen"] is None or ts_iso > grp["last_seen"]:
                        grp["last_seen"] = ts_iso
                grp["reasons"][str(rec.get("reason", ""))] += 1
                line = str(rec.get("line", ""))
                if line:
                    if len(line) > _EXEMPLAR_MAX:
                        # Explicit marker -- never a silent cut posing as verbatim.
                        line = line[:_EXEMPLAR_MAX] + " ...[TRUNCATED]"
                    grp["exemplar_line"] = line

    out_groups = []
    for grp in groups.values():
        # Label = the MODAL verbatim reason string -- a real observed reason,
        # never a generated paraphrase.
        label, _ = grp["reasons"].most_common(1)[0]
        out_groups.append({
            "source": grp["source"],
            "severity": grp["severity"],
            "label": label,
            "reason_class": grp["reason_class"],
            "count": grp["count"],
            "first_seen": grp["first_seen"],
            "last_seen": grp["last_seen"],
            "exemplar_line": grp["exemplar_line"],
        })
    out_groups.sort(key=lambda g: (_SEV_RANK.get(g["severity"], 0), -g["count"]))

    return {
        "schema": "llm-alerts-rollup-v1",
        "generated_at": now.isoformat(),
        "window_days": window_days,
        "records_in_window": total,
        "group_count": len(out_groups),
        "malformed_lines": malformed,
        "groups": out_groups,
    }


def write_rollup(alerts_path, out_path, window_days=_DEFAULT_WINDOW_DAYS,
                 logger=None):
    """Build and atomically write the rollup (tmp + os.replace, matching the
    loop's offsets discipline). Returns the rollup dict."""
    rollup = build_rollup(alerts_path, window_days=window_days)
    parent = os.path.dirname(out_path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(rollup, handle, indent=2)
    os.replace(tmp, out_path)
    if logger:
        logger.info(
            "Alert rollup: %d record(s) -> %d group(s) (window %dd) -> %s",
            rollup["records_in_window"], rollup["group_count"],
            window_days, out_path)
    return rollup


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    alerts = os.path.join(script_dir, "state", "llm_alerts.jsonl")
    out = os.path.join(script_dir, "state", "llm_alerts_rollup.json")
    rollup = write_rollup(alerts, out)
    print("records_in_window=%d groups=%d -> %s"
          % (rollup["records_in_window"], rollup["group_count"], out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
