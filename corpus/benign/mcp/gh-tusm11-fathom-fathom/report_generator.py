"""Coverage analyzer and diagnostic report generation."""

from typing import Optional
from fathom.models import (
    SystemProfile,
    SkillResult,
    EvidenceRecord,
    Finding,
    DiagnosticReport,
    ThreatCategory,
    CoverageState,
    ValidationStatus,
    ValidationMethod,
)
from fathom.registry import SkillRegistry


class CoverageAnalyzer:
    """Analyzes skill execution results and generates findings."""

    def __init__(self):
        self.version = "1.0"

    def analyze_evidence(
        self,
        evidence: EvidenceRecord,
        registry: SkillRegistry,
    ) -> Finding:
        """
        Convert evidence into a single Finding with result state, coverage state, and validation status.
        v1.1: Finding now includes decision_method (how result_state was determined).
        """
        skill_id = evidence.skill_result.skill_id
        skill = registry.get_skill(skill_id)

        if not skill:
            raise ValueError(f"Skill {skill_id} not found in registry")

        # Extract decision_method from evidence_summary if available
        # v1.1: evidence_summary now includes decision notes
        decision_method = self._extract_decision_method(evidence.skill_result.evidence_summary)

        finding = Finding(
            threat_category=skill.threat_category,
            result_state=evidence.skill_result.result_state,
            coverage_state=CoverageState.TESTED,
            validation_status=skill.validation_status,
            decision_method=decision_method,
            evidence_id=evidence.id,
            summary=f"Skill {skill_id} executed: {evidence.skill_result.result_state.value}",
            details=evidence.skill_result.evidence_summary,
        )

        return finding

    def _extract_decision_method(self, evidence_summary: str) -> ValidationMethod:
        """Extract decision method from evidence summary."""
        if "HYBRID" in evidence_summary or "model-assisted" in evidence_summary:
            return ValidationMethod.HYBRID
        elif "MODEL_ASSISTED" in evidence_summary:
            return ValidationMethod.MODEL_ASSISTED
        else:
            return ValidationMethod.DETERMINISTIC


class DiagnosticReportGenerator:
    """Generates complete diagnostic reports."""

    def __init__(self):
        self.version = "1.0"
        self.analyzer = CoverageAnalyzer()

    def generate_report(
        self,
        system_id: str,
        evidence_records: list[EvidenceRecord],
        registry: SkillRegistry,
        unclassified_facts: Optional[list] = None,
    ) -> DiagnosticReport:
        """
        Generate diagnostic report from evidence records.
        Includes findings, coverage summary, tested vs untested threats.
        """
        findings = []
        tested_skills = set()
        tested_threat_categories = set()

        for evidence in evidence_records:
            finding = self.analyzer.analyze_evidence(evidence, registry)
            findings.append(finding)
            tested_skills.add(evidence.skill_result.skill_id)
            tested_threat_categories.add(finding.threat_category)

        # Identify untested threats
        all_threats = set(s.threat_category for s in registry.get_all_skills())
        untested_threats = list(all_threats - tested_threat_categories)

        # Build coverage summary
        coverage_summary = {}
        for threat in all_threats:
            if threat in tested_threat_categories:
                coverage_summary[threat] = CoverageState.TESTED
            else:
                coverage_summary[threat] = CoverageState.NOT_TESTED

        report = DiagnosticReport(
            system_id=system_id,
            findings=findings,
            coverage_summary=coverage_summary,
            tested_skills=sorted(tested_skills),
            not_tested_threats=untested_threats,
            unclassified_facts=unclassified_facts or [],
        )

        return report
