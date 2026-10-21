"""Research Engine: extract coverage gaps, propose candidate skills."""

import json
from pathlib import Path
from typing import Optional
from datetime import datetime
from fathom.models import DiagnosticReport, SkillDefinition, ValidationStatus, ResultState, CoverageState
from fathom.registry import SkillRegistry


def extract_coverage_gaps(report: DiagnosticReport) -> list[str]:
    """
    Extract coverage gaps from a diagnostic report.
    
    Returns list of gap descriptions:
    - Findings with Result State: INCONCLUSIVE
    - Findings with Coverage State: NOT_TESTED
    """
    gaps = []
    
    # Check findings for gaps
    for finding in report.findings:
        # INCONCLUSIVE result state
        if finding.result_state == ResultState.INCONCLUSIVE:
            gaps.append(f"Inconclusive result: {finding.summary}")
        
        # NOT_TESTED coverage state
        if finding.coverage_state == CoverageState.NOT_TESTED:
            gaps.append(f"Not tested: {finding.summary}")
    
    return gaps


def read_reports_from_dir(evidence_dir: Path = None) -> list[DiagnosticReport]:
    """Load all diagnostic reports from evidence directory."""
    if evidence_dir is None:
        evidence_dir = Path(__file__).parent.parent / ".fathom_evidence"
    
    reports = []
    if evidence_dir.exists():
        for report_file in evidence_dir.glob("*.json"):
            try:
                with open(report_file) as f:
                    data = json.load(f)
                    report = DiagnosticReport(**data)
                    reports.append(report)
            except Exception:
                pass
    
    return reports


def aggregate_gaps(reports: list[DiagnosticReport]) -> list[str]:
    """Aggregate unique gaps across all reports."""
    all_gaps = []
    for report in reports:
        all_gaps.extend(extract_coverage_gaps(report))
    
    # Deduplicate while preserving order
    seen = set()
    unique_gaps = []
    for gap in all_gaps:
        if gap not in seen:
            seen.add(gap)
            unique_gaps.append(gap)
    
    return unique_gaps


def validate_candidate(candidate: dict) -> tuple[bool, Optional[str]]:
    """
    Structurally validate candidate SkillDefinition.
    
    Returns (is_valid, error_message)
    """
    required_fields = [
        "id",
        "version",
        "description",
        "test_structure",
        "expected_behavior",
        "validation_status",
    ]
    
    for field in required_fields:
        if field not in candidate:
            return False, f"Missing required field: {field}"
    
    # Validate enum values
    valid_statuses = {s.value for s in ValidationStatus}
    if candidate.get("validation_status") not in valid_statuses:
        return False, f"Invalid validation_status: {candidate.get('validation_status')}"
    
    return True, None


def generate_candidate_skill(gap: str, registry: SkillRegistry) -> Optional[SkillDefinition]:
    """
    Generate a candidate SkillDefinition by extending an existing skill category.
    
    Strategy: find the most similar existing skill, use it as a template,
    adjust description to address the gap.
    
    Always registers at EXPLORATORY (no promotion path in v1).
    """
    # Get existing skills as examples
    existing_skills = registry.get_all_skills()
    
    if not existing_skills:
        # No skills to extend from yet
        return None
    
    # Simple template: clone the first skill, update description and ID
    base_skill = existing_skills[0]
    
    candidate_id = f"Gap_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    candidate = SkillDefinition(
        id=candidate_id,
        version=1,
        threat_category=base_skill.threat_category,
        title=f"Exploratory: {gap[:50]}",
        description=f"Exploratory skill addressing gap: {gap[:100]}",
        test_generation_method=base_skill.test_generation_method,
        execution_procedure=base_skill.execution_procedure,
        decision_rules=base_skill.decision_rules,
        validation_status=ValidationStatus.EXPLORATORY,
    )
    
    return candidate


def process_gap_and_register(gap: str, registry: SkillRegistry) -> tuple[Optional[SkillDefinition], Optional[str]]:
    """
    Process one gap: generate candidate, validate, register at EXPLORATORY.
    
    Returns (candidate_skill, error_message)
    """
    candidate = generate_candidate_skill(gap, registry)
    
    if candidate is None:
        return None, "No existing skills to extend from"
    
    # Validate structure
    candidate_dict = candidate.model_dump()
    is_valid, error = validate_candidate(candidate_dict)
    
    if not is_valid:
        return None, error
    
    # Register at EXPLORATORY (hard stop, no promotion)
    registry.register_skill(candidate)
    
    return candidate, None


