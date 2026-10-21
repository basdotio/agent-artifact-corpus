"""The observation oracle.

Reads backend truth. Never trusts an agent's success string, and never imports
the server's transition logic — expected effects are read from the store.

`undetermined` is deliberately a first-class outcome. The comparison must be able
to say "I could not tell" without that collapsing into "they agreed".
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from reference.backend import Compensation, IssueStore, OperationIdentity

__all__ = ["EffectObservation", "EffectState", "ReadBack"]

EffectState = Literal["not_applied", "applied", "partial", "unknown"]


def result_matches_effect(state: EffectState, ids: tuple[int, ...], result: str | None) -> bool:
    """Check the bounded reference application's durable result format."""
    if state == "applied":
        return len(ids) == 1 and result in {
            f"created {ids[0]}",
            f"created {ids[0]} with watcher",
        }
    if state == "partial":
        return len(ids) == 1 and result in {
            f"partial {ids[0]}; watcher failed; rollback succeeded",
            f"partial {ids[0]}; watcher failed; rollback failed",
        }
    return result is None


@dataclass(frozen=True, slots=True)
class EffectObservation:
    """Fresh evidence about whether an effect landed, within a declared scope."""

    identity: OperationIdentity
    observed_at: str
    authoritative: bool
    scope: str
    state: EffectState
    matching_ids: tuple[int, ...]
    detail: str = ""
    stored_result: str | None = None
    scope_binding: OperationIdentity | None = None

    @property
    def effects(self) -> int:
        return len(self.matching_ids)


class ReadBack:
    """Independent read-back over the store. Read-only: it never writes."""

    def __init__(
        self,
        store: IssueStore,
        *,
        principal: str = "test-principal",
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._principal = principal
        self._now = now or (lambda: datetime.now(UTC))

    def _identity(self, operation_id: str) -> OperationIdentity:
        if not operation_id:
            raise ValueError("operation_id must be non-empty")
        return OperationIdentity(operation_id, self._principal, self._store.backend_id)

    def _observed_at(self) -> str:
        return self._now().isoformat()

    def observe_by_title(self, title: str, *, operation_id: str) -> EffectObservation:
        """Observation scope: issues carrying this exact title.

        `state` reports presence; `effects` carries the count, so a duplicate
        (the protocol's finding) is visible via `effects` without corrupting
        the presence/absence axis.
        """
        matches = self._store.issues_with_title(title)
        ids = tuple(i.id for i in matches)
        state: EffectState = "not_applied" if not ids else "applied"
        scope = f"issue.title == {title!r}"
        detail = f"{len(ids)} issue(s) matching title"
        return EffectObservation(
            identity=self._identity(operation_id),
            observed_at=self._observed_at(),
            authoritative=False,
            scope=scope,
            state=state,
            matching_ids=ids,
            detail=detail,
        )

    def observe_by_body(self, body: str, *, operation_id: str) -> EffectObservation:
        """Observation scope: issues carrying this exact body."""
        matches = self._store.issues_with_body(body)
        ids = tuple(i.id for i in matches)
        state: EffectState = "not_applied" if not ids else "applied"
        scope = f"issue.body == {body!r}"
        detail = f"{len(ids)} issue(s) matching body"
        return EffectObservation(
            identity=self._identity(operation_id),
            observed_at=self._observed_at(),
            authoritative=False,
            scope=scope,
            state=state,
            matching_ids=ids,
            detail=detail,
        )

    def observe_issue_with_watcher(
        self, title: str, watcher: str, *, operation_id: str
    ) -> EffectObservation:
        """Case 12 scope: an issue exists but its watcher sub-effect did not land.

        `partial` is a first-class outcome here — the issue row is present, the
        watcher row is absent, and the observation says exactly that instead of
        collapsing into either `applied` or `not_applied`.
        """
        issues = self._store.issues_with_title(title)
        if not issues:
            return EffectObservation(
                identity=self._identity(operation_id),
                observed_at=self._observed_at(),
                authoritative=False,
                scope=f"issue.title == {title!r} + watcher {watcher!r}",
                state="not_applied",
                matching_ids=(),
                detail="no issue",
            )
        ids = tuple(i.id for i in issues)
        present_ids = tuple(
            issue_id
            for issue_id in ids
            if any(w.name == watcher for w in self._store.watchers_for(issue_id))
        )
        state: EffectState = "applied" if present_ids == ids else "partial"
        detail = f"issue(s) {ids}; watcher {watcher!r} present on {present_ids}"
        return EffectObservation(
            identity=self._identity(operation_id),
            observed_at=self._observed_at(),
            authoritative=False,
            scope=f"issue.title == {title!r} + watcher {watcher!r}",
            state=state,
            matching_ids=ids,
            detail=detail,
        )

    def reconcile_operation(self, identity: OperationIdentity) -> EffectObservation:
        """Observe a mediated operation by its complete reconciliation identity."""
        if identity.backend != self._store.backend_id:
            raise ValueError("reconciliation backend does not match the store")
        if identity.principal != self._principal:
            raise ValueError("reconciliation principal is outside the authorized read-back scope")
        record = self._store.operation_record(identity)
        if record is None:
            state: EffectState = "unknown"
            ids: tuple[int, ...] = ()
            detail = "no durable operation record; absence is not terminal non-application proof"
        elif (
            record.state == "applied"
            and record.effect_id is not None
            and self._store.get_issue(record.effect_id) is not None
        ):
            state = "applied"
            ids = (record.effect_id,)
            detail = "operation ledger and effect row are present"
        elif (
            record.state == "partial"
            and record.effect_id is not None
            and self._store.get_issue(record.effect_id) is not None
        ):
            state = "partial"
            ids = (record.effect_id,)
            detail = "operation ledger records a partial effect"
        else:
            state = "unknown"
            ids = ()
            detail = f"operation ledger state is {record.state!r}"
        return EffectObservation(
            identity=identity,
            observed_at=self._observed_at(),
            authoritative=True,
            scope=(
                f"operation_id={identity.operation_id!r}; principal={identity.principal!r}; "
                f"backend={identity.backend!r}"
            ),
            state=state,
            matching_ids=ids,
            detail=detail,
            stored_result=record.result
            if record is not None and state in {"applied", "partial"}
            else None,
            scope_binding=identity,
        )

    def compensations_for(self, issue_id: int) -> list[Compensation]:
        """Compensation rows for an issue — separate identities, never rewrites."""
        return self._store.compensations_for(issue_id)

    def total(self) -> int:
        """Total issue count. Used only as a cross-check, never as the primary read."""
        return self._store.count()
