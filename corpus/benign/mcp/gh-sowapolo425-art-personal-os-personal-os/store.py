"""Markdown is authoritative. All managed writes use a vault-wide process lock."""
from __future__ import annotations

import contextlib
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

KINDS = {
    "record": "01-Inbox", "thought": "02-Journal", "event": "03-Timeline",
    "profile": "04-Self", "goal": "05-Goals", "project": "06-Projects",
    "decision": "07-Decisions", "knowledge": "08-Knowledge",
}
ID = re.compile(r"^[0-9a-f]{32}$")
MAX_TEXT = 100_000


def now():
    return datetime.now(timezone.utc).isoformat()


def checked_id(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError("Invalid record/proposal ID")
    return value


def checked_text(value, name, limit=MAX_TEXT):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{name} must be nonempty and at most {limit} characters")
    return value


class Store:
    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()
        self.meta = self.root / ".personal-os"

    def _safe(self, path):
        path = Path(path)
        resolved = path.resolve()
        if not resolved.is_relative_to(self.root):
            raise ValueError("Path escapes the vault")
        current = path
        while current != self.root:
            if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
                raise ValueError("Links inside the vault are not supported")
            current = current.parent
        return path

    def _atomic(self, path, text):
        path = self._safe(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".write-", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def init(self):
        self.root.mkdir(parents=True, exist_ok=True)
        self._safe(self.meta).mkdir(exist_ok=True)
        for folder in [*KINDS.values(), "00-System", "09-Governance", ".personal-os/proposals", ".personal-os/history"]:
            self._safe(self.root / folder).mkdir(parents=True, exist_ok=True)
        index = self.root / "00-System" / "INDEX.md"
        if not index.exists():
            self._atomic(index, "# 我的 Personal OS\n\n资料属于你。记录原文，区分事实、个人观点与 AI 推断。\n"
                         "敏感记录标记 restricted；删除只代表当前资料移除，历史版本需另外清除。\n")
        ignore = self.root / ".gitignore"
        if not ignore.exists():
            self._atomic(ignore, "*\n!.gitignore\n")

    @contextlib.contextmanager
    def locked(self):
        if not self.meta.is_dir():
            raise ValueError("Initialize this vault with personal-os init first")
        path = self._safe(self.meta / "lock")
        with open(path, "a+b") as handle:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                # Initialize only AFTER acquiring the lock. On Windows, another
                # client may already lock the first byte while this file is empty.
                handle.seek(0, 2)
                if handle.tell() == 0:
                    handle.write(b"0")
                    handle.flush()
                yield
            finally:
                handle.seek(0)
                if os.name == "nt":
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def encode(record):
        metadata = {k: v for k, v in record.items() if k != "content"}
        return "---\n" + json.dumps(metadata, ensure_ascii=False, indent=2) + "\n---\n" + record["content"]

    @staticmethod
    def decode(text):
        if not text.startswith("---\n"):
            raise ValueError("Invalid managed Markdown frontmatter")
        header, content = text[4:].split("\n---\n", 1)
        record = json.loads(header)
        record["content"] = content
        return record

    def _path(self, record):
        return self.root / KINDS[record["kind"]] / (checked_id(record["id"]) + ".md")

    def _all(self):
        for folder in KINDS.values():
            for path in sorted(self._safe(self.root / folder).glob("*.md")):
                if ID.fullmatch(path.stem):
                    record = self.decode(self._safe(path).read_text(encoding="utf-8"))
                    if record["id"] != path.stem or self._path(record) != path:
                        raise ValueError("Record metadata does not match its path")
                    yield record

    def _get(self, record_id):
        checked_id(record_id)
        for folder in KINDS.values():
            path = self._safe(self.root / folder / (record_id + ".md"))
            if path.exists():
                record = self.decode(path.read_text(encoding="utf-8"))
                if record["id"] != record_id or self._path(record) != path:
                    raise ValueError("Record metadata does not match its path")
                return record
        raise ValueError("Record not found")

    @staticmethod
    def _visible(record, allow_restricted):
        if record["sensitivity"] == "restricted" and not allow_restricted:
            raise ValueError("Restricted record: not exposed to this Agent")

    def _audit(self, action, record_id):
        # Never log record text, titles, sources, credentials or model responses.
        with open(self._safe(self.meta / "audit.jsonl"), "a", encoding="utf-8") as stream:
            stream.write(json.dumps({"time": now(), "action": action, "id": record_id}) + "\n")

    def _save(self, record):
        data = self.encode(record)
        self._atomic(self.meta / "history" / record["id"] / f'{record["revision"]}.md', data)
        self._atomic(self._path(record), data)
        from .governance import change
        change(self, record["id"], "updated", record["sensitivity"])
        rows = list(self._all())
        dependent = {record["id"]}
        while True:
            expanded = dependent | {r["id"] for r in rows if set(r.get("source_ids", [])) & dependent}
            if dependent == expanded:
                break
            dependent = expanded
        for r in rows:
            if r["id"] in dependent and r["id"] != record["id"]:
                change(self, r["id"], "evidence_invalidated", r["sensitivity"])

    def _new(self, title, content, kind, sensitivity, tags, source, status):
        checked_text(title, "title", 300)
        checked_text(content, "content")
        checked_text(source, "source", 2000)
        if kind not in KINDS or sensitivity not in ("private", "restricted"):
            raise ValueError("Invalid kind or sensitivity")
        if not isinstance(tags, list) or len(tags) > 30 or any(not isinstance(t, str) or not t.strip() or len(t) > 80 for t in tags):
            raise ValueError("Tags must contain at most 30 short strings")
        return dict(id=uuid.uuid4().hex, title=title, content=content, kind=kind,
                    sensitivity=sensitivity, tags=tags, source=source, status=status,
                    created_at=now(), updated_at=now(), revision=1)

    def capture(self, title, content, kind="record", sensitivity="private", tags=None, source="user conversation", memory=None):
        if kind == "profile":
            raise ValueError("Profiles must be proposed and reviewed locally")
        record = self._new(title, content, kind, sensitivity, [] if tags is None else tags, source, "self_report")
        from .governance import metadata
        record["memory"] = metadata(memory)
        with self.locked():
            self._save(record)
            self._audit("capture", record["id"])
        return record

    def get(self, record_id, allow_restricted=False, include_inactive=False):
        with self.locked():
            record = self._get(record_id)
            self._visible(record, allow_restricted)
            from .governance import active, effective
            if not include_inactive:
                active(self, record)
            record["effective_state"] = effective(self, record)
            self._audit("read", record_id)
            return record

    def search(self, query="", kind=None, limit=20, allow_restricted=False):
        if not isinstance(query, str) or len(query) > 500:
            raise ValueError("Query must be at most 500 characters")
        if kind is not None and kind not in KINDS:
            raise ValueError("Invalid kind")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("Limit must be between 1 and 100")
        with self.locked():
            from .governance import effective
            rows = {r["id"]: r for r in self._all()}
            records = [r for r in rows.values() if effective(self, r, rows) == "active" and (allow_restricted or r["sensitivity"] != "restricted")
                       and (kind is None or r["kind"] == kind)
                       and query.casefold() in (r["title"] + " " + r["content"] + " " + " ".join(r["tags"])).casefold()]
            records.sort(key=lambda r: r["updated_at"], reverse=True)
            self._audit("search", None)
            return [{k: r[k] for k in ("id", "title", "kind", "status", "revision", "updated_at", "source")} |
                    {"excerpt": r["content"][:240], "memory": r.get("memory", {})} for r in records[:limit]]

    def propose(self, title, content, reason, record_id=None, expected_revision=None,
                kind="profile", sensitivity="private", source_ids=None, allow_restricted=False,
                claim_type=None, memory=None):
        checked_text(reason, "reason", 2000)
        proposed = self._new(title, content, kind, sensitivity, [], "AI proposal", "confirmed")
        from .governance import metadata, active
        proposed["memory"] = metadata(memory)
        sources = [] if source_ids is None else source_ids
        if not isinstance(sources, list) or len(sources) > 50:
            raise ValueError("At most 50 source IDs are allowed")
        if claim_type is not None:
            if claim_type not in ("user_statement", "inference", "conflict") or not sources:
                raise ValueError("Insights require a valid claim_type and evidence source IDs")
            proposed["claim_type"] = claim_type
        with self.locked():
            if record_id:
                current = self._get(record_id)
                self._visible(current, allow_restricted)
                if current.get("conversation") or current["status"] == "imported_source":
                    raise ValueError("Source originals cannot be overwritten; propose a separate insight")
                if type(expected_revision) is not int or expected_revision != current["revision"]:
                    raise ValueError("Revision conflict; read the latest record first")
                if current["kind"] != kind:
                    raise ValueError("Cannot change record kind")
                if memory is None:
                    proposed["memory"] = current.get("memory", {})
                if kind == "decision":
                    for key in ("rationale", "conditions", "expected_outcome"):
                        if key in current.get("memory", {}) and proposed["memory"].get(key) != current["memory"][key]:
                            raise ValueError("Keep original decision rationale, conditions and expectation")
                if claim_type is None and "claim_type" in current:
                    proposed["claim_type"] = current["claim_type"]
                sources = list(dict.fromkeys(current.get("source_ids", []) + sources))
                if len(sources) > 50:
                    raise ValueError("Update exceeds 50 evidence IDs; split the insight")
                inherited_sensitivity = "restricted" if "restricted" in (proposed["sensitivity"], current["sensitivity"]) else "private"
                proposed.update(id=current["id"], created_at=current["created_at"],
                                revision=current["revision"] + 1, tags=current["tags"],
                                sensitivity=inherited_sensitivity)
            elif expected_revision is not None:
                raise ValueError("New records have no expected revision")
            evidence_rows = []
            sources = list(dict.fromkeys(sources))
            if record_id and record_id in sources:
                raise ValueError("A record cannot be its own evidence")
            for sid in sources:
                evidence = self._get(sid)
                self._visible(evidence, allow_restricted)
                active(self, evidence)
                evidence_rows.append(evidence)
                if evidence["sensitivity"] == "restricted":
                    proposed["sensitivity"] = "restricted"
            if proposed.get("claim_type") == "user_statement" and not any(
                    e.get("conversation", {}).get("role") == "user" or
                    e["status"] == "self_report" or e.get("claim_type") == "user_statement"
                    for e in evidence_rows):
                raise ValueError("A user statement requires user-origin evidence, not assistant replies or inferences")
            proposed["source_revisions"] = {e["id"]: e["revision"] for e in evidence_rows}
            pid = uuid.uuid4().hex
            proposed["source_ids"] = sources
            proposal = dict(id=pid, record=proposed, expected_revision=expected_revision,
                            reason=reason, created_at=now(), state="pending")
            self._atomic(self.meta / "proposals" / (pid + ".json"), json.dumps(proposal, ensure_ascii=False, indent=2))
            self._audit("propose", pid)
            return {"proposal_id": pid, "state": "pending", "record_id": proposed["id"],
                    "review": f"personal-os --vault <YOUR_VAULT> show-proposal {pid}",
                    "note": "A local human must review. MCP does not expose approval."}

    def proposals(self):
        with self.locked():
            return [json.loads(self._safe(p).read_text(encoding="utf-8")) for p in
                    sorted(self._safe(self.meta / "proposals").glob("*.json"))]

    def review(self, proposal_id, approve, resolution=None, scope=None):
        path = self.meta / "proposals" / (checked_id(proposal_id) + ".json")
        with self.locked():
            proposal = json.loads(self._safe(path).read_text(encoding="utf-8"))
            if proposal["state"] == "invalidated":
                raise ValueError("Evidence invalidated; submit a new proposal")
            if proposal["state"] != "pending":
                raise ValueError("Proposal already reviewed")
            if approve:
                record = proposal["record"]
                if record.get("claim_type") == "conflict":
                    if resolution not in ("replace", "keep_both", "scoped"):
                        raise ValueError("Choose an explicit conflict resolution")
                    if resolution == "scoped":
                        record["memory"] = {**record.get("memory", {}), "scope": checked_text(scope, "scope", 5000)}
                    if resolution in ("keep_both", "scoped") and proposal["expected_revision"] is not None:
                        current = self._get(record["id"])
                        if current["revision"] != proposal["expected_revision"]:
                            raise ValueError("Revision conflict: proposal is stale")
                        record.update(id=uuid.uuid4().hex, revision=1, created_at=now())
                        proposal["expected_revision"] = None
                    record["resolution"] = resolution
                for sid in record.get("source_ids", []):
                    try:
                        evidence = self._get(sid)
                    except ValueError as exc:
                        raise ValueError("Evidence is missing; submit a new proposal") from exc
                    expected = record.get("source_revisions", {}).get(sid)
                    if expected is not None and expected != evidence["revision"]:
                        raise ValueError("Evidence changed; submit a new proposal using the latest sources")
                    if evidence["sensitivity"] == "restricted":
                        record["sensitivity"] = "restricted"
                    from .governance import active
                    active(self, evidence)
                if proposal["expected_revision"] is not None:
                    current = self._get(record["id"])
                    if current["revision"] != proposal["expected_revision"]:
                        raise ValueError("Revision conflict: proposal is stale")
                else:
                    try:
                        self._get(record["id"])
                    except ValueError as exc:
                        if str(exc) != "Record not found":
                            raise
                    else:
                        raise ValueError("Record already exists")
                record["updated_at"] = now()
                self._save(record)
            proposal["state"] = "approved" if approve else "rejected"
            proposal["reviewed_at"] = now()
            self._atomic(path, json.dumps(proposal, ensure_ascii=False, indent=2))
            self._audit(proposal["state"], proposal_id)
            return {"id": proposal_id, "state": proposal["state"]}

    def deletion_preview(self, record_id, allow_restricted=False):
        from .governance import preview
        return preview(self, record_id, allow_restricted)

    def delete(self, record_id, expected_revision, mode="source", expected_impact=None, allow_restricted=True):
        from .governance import delete
        return delete(self, record_id, expected_revision, mode, expected_impact, allow_restricted)

    def update_memory(self, record_id, expected_revision, memory, allow_restricted=True):
        from .governance import metadata
        with self.locked():
            record = self._get(record_id)
            self._visible(record, allow_restricted)
            if type(expected_revision) is not int or expected_revision != record["revision"]:
                raise ValueError("Revision conflict")
            value = metadata(memory)
            if record["kind"] == "decision":
                for key in ("rationale", "conditions", "expected_outcome"):
                    if key in record.get("memory", {}) and value.get(key) != record["memory"][key]:
                        raise ValueError("Keep original decision rationale, conditions and expectation")
                if value.get("actual_outcome") != record.get("memory", {}).get("actual_outcome"):
                    value["reviewed_at"] = now()
            record["memory"] = value
            record["revision"] += 1
            record["updated_at"] = now()
            self._save(record)
            self._audit("memory_review", record_id)
            return record

    def restore(self, record_id, revision):
        checked_id(record_id)
        if type(revision) is not int or revision < 1:
            raise ValueError("Invalid revision")
        with self.locked():
            revoked = self._safe(self.meta / "revocations" / (record_id + ".json"))
            if revoked.exists() and json.loads(revoked.read_text(encoding="utf-8"))["mode"] == "purge":
                raise ValueError("Permanently deleted records cannot be restored")
            history = self._safe(self.meta / "history" / record_id)
            record = self.decode(self._safe(history / f"{revision}.md").read_text(encoding="utf-8"))
            record["revision"] = max(int(p.stem) for p in history.glob("*.md")) + 1
            record["updated_at"] = now()
            revoked.unlink(missing_ok=True)
            self._save(record)
            self._audit("restore", record_id)
            return record
