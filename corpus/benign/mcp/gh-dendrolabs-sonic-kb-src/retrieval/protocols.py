"""Protocol retrieval functions for sonic-kb."""

from __future__ import annotations

from ._loader import load_protocol, load_protocol_index
from ._resolver import resolve_def_refs


def get_protocol(protocol_id: str) -> dict | None:
    data = load_protocol(protocol_id)
    if data is None:
        return None
    return resolve_def_refs(data)


def get_protocol_state(protocol_id: str, state: str) -> dict | None:
    data = load_protocol(protocol_id)
    if data is None:
        return None
    state_upper = state.upper()
    for s in data.get("states", []):
        if s.get("name", "").upper() == state_upper:
            transitions_from = [
                t for t in data.get("transitions", [])
                if t.get("from_state", "").upper() == state_upper
            ]
            transitions_to = [
                t for t in data.get("transitions", [])
                if t.get("to_state", "").upper() == state_upper
            ]
            failures = [
                f for f in data.get("failure_modes", [])
                if state_upper in (f.get("scenario", "") + " ".join(f.get("symptoms", []))).upper()
            ]
            return {
                "state": s,
                "transitions_from": transitions_from,
                "transitions_to": transitions_to,
                "related_failures": failures,
            }
    return None


def get_protocol_failures(protocol_id: str, keyword: str | None = None,
                          state: str | None = None) -> list[dict]:
    data = load_protocol(protocol_id)
    if data is None:
        return []
    failures = data.get("failure_modes", [])
    if state:
        su = state.upper()
        failures = [
            f for f in failures
            if su in (f.get("scenario", "") + " ".join(f.get("symptoms", []))).upper()
        ]
    if keyword:
        kl = keyword.lower()
        failures = [
            f for f in failures
            if kl in (f.get("scenario", "") + f.get("description", "")).lower()
        ]
    return failures


def get_protocol_timers(protocol_id: str, name: str | None = None) -> list[dict]:
    data = load_protocol(protocol_id)
    if data is None:
        return []
    timers = data.get("timers", [])
    if name:
        nl = name.lower()
        timers = [t for t in timers if nl in t.get("name", "").lower()]
    return timers


def get_protocol_messages(protocol_id: str) -> list[dict]:
    data = load_protocol(protocol_id)
    if data is None:
        return []
    return data.get("messages", [])


def get_related_protocols(protocol_id: str) -> list[str]:
    data = load_protocol(protocol_id)
    if data is None:
        return []
    return data.get("related_protocols", [])


def search_protocols_by_tag(tag: str) -> list[dict]:
    index = load_protocol_index()
    tag_lower = tag.lower()
    results = []
    for proto_id, meta in index.items():
        tags = [t.lower() for t in meta.get("tags", [])]
        if tag_lower in tags:
            results.append({"protocol_id": proto_id, **meta})
    return results


def get_verify_commands(protocol_id: str, state: str | None = None,
                        failure: str | None = None) -> list[dict]:
    data = load_protocol(protocol_id)
    if data is None:
        return []
    commands = []
    if state:
        su = state.upper()
        for s in data.get("states", []):
            if s.get("name", "").upper() == su:
                for cmd in s.get("verify_commands", []):
                    if isinstance(cmd, str):
                        commands.append({"command": cmd})
                    else:
                        commands.append(cmd)
    if failure:
        fl = failure.lower()
        for fm in data.get("failure_modes", []):
            if fl in fm.get("scenario", "").lower():
                commands.extend(fm.get("verify_commands", []))
    if not state and not failure:
        for fm in data.get("failure_modes", []):
            commands.extend(fm.get("verify_commands", []))
    return commands
