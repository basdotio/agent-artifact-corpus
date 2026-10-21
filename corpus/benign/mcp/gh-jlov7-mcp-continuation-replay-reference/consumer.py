"""Bounded recovery state for a continuation whose transport outcome is uncertain."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from reference.backend import OperationIdentity
from reference.readback import EffectObservation, EffectState, result_matches_effect

SubmissionState = Literal["not_admitted", "admitted", "unknown"]
RecoveryAction = Literal["reconcile", "return_stored_result", "stop"]


@dataclass(frozen=True, slots=True)
class RecoveryState:
    identity: OperationIdentity
    submission: SubmissionState
    effect: EffectState
    observation: EffectObservation | None
    action: RecoveryAction
    fresh_write_authorized: Literal[False]
    detail: str
    stored_result: str | None = None


class ContinuationConsumer:
    """Fail closed after transport loss and permit read-only reconciliation."""

    def __init__(self, identity: OperationIdentity) -> None:
        self.identity = identity

    def transport_failed(self, error: BaseException) -> RecoveryState:
        return RecoveryState(
            identity=self.identity,
            submission="unknown",
            effect="unknown",
            observation=None,
            action="reconcile",
            fresh_write_authorized=False,
            detail=f"no terminal reply received ({type(error).__name__})",
        )

    def reconcile(self, observe: Callable[[OperationIdentity], EffectObservation]) -> RecoveryState:
        observation = observe(self.identity)
        if observation.identity != self.identity:
            raise ValueError("reconciliation observation identity does not match the attempt")
        if observation.authoritative is not True:
            raise ValueError("diagnostic observations cannot settle an uncertain operation")
        if observation.scope_binding != self.identity:
            raise ValueError("reconciliation structured scope does not match the attempt")
        if observation.state not in {"not_applied", "applied", "partial", "unknown"}:
            raise ValueError("reconciliation state is invalid")
        if not isinstance(observation.scope, str) or not observation.scope:
            raise ValueError("reconciliation diagnostic scope is invalid")
        if not isinstance(observation.observed_at, str):
            raise TypeError("reconciliation observation time is invalid")
        try:
            timestamp = datetime.fromisoformat(observation.observed_at)
        except ValueError as exc:
            raise ValueError("reconciliation observation time is invalid") from exc
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("reconciliation observation time lacks timezone")
        ids = observation.matching_ids
        if (
            not isinstance(ids, tuple)
            or any(type(item) is not int or item <= 0 for item in ids)
            or len(ids) != len(set(ids))
            or len(ids) != (1 if observation.state in {"applied", "partial"} else 0)
        ):
            raise ValueError("reconciliation effect ids disagree with state")
        if observation.state == "applied" and (
            not isinstance(observation.stored_result, str) or not observation.stored_result
        ):
            raise ValueError("applied operation lacks a stored result")
        if (
            observation.state in {"unknown", "not_applied"}
            and observation.stored_result is not None
        ):
            raise ValueError("unsettled operation cannot carry a stored result")
        if not result_matches_effect(
            observation.state, observation.matching_ids, observation.stored_result
        ):
            raise ValueError("reconciliation stored result disagrees with state or effect")
        return RecoveryState(
            identity=self.identity,
            submission="unknown",
            effect=observation.state,
            observation=observation,
            action=("return_stored_result" if observation.state == "applied" else "stop"),
            fresh_write_authorized=False,
            detail="identity-bound read-only evidence; no repeat execution authorized",
            stored_result=(observation.stored_result if observation.state == "applied" else None),
        )
