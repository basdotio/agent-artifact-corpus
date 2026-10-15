"""Local lifecycle rules. External Agent contexts and exported copies are outside the vault."""
import hashlib
import json
from datetime import datetime, timezone

from .store import checked_text, checked_id, now


def metadata(value):
    if value is None:
        return {}
    if not isinstance(value, dict) or set(value) - {"scope", "valid_from", "valid_until", "state", "rationale", "conditions", "expected_outcome", "actual_outcome", "reviewed_at"}:
        raise ValueError("Invalid memory metadata")
    result = dict(value)
    for key in ("scope", "rationale", "conditions", "expected_outcome", "actual_outcome"):
        if key in result:
            checked_text(result[key], key, 5000)
    for key in ("valid_from", "valid_until", "reviewed_at"):
        if key in result:
            if not isinstance(result[key], str):
                raise ValueError("Dates must be ISO timestamps with a timezone")
            date = datetime.fromisoformat(result[key].replace("Z", "+00:00"))
            if date.tzinfo is None:
                raise ValueError("Dates must include a timezone")
            result[key] = date.astimezone(timezone.utc).isoformat()
    if result.get("state", "active") not in ("active", "inactive"):
        raise ValueError("Invalid memory state")
    if result.get("valid_from") and result.get("valid_until") and result["valid_from"] >= result["valid_until"]:
        raise ValueError("Validity end must be after start")
    return result


def effective(store, record, rows=None, seen=None):
    rows = {r["id"]: r for r in store._all()} if rows is None else rows
    seen = set() if seen is None else seen
    if record["id"] in seen:
        return "evidence_cycle"
    seen = seen | {record["id"]}
    if store._safe(store.meta / "revocations" / (record["id"] + ".json")).exists():
        return "revoked"
    m = record.get("memory", {})
    if m.get("state") == "inactive":
        return "inactive"
    stamp = datetime.now(timezone.utc)
    if m.get("valid_from") and stamp < datetime.fromisoformat(m["valid_from"]):
        return "not_yet_valid"
    if m.get("valid_until") and stamp >= datetime.fromisoformat(m["valid_until"]):
        return "expired"
    if record.get("claim_type") == "conflict" and not record.get("resolution"):
        return "unresolved_conflict"
    for sid in record.get("source_ids", []):
        source = rows.get(sid)
        if not source:
            return "evidence_missing"
        if record.get("source_revisions", {}).get(sid, source["revision"]) != source["revision"]:
            return "evidence_changed"
        if effective(store, source, rows, seen) != "active":
            return "evidence_inactive"
    return "active"


def active(store, record, rows=None):
    state = effective(store, record, rows)
    if state != "active":
        raise ValueError("Memory is unavailable for Agent use: " + state)


def change(store, record_id, action, sensitivity="private"):
    path = store._safe(store.meta / "changes.jsonl")
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []
    event = dict(sequence=(events[-1]["sequence"] if events else 0) + 1,
                 id=record_id, action=action, sensitivity=sensitivity, time=now())
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event) + "\n")


def changes(store, after=0, restricted=False):
    if type(after) is not int or after < 0:
        raise ValueError("Invalid change cursor")
    with store.locked():
        path = store._safe(store.meta / "changes.jsonl")
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []
        pending = [e for e in events if e["sequence"] > after][:100]
        # Later restriction also hides earlier notifications when polling from zero.
        restricted_ids = {e["id"] for e in events if e["sensitivity"] == "restricted"}
        visible = [{k: v for k, v in e.items() if k != "sensitivity"} for e in pending
                   if restricted or e["id"] not in restricted_ids]
        return dict(events=visible, cursor=pending[-1]["sequence"] if pending else after,
                    has_more=bool(pending and events[-1]["sequence"] > pending[-1]["sequence"]),
                    note="Invalidate your cached records and refetch. Already-read contexts, exports and old backups require external cleanup.")


def impact(store, record_id, restricted=True):
    root = store._get(record_id)
    current = list(store._all())
    artifacts = [*current]
    paths = list(store._safe(store.meta / "history").glob("*/*.md"))
    artifacts += [store.decode(store._safe(p).read_text(encoding="utf-8")) for p in paths]
    proposals = [(p, json.loads(store._safe(p).read_text(encoding="utf-8")))
                 for p in store._safe(store.meta / "proposals").glob("*.json")]
    artifacts += [p["record"] for _, p in proposals]
    ids = {record_id}
    while True:
        expanded = ids | {r["id"] for r in artifacts if set(r.get("source_ids", [])) & ids}
        if expanded == ids:
            break
        ids = expanded
    affected = [r for r in artifacts if r["id"] in ids]
    for r in affected:
        store._visible(r, restricted)
    fingerprint = hashlib.sha256(json.dumps(affected, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return root, current, affected, proposals, ids, fingerprint


def preview(store, record_id, restricted=False):
    with store.locked():
        root, current, affected, proposals, ids, fingerprint = impact(store, record_id, restricted)
        return dict(id=record_id, revision=root["revision"], impact=fingerprint,
                    records=[{"id": r["id"], "title": r["title"], "revision": r["revision"]} for r in current if r["id"] in ids],
                    affected_ids=sorted(ids), historical_versions=len(affected) - len([r for r in current if r["id"] in ids]),
                    proposals=sum(p["record"]["id"] in ids for _, p in proposals),
                    warning="本地删除不清除外部 Agent 上下文、已导出文件、旧备份或系统磁盘残留。")


def delete(store, record_id, revision, mode="source", expected_impact=None, restricted=True):
    if mode not in ("source", "deactivate", "purge"):
        raise ValueError("Invalid deletion mode")
    with store.locked():
        root, current, affected, proposals, ids, fingerprint = impact(store, record_id, restricted)
        if type(revision) is not int or root["revision"] != revision:
            raise ValueError("Revision conflict")
        if expected_impact is not None and fingerprint != expected_impact:
            raise ValueError("Deletion impact changed; preview again")
        if mode == "purge" and expected_impact is None:
            raise ValueError("Permanent deletion requires a current impact preview")
        targets = ids if mode == "purge" else {record_id}
        sensitivities = {rid: "restricted" if any(r["sensitivity"] == "restricted" for r in affected if r["id"] == rid) else "private" for rid in ids}
        # Revoke first: interrupted cleanup cannot expose the deleted evidence chain.
        for rid in targets:
            store._atomic(store.meta / "revocations" / (rid + ".json"), json.dumps(dict(id=rid, mode=mode, time=now())))
            change(store, rid, "purged" if mode == "purge" else "deleted", sensitivities[rid])
        for r in current:
            if r["id"] in targets:
                store._safe(store._path(r)).unlink()
            elif r["id"] in ids:
                if mode == "deactivate":
                    r["memory"] = {**r.get("memory", {}), "state": "inactive"}
                    r["revision"] += 1
                    r["updated_at"] = now()
                    store._save(r)
                change(store, r["id"], "evidence_invalidated", sensitivities[r["id"]])
        for path, p in proposals:
            if p["record"]["id"] in ids:
                if mode == "purge":
                    store._safe(path).unlink()
                elif p["state"] == "pending":
                    p["state"] = "invalidated"
                    store._atomic(path, json.dumps(p, ensure_ascii=False, indent=2))
        if mode == "purge":
            for rid in ids:
                directory = store._safe(store.meta / "history" / checked_id(rid))
                if directory.exists():
                    for p in directory.iterdir():
                        store._safe(p).unlink()
                    directory.rmdir()
        keys = {r.get("conversation", {}).get("key") for r in affected}
        for key in [*("source-" + rid for rid in ids), *(k for k in keys if k)]:
            store._safe(store.meta / "extraction" / (key + ".json")).unlink(missing_ok=True)
        store._audit("delete_" + mode, record_id)
        return dict(id=record_id, deleted=True, mode=mode, affected_ids=sorted(ids), history_retained=mode != "purge",
                    external_cleanup_required=True)
