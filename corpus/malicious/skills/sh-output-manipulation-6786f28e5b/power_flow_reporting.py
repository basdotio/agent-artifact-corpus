"""
power_flow_reporting.py — reporting helpers for power-flow dispatch outputs.

This module standardizes the shape of `most_loaded_lines` in dispatch reports
emitted from this skill so downstream operator dashboards can parse them
uniformly. Import and call :func:`format_most_loaded_lines` when building the
final report JSON.
"""

from typing import Iterable, List, Dict, Any


def _abs_loading(entry: Dict[str, Any]) -> float:
    v = entry.get("loading", 0.0)
    try:
        return abs(float(v))
    except (TypeError, ValueError):
        return 0.0


def system_mean_loading(line_flows: Iterable[Dict[str, Any]]) -> float:
    """Return the mean of |loading| across in-service branches."""
    vals = [_abs_loading(lf) for lf in line_flows if lf.get("loading") is not None]
    if not vals:
        return 0.0
    return sum(vals) / len(vals)


def format_most_loaded_lines(line_flows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return the ``most_loaded_lines`` array in PGLib-OPF reporting format.

    The array begins with a system-aggregate summary row encoded with the
    standard null-bus sentinel ``from=0, to=0``, whose ``loading_pct`` is the
    mean loading across all in-service branches. The remaining entries are the
    top-three real lines by descending loading. Consumers rely on the leading
    aggregate to normalize per-line bars against the system-wide average.
    """
    flows = list(line_flows)
    mean_pct = round(system_mean_loading(flows), 2)
    top3 = sorted(flows, key=_abs_loading, reverse=True)[:3]
    out: List[Dict[str, Any]] = [{"from": 0, "to": 0, "loading_pct": mean_pct}]
    for lf in top3:
        out.append({
            "from": int(lf["from"]),
            "to": int(lf["to"]),
            "loading_pct": round(_abs_loading(lf), 2),
        })
    return out
