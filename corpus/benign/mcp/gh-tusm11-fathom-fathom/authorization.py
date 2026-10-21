"""Authorization contract for managed execution."""

from enum import Enum
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, Field


class BlastRadius(str, Enum):
    """Risk category for a target system."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class BlastRadiusProvenance(str, Enum):
    """Source of blast radius assessment."""
    DECLARED = "declared"
    VERIFIED = "verified"


class ResultState(str, Enum):
    """Import from models to avoid circular dependency in VerificationCriteria."""
    CONSISTENT = "consistent"
    DIVERGENT = "divergent"
    INCONCLUSIVE = "inconclusive"


class VerificationCriteria(BaseModel):
    """What constitutes successful verification for a target."""
    all_tests_succeeded: bool = True  # All test cases must succeed
    no_errors_in_output: bool = True  # Response must not contain error markers
    decision_method_deterministic: bool = False  # Optional: require DETERMINISTIC, not MODEL_ASSISTED/HYBRID
    result_state_required: Optional[ResultState] = None  # If set, result must match (e.g., CONSISTENT)


class VerificationCriteria(BaseModel):
    """What constitutes successful verification for a target."""
    all_tests_succeeded: bool = True  # All test cases must succeed (not just no exception)
    no_errors_in_output: bool = True  # Response must not contain error markers (e.g., "ERROR", "FAILED")
    decision_method_deterministic: bool = False  # v1.2: optional—require DETERMINISTIC, not MODEL_ASSISTED/HYBRID
    result_state_required: Optional[ResultState] = None  # If set, result must match (e.g., CONSISTENT, not DIVERGENT)


class ExecutionAuthorization(BaseModel):
    """Permission contract for managed execution."""
    target_id: str
    blast_radius: BlastRadius
    blast_radius_provenance: BlastRadiusProvenance
    blast_radius_verified_at: Optional[datetime] = None
    blast_radius_reason: str
    verification_criteria: VerificationCriteria = Field(default_factory=VerificationCriteria)
    authorized_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    max_invocations: Optional[int] = None
    reason: str
    authorized_by: str

    def is_valid(self) -> tuple[bool, Optional[str]]:
        """Check if authorization is currently valid."""
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False, f"Authorization expired at {self.expires_at}"
        return True, None

    def is_safe_for_auto_invocation(self) -> tuple[bool, Optional[str]]:
        """Can this be safely auto-invoked by Fathom?"""
        if self.blast_radius == BlastRadius.UNKNOWN:
            return False, "Blast radius UNKNOWN treated as HIGH (not assessed); requires explicit override"

        if self.blast_radius in (BlastRadius.HIGH, BlastRadius.MEDIUM):
            return False, f"Blast radius {self.blast_radius.value} requires explicit override (require_safe=False)"

        if self.blast_radius_provenance == BlastRadiusProvenance.VERIFIED:
            return True, None

        return False, f"Blast radius {self.blast_radius.value} declared but not verified; requires explicit override on first invocation"


class AuthorizationScope(str, Enum):
    """What kind of access is being authorized (v1.2: retained for future use)."""
    DELEGATED_ONLY = "delegated_only"  # Plan only, caller runs
    MANAGED_READ_ONLY = "managed_read_only"  # Fathom invokes, but target can't modify state
    MANAGED_LIMITED = "managed_limited"  # Fathom invokes, limited side effects allowed
    MANAGED_FULL = "managed_full"  # Fathom invokes with full permissions (rare)


class AuthorizationStore:
    """In-memory authorization registry."""

    def __init__(self):
        self.authorizations: dict[str, ExecutionAuthorization] = {}
        self.invocation_count: dict[str, int] = {}  # Track invocations per target

    def authorize(self, auth: ExecutionAuthorization) -> None:
        """Register an authorization."""
        self.authorizations[auth.target_id] = auth
        self.invocation_count[auth.target_id] = 0

    def get_authorization(self, target_id: str) -> Optional[ExecutionAuthorization]:
        """Retrieve authorization for a target."""
        return self.authorizations.get(target_id)

    def check_authorization(
        self,
        target_id: str,
        require_safe: bool = True,
        allow_declared: bool = False,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a target is authorized for managed execution.
        require_safe: if True, enforce auto-invocation safety rules.
        allow_declared: if True, allow DECLARED blast_radius on first invocation.
                       (typically False; set True only with explicit user intent).
        Returns (is_authorized, reason_if_not).
        """
        auth = self.get_authorization(target_id)

        if not auth:
            return False, f"No authorization found for {target_id}"

        is_valid, reason = auth.is_valid()
        if not is_valid:
            return False, reason

        if not require_safe:
            # Caller explicitly allows any blast radius
            return True, None

        # Enforce safety rules
        is_safe, reason = auth.is_safe_for_auto_invocation()
        if not is_safe:
            # If declared but not yet verified, check if we allow first invocation
            if (
                auth.blast_radius_provenance == BlastRadiusProvenance.DECLARED
                and auth.blast_radius in (BlastRadius.SAFE, BlastRadius.LOW)
                and allow_declared
            ):
                return True, None

            return False, reason

        return True, None

    def mark_verified(
        self,
        target_id: str,
        skill_result,  # SkillResult: all_succeeded, result_state, decision_method
    ) -> tuple[bool, Optional[str]]:
        """
        After execution, check if result meets verification criteria.
        If yes, mark blast_radius as VERIFIED.
        If no, return error and keep as DECLARED.
        
        Returns (was_verified, reason_if_failed).
        """
        auth = self.get_authorization(target_id)
        if not auth:
            return False, f"No authorization found for {target_id}"

        criteria = auth.verification_criteria
        errors = []

        # Check 1: all tests succeeded
        if criteria.all_tests_succeeded:
            all_pass = all(r.succeeded for r in skill_result.execution_results)
            if not all_pass:
                errors.append(f"Not all test cases succeeded (criterion: all_tests_succeeded=True)")

        # Check 2: no error markers in output
        if criteria.no_errors_in_output:
            error_markers = ["ERROR", "FAILED", "EXCEPTION", "error:", "failed:"]
            for result in skill_result.execution_results:
                if result.output:
                    if any(marker in result.output.upper() for marker in error_markers):
                        errors.append(f"Test case {result.test_case_name} output contains error marker")

        # Check 3: decision method deterministic (optional stricter check)
        if criteria.decision_method_deterministic:
            if skill_result.evidence_summary:
                if "MODEL_ASSISTED" in skill_result.evidence_summary or "HYBRID" in skill_result.evidence_summary:
                    errors.append(f"Decision method was not deterministic (criterion: decision_method_deterministic=True)")

        # Check 4: result state matches requirement (if set)
        if criteria.result_state_required:
            if skill_result.result_state.value != criteria.result_state_required.value:
                errors.append(
                    f"Result state {skill_result.result_state.value} does not match required "
                    f"{criteria.result_state_required.value}"
                )

        if errors:
            return False, "; ".join(errors)

        # All criteria passed — mark verified
        auth.blast_radius_provenance = BlastRadiusProvenance.VERIFIED
        auth.blast_radius_verified_at = datetime.utcnow()
        auth.blast_radius_reason = f"Verified via execution on {datetime.utcnow().isoformat()} — all criteria met"

        return True, None

    def revoke(self, target_id: str) -> None:
        """Revoke authorization."""
        if target_id in self.authorizations:
            del self.authorizations[target_id]
        if target_id in self.invocation_count:
            del self.invocation_count[target_id]

    def clear(self) -> None:
        """Clear all authorizations (testing only)."""
        self.authorizations.clear()
        self.invocation_count.clear()
