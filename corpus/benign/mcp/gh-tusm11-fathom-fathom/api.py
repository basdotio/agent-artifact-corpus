"""Fathom public API."""

import json
from pathlib import Path
from typing import Optional, Callable, Any
from fathom.pipeline import DiagnosticPipeline
from fathom.profiler import SystemProfiler
from fathom.models import SystemProfile, ProfileFact, Provenance
from fathom.registry import SkillRegistry, bootstrap_registry


class FathomClient:
    """
    High-level client for Fathom diagnostics.
    Simple entry point: profile system → diagnose → get report.
    """

    def __init__(self, registry: Optional[SkillRegistry] = None):
        self.registry = registry or bootstrap_registry()
        self.profiler = SystemProfiler()
        self.pipeline = DiagnosticPipeline(registry=self.registry)

    def create_profile(self, system_id: str) -> SystemProfile:
        """Create empty profile for manual fact addition."""
        return self.profiler.create_profile(system_id, [])

    def add_declared_fact(
        self, profile: SystemProfile, category: str, key: str, value: Any
    ) -> ProfileFact:
        """Add a declared fact to a profile."""
        fact = self.profiler.add_declared_fact(category, key, value)
        profile.facts.append(fact)
        return fact

    def add_observed_fact(
        self, profile: SystemProfile, category: str, key: str, value: Any
    ) -> ProfileFact:
        """Add an observed fact to a profile."""
        fact = self.profiler.add_observed_fact(category, key, value)
        profile.facts.append(fact)
        return fact

    def diagnose(self, profile: SystemProfile, executor: Optional[Callable] = None):
        """Run full diagnostic pipeline."""
        return self.pipeline.diagnose(profile, executor)

    def export_report(self, report, output_path: str) -> None:
        """Export report to JSON file."""
        output = Path(output_path)
        with open(output, "w") as f:
            json.dump(
                json.loads(report.model_dump_json()),
                f,
                indent=2,
                default=str,
            )
