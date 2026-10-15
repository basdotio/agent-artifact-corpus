"""Replay verification — the feature nothing else in the landscape does.

Given an old ledger, re-run every recorded call against the same downstream
servers and report what changed.

    "This figure used GEO as of 2026-03-01.
     3 of 12 queries now return different data."

That is the reproducibility claim. Everything else in provmcp exists to make this
possible.

Honest scoping: a difference here means the downstream data changed, the server
changed, or the call was nondeterministic. Replay separates the third by
re-running twice; it cannot separate the first two without a source release
string, which is why sources.py tries to capture one.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .config import Config
from .downstream import Downstreams, error_payload, hash_result
from .ledger import Entry, Ledger
from .sources import resolve_release


class Verdict(StrEnum):
    MATCH = "match"                # identical result hash
    CHANGED = "changed"            # upstream data moved
    NONDETERMINISTIC = "flaky"     # differs between two fresh runs of the same call
    UNAVAILABLE = "unavailable"    # server not configured, or arguments were redacted
    ERROR = "error"                # replay itself failed


@dataclass
class ReplayResult:
    seq: int
    server_id: str
    tool: str
    verdict: Verdict
    original_hash: str
    current_hash: str | None
    original_release: str | None
    current_release: str | None
    detail: str = ""


def _redacted(arguments: dict) -> bool:
    from .proxy import REDACTED

    return any(v == REDACTED for v in arguments.values())


async def replay_entry(
    entry: Entry, downstreams: Downstreams, config: Config, *, double_run: bool = True
) -> ReplayResult:
    """Re-execute one recorded call.

    double_run re-executes a second time when the first run disagrees with the
    ledger, so nondeterminism is separated from genuine upstream change. Without
    that, a flaky tool reads as changed data — the exact false alarm that would
    make this tool untrustworthy.
    """
    base = dict(
        seq=entry.seq, server_id=entry.server_id, tool=entry.tool,
        original_hash=entry.result_hash, current_hash=None,
        original_release=entry.source_release, current_release=None,
    )
    server = config.by_id(entry.server_id)
    if server is None or entry.server_id not in downstreams.clients:
        return ReplayResult(**base, verdict=Verdict.UNAVAILABLE,
                            detail=f"server {entry.server_id!r} not in config")
    if _redacted(entry.arguments):
        return ReplayResult(**base, verdict=Verdict.UNAVAILABLE,
                            detail="arguments were redacted at record time")

    async def run_once() -> tuple[str, dict, str | None]:
        try:
            _, result_json, _ = await downstreams.call(entry.server_id, entry.tool, entry.arguments)
            return hash_result(result_json), result_json, None
        except Exception as exc:
            payload = error_payload(exc)
            return hash_result(payload), payload, payload["error"]

    first_hash, first_json, first_err = await run_once()
    release = await resolve_release(server.source, server.source_options, first_json)
    base["current_hash"], base["current_release"] = first_hash, release

    if first_hash == entry.result_hash:
        return ReplayResult(**base, verdict=Verdict.MATCH)

    if first_err is not None and entry.error is None:
        return ReplayResult(**base, verdict=Verdict.ERROR, detail=first_err)

    if double_run:
        second_hash, _, _ = await run_once()
        if second_hash != first_hash:
            return ReplayResult(**base, verdict=Verdict.NONDETERMINISTIC,
                                detail="two fresh runs disagree with each other")

    return ReplayResult(**base, verdict=Verdict.CHANGED)


async def replay_ledger(
    ledger: Ledger, config: Config, *, double_run: bool = True
) -> list[ReplayResult]:
    entries = list(ledger.entries())
    needed = {e.server_id for e in entries}
    servers = [s for s in config.servers if s.id in needed]
    results: list[ReplayResult] = []
    async with Downstreams(servers, config.server_log_dir) as ds:
        for entry in entries:
            results.append(await replay_entry(entry, ds, config, double_run=double_run))
    return results


def summarize(results: list[ReplayResult]) -> str:
    counts: dict[Verdict, int] = {}
    for r in results:
        counts[r.verdict] = counts.get(r.verdict, 0) + 1

    total = len(results)
    changed = counts.get(Verdict.CHANGED, 0)
    lines = [f"{total} recorded calls replayed"]

    if changed:
        lines.append(f"  {changed} of {total} now return different data:")
        for r in results:
            if r.verdict is Verdict.CHANGED:
                rel = ""
                if r.original_release or r.current_release:
                    rel = f"  [{r.original_release or '?'} -> {r.current_release or '?'}]"
                lines.append(f"    seq {r.seq:<4} {r.server_id}__{r.tool}{rel}")
    elif total:
        lines.append("  all results reproduce")

    for verdict in (Verdict.NONDETERMINISTIC, Verdict.UNAVAILABLE, Verdict.ERROR):
        n = counts.get(verdict, 0)
        if n:
            lines.append(f"  {n} {verdict.value}:")
            for r in results:
                if r.verdict is verdict:
                    lines.append(f"    seq {r.seq:<4} {r.server_id}__{r.tool}  {r.detail}")

    return "\n".join(lines)
