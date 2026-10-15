"""Separate transport completion from Lean's mathematical result."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OperationOutcome:
    """A terminal or pending operation, including the unmodified server receipt."""

    operation: dict[str, Any]

    @property
    def terminal(self) -> bool:
        return self.operation.get("state") in {"completed", "failed", "cancelled"}

    @property
    def result(self) -> dict[str, Any] | None:
        envelope = self.operation.get("result")
        if not isinstance(envelope, dict):
            return None
        operation_id = self.operation.get("operation_id")
        revision = self.operation.get("revision")
        if (
            not isinstance(operation_id, str)
            or not operation_id.strip()
            or type(revision) is not int
            or revision < 0
            or envelope.get("operation_id") != operation_id
            or type(envelope.get("revision")) is not int
            or envelope["revision"] != revision
            or type(envelope.get("generation")) is not int
            or envelope["generation"] < 1
        ):
            return None
        result = envelope.get("result")
        return result if isinstance(result, dict) else None

    @property
    def verified(self) -> bool:
        result = self.result
        if not isinstance(result, dict):
            return False
        receipt = result.get("receipt")
        return (
            self.operation.get("kind") == "verify_target"
            and self.operation.get("state") == "completed"
            and result.get("status") == "ok"
            and isinstance(receipt, dict)
            and receipt.get("policy") == "fixed_target_kernel_check_v1"
        )

    @property
    def successful(self) -> bool:
        """Proof rejection and diagnostics do not become success through HTTP 200."""
        if self.operation.get("kind") == "verify_target":
            return self.verified
        result = self.result
        if self.operation.get("state") != "completed" or not isinstance(result, dict):
            return False
        kind = self.operation.get("kind")
        if kind == "inspect":
            # Goal availability is separate from whether the worker retained a
            # proof state. Older services expose only that retention status.
            goals = result.get("goal_contexts")
            return (
                result.get("status") in {"available", "proof_state", "metadata_only"}
                and ("goal_status" not in result or result["goal_status"] == "available")
                and isinstance(goals, list)
                and bool(goals)
                and all(
                    isinstance(goal, dict)
                    and isinstance(goal.get("target"), str)
                    and bool(goal["target"].strip())
                    for goal in goals
                )
            )
        if kind == "try_tactics":
            # A completed trial batch can contain unsuccessful candidate tactics.
            # This says nothing about whether the theorem has been proved.
            return isinstance(result.get("results"), list)
        return kind == "check" and result.get("status") == "ok"


def reported(operation: dict[str, Any]) -> dict[str, Any]:
    """Lead an operation with whether it passed: true, false, or null while running."""
    outcome = OperationOutcome(operation)
    return {"success": outcome.successful if outcome.terminal else None, **operation}
