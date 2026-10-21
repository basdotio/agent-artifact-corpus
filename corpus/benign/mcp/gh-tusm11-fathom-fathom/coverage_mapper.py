"""Deterministic coverage mapper: rule-based skill applicability."""

from typing import Optional
from fathom.models import (
    SystemProfile,
    ProfileFact,
    SkillDefinition,
    ThreatCategory,
    CoverageState,
    Provenance,
)


class CoverageMapper:
    """
    Deterministic matcher: given profile facts and a set of skills,
    returns which skills apply and which facts remain unclassified.
    """

    def __init__(self):
        self.rules_version = "1.0"

    def is_skill_applicable(
        self, skill: SkillDefinition, profile: SystemProfile
    ) -> tuple[bool, Optional[str]]:
        """
        Check if all preconditions are met.
        Returns (applicable, reason_if_not).
        """
        for precond in skill.preconditions:
            # Find matching facts
            matching_facts = [
                f
                for f in profile.facts
                if f.category == precond.fact_category and f.key == precond.fact_key
            ]

            if not matching_facts:
                return False, f"Missing fact: {precond.fact_category}.{precond.fact_key}"

            # Check provenance requirement
            if precond.min_observed > 0:
                observed_count = sum(
                    1 for f in matching_facts if f.provenance == Provenance.OBSERVED
                )
                if observed_count < precond.min_observed:
                    return (
                        False,
                        f"Fact {precond.fact_category}.{precond.fact_key} has only "
                        f"{observed_count} observations, need {precond.min_observed}",
                    )

            # Check allowed values
            if precond.required_values is not None:
                for fact in matching_facts:
                    if fact.value not in precond.required_values:
                        return (
                            False,
                            f"Fact {precond.fact_category}.{precond.fact_key} has value "
                            f"{fact.value}, not in {precond.required_values}",
                        )

        return True, None

    def map_coverage(
        self, profile: SystemProfile, skills: list[SkillDefinition]
    ) -> dict:
        """
        Deterministic coverage mapping.
        Returns applicable skills, unclassified facts, and gaps.
        """
        applicable_skills = []
        inapplicable_skills = []
        threat_coverage = {}

        # Check each skill
        for skill in skills:
            is_applicable, reason = self.is_skill_applicable(skill, profile)
            if is_applicable:
                applicable_skills.append(skill)
                threat_category = skill.threat_category
                if threat_category not in threat_coverage:
                    threat_coverage[threat_category] = CoverageState.TESTED
            else:
                inapplicable_skills.append((skill, reason))

        # Find unclassified facts (not matched by any precondition)
        unclassified = []
        for fact in profile.facts:
            matched = any(
                fact.category == s.preconditions[0].fact_category
                and fact.key == s.preconditions[0].fact_key
                for skill in applicable_skills + [s for s, _ in inapplicable_skills]
                for s in [skill]
            )
            if not matched:
                unclassified.append(fact)

        # Identify threats with no applicable skills
        all_threat_categories = {s.threat_category for s in skills}
        untested_threats = [
            threat for threat in all_threat_categories if threat not in threat_coverage
        ]

        return {
            "applicable_skills": applicable_skills,
            "inapplicable_skills": inapplicable_skills,
            "threat_coverage": threat_coverage,
            "untested_threats": untested_threats,
            "unclassified_facts": unclassified,
        }
