"""System profiler: declarative and observed fact extraction."""

from datetime import datetime
from typing import Any, Optional
from fathom.models import SystemProfile, ProfileFact, Provenance


class SystemProfiler:
    """
    Extracts structured facts about target systems.
    Facts tagged with provenance: declared (self-reported) or observed (verified).
    """

    def __init__(self):
        self.version = "1.0"

    def add_declared_fact(
        self,
        category: str,
        key: str,
        value: Any,
        profile: Optional[SystemProfile] = None,
    ) -> ProfileFact:
        """
        Record a fact as declared by the target system.
        Lower evidentiary weight than observed.
        """
        fact = ProfileFact(
            category=category,
            key=key,
            value=value,
            provenance=Provenance.DECLARED,
        )
        return fact

    def add_observed_fact(
        self,
        category: str,
        key: str,
        value: Any,
        profile: Optional[SystemProfile] = None,
    ) -> ProfileFact:
        """
        Record a fact independently verified by Fathom.
        Higher evidentiary weight than declared.
        """
        fact = ProfileFact(
            category=category,
            key=key,
            value=value,
            provenance=Provenance.OBSERVED,
            observed_at=datetime.utcnow(),
        )
        return fact

    def create_profile(self, system_id: str, facts: list[ProfileFact]) -> SystemProfile:
        """Build a complete profile from facts."""
        return SystemProfile(system_id=system_id, facts=facts, profiled_at=datetime.utcnow())

    def merge_profiles(
        self, profiles: list[SystemProfile]
    ) -> SystemProfile:
        """Merge multiple profiles (e.g., from different observation runs)."""
        if not profiles:
            raise ValueError("Cannot merge empty profile list")

        merged_system_id = profiles[0].system_id
        all_facts = []

        for profile in profiles:
            if profile.system_id != merged_system_id:
                raise ValueError(
                    f"Cannot merge profiles from different systems: "
                    f"{merged_system_id} vs {profile.system_id}"
                )
            all_facts.extend(profile.facts)

        # Deduplicate: keep observed over declared for same (category, key)
        fact_map = {}
        for fact in all_facts:
            key = (fact.category, fact.key)
            if key not in fact_map:
                fact_map[key] = fact
            elif fact.provenance == Provenance.OBSERVED:
                fact_map[key] = fact  # Observed overrides declared

        return SystemProfile(
            system_id=merged_system_id,
            facts=list(fact_map.values()),
            profiled_at=datetime.utcnow(),
        )

    def filter_profile(
        self, profile: SystemProfile, category: Optional[str] = None
    ) -> SystemProfile:
        """Extract a subset of facts by category."""
        filtered_facts = (
            [f for f in profile.facts if f.category == category]
            if category
            else profile.facts
        )
        return SystemProfile(
            system_id=profile.system_id,
            facts=filtered_facts,
            profiled_at=datetime.utcnow(),
        )

    def get_provenance_summary(self, profile: SystemProfile) -> dict:
        """Count declared vs observed facts."""
        declared = sum(1 for f in profile.facts if f.provenance == Provenance.DECLARED)
        observed = sum(1 for f in profile.facts if f.provenance == Provenance.OBSERVED)
        return {
            "total_facts": len(profile.facts),
            "declared": declared,
            "observed": observed,
            "declared_ratio": declared / len(profile.facts) if profile.facts else 0,
            "observed_ratio": observed / len(profile.facts) if profile.facts else 0,
        }
