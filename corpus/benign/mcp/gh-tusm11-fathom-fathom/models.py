"""Core data models for Fathom."""

from enum import Enum
from typing import Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


# === Enums ===

class Provenance(str, Enum):
    """Source of a profile fact."""
    DECLARED = "declared"  # Self-reported by target system
    OBSERVED = "observed"  # Independently verified by Fathom


class ThreatCategory(str, Enum):
    """Categories of behavioral inconsistency threats."""
    EVALUATION_CONTEXT_SENSITIVITY = "evaluation_context_sensitivity"
    TRIGGER_CONDITIONED_BEHAVIOR = "trigger_conditioned_behavior"
    STATE_DEPENDENT_BEHAVIOR = "state_dependent_behavior"
    TOOL_PERMISSION_BYPASS = "tool_permission_bypass"
    DATA_SOURCE_LEAKAGE = "data_source_leakage"
    MULTI_AGENT_COORDINATION = "multi_agent_coordination"


class ResultState(str, Enum):
    """Outcome of a behavioral test."""
    CONSISTENT = "consistent"
    DIVERGENT = "divergent"
    INCONCLUSIVE = "inconclusive"


class CoverageState(str, Enum):
    """Whether a threat category has been tested."""
    TESTED = "tested"
    NOT_TESTED = "not_tested"
    NOT_APPLICABLE = "not_applicable"
    UNCLASSIFIED = "unclassified"


class ValidationStatus(str, Enum):
    """Epistemic status of a skill."""
    EXPLORATORY = "exploratory"
    EMPIRICALLY_SUPPORTED = "empirically_supported"
    VALIDATED = "validated"
    DEPRECATED = "deprecated"


class DeprecationReason(str, Enum):
    """Why a skill was deprecated."""
    HIGH_FALSE_POSITIVE = "high_false_positive"
    HIGH_FALSE_NEGATIVE = "high_false_negative"
    FAILED_REPLICATION = "failed_replication"
    INVALIDATED_ASSUMPTION = "invalidated_assumption"
    SUPERIOR_REPLACEMENT = "superior_replacement"
    DEPENDENCY_CHANGED = "dependency_changed"
    SCOPE_EXPIRED = "scope_expired"


class ValidationMethod(str, Enum):
    """How a plan was validated."""
    DETERMINISTIC = "deterministic"
    MODEL_ASSISTED = "model_assisted"
    HYBRID = "hybrid"


class PlanValidityStatus(str, Enum):
    """Validation result."""
    VALID = "valid"
    INVALID = "invalid"
    INCONCLUSIVE = "inconclusive"


# === Profile Facts ===

class ProfileFact(BaseModel):
    """A single structural fact about the target system."""
    category: str
    key: str
    value: Any
    provenance: Provenance
    observed_at: Optional[datetime] = None


class SystemProfile(BaseModel):
    """Extracted facts about target system."""
    system_id: str
    facts: list[ProfileFact]
    profiled_at: datetime = Field(default_factory=datetime.utcnow)


# === Skills & Preconditions ===

class PreconditionRule(BaseModel):
    """Rule matching profile facts to skill applicability."""
    fact_category: str
    fact_key: str
    required_values: list[Any] | None = None  # None = any value ok
    min_observed: int = 0  # Min observations required (0=declared ok)


class SkillDefinition(BaseModel):
    """Schema for a diagnostic skill."""
    id: str
    version: int
    threat_category: ThreatCategory
    title: str
    description: str
    preconditions: list[PreconditionRule]
    test_generation_method: str  # e.g., "prompt_variant", "state_injection"
    execution_procedure: str
    decision_rules: str  # How to interpret results
    decision_function_spec: str  # v1.1: specifies decision layers (structural/semantic/model-assisted)
    known_limitations: str
    coverage_boundaries: str
    validation_status: ValidationStatus
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("id")
    @classmethod
    def id_format(cls, v: str) -> str:
        if not v or "_v" not in v:
            raise ValueError("ID must include version suffix (e.g., EvaluationContextSensitivity_v1)")
        return v


# === Plan Validation ===

class ValidationRecord(BaseModel):
    """Validation history for a skill's epistemic promotion."""
    skill_id: str
    proposer: str
    validator: str
    registry_authority: str
    independence_status: bool  # True = all three roles different
    protocol_version: str
    test_suite_version: str
    replication_count: int
    decision: ValidationStatus
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("independence_status")
    @classmethod
    def check_independence(cls, v: bool, info) -> bool:
        # Can only be True if proposer, validator, registry_authority are all different
        data = info.data
        if v:
            people = {data.get("proposer"), data.get("validator"), data.get("registry_authority")}
            if len(people) < 3:
                raise ValueError("Independence requires all three roles to be different people")
        return v


class PlanValidationResult(BaseModel):
    """Structured result of plan validation."""
    status: PlanValidityStatus
    validation_method: ValidationMethod
    structural_passed: bool
    semantic_passed: bool | None = None
    model_assisted_notes: str | None = None
    errors: list[str] = Field(default_factory=list)


# === Test Plan ===

class SkillTestCase(BaseModel):
    """Single variant in a test plan."""
    name: str
    description: str
    inputs: dict[str, Any]
    constraints: dict[str, Any] = Field(default_factory=dict)


class EvaluationPlan(BaseModel):
    """Bounded, ready-to-execute test plan."""
    id: str
    skill_id: str
    skill_version: int
    system_id: str
    test_cases: list[SkillTestCase]
    validation_result: PlanValidationResult
    created_at: datetime = Field(default_factory=datetime.utcnow)


# === Execution & Evidence ===

class ExecutionResult(BaseModel):
    """Raw outcome from running a single test case."""
    test_case_name: str
    succeeded: bool
    output: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkillResult(BaseModel):
    """Aggregated result from executing a skill."""
    skill_id: str
    skill_version: int
    system_id: str
    execution_results: list[ExecutionResult]
    result_state: ResultState
    evidence_summary: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EvidenceRecord(BaseModel):
    """Complete audit trail for a single diagnostic run."""
    id: str
    system_profile: SystemProfile
    evaluation_plan: EvaluationPlan
    skill_result: SkillResult
    created_at: datetime = Field(default_factory=datetime.utcnow)


# === Findings & Reports ===

class Finding(BaseModel):
    """Single finding in a diagnostic report."""
    threat_category: ThreatCategory
    result_state: ResultState
    coverage_state: CoverageState
    validation_status: ValidationStatus
    decision_method: ValidationMethod  # v1.1: how result_state was determined
    evidence_id: str
    summary: str
    details: str | None = None


class DiagnosticReport(BaseModel):
    """Complete diagnostic output for a system."""
    system_id: str
    findings: list[Finding]
    coverage_summary: dict[ThreatCategory, CoverageState]
    tested_skills: list[str]  # skill_id@version
    not_tested_threats: list[ThreatCategory]
    unclassified_facts: list[ProfileFact]
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    report_version: str = "1.0"
