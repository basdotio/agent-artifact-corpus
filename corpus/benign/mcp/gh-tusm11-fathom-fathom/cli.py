"""CLI entry point for Fathom."""

import sys
import json
from pathlib import Path
from fathom.api import FathomClient
from fathom.execution_adapter import MockTargetAgent


def create_profile_interactive():
    """Interactive profile creation."""
    client = FathomClient()

    system_id = input("System ID: ").strip()
    profile = client.create_profile(system_id)

    print(f"Profile created for {system_id}")
    print("Add facts (format: category key value [observed]). Enter 'done' to finish.")

    while True:
        line = input("> ").strip()
        if line == "done":
            break

        parts = line.split()
        if len(parts) < 3:
            print("Usage: category key value [observed]")
            continue

        category, key, value = parts[0], parts[1], parts[2]
        observed = len(parts) > 3 and parts[3].lower() == "observed"

        # Parse value
        if value.lower() in ("true", "false"):
            value = value.lower() == "true"
        elif value.isdigit():
            value = int(value)

        if observed:
            client.add_observed_fact(profile, category, key, value)
        else:
            client.add_declared_fact(profile, category, key, value)

        print(f"Added: {category}.{key} = {value} ({'observed' if observed else 'declared'})")

    return profile


def run_diagnostic(profile, executor_behavior="consistent"):
    """Run diagnostic on profile."""
    client = FathomClient()

    print(f"\nDiagnosing {profile.system_id} (executor: {executor_behavior})...")

    mock_agent = MockTargetAgent(behavior=executor_behavior)
    executor = mock_agent.get_executor()

    report = client.diagnose(profile, executor)

    print(f"\n=== DIAGNOSTIC REPORT ===")
    print(f"System: {report.system_id}")
    print(f"Findings: {len(report.findings)}")
    print(f"Tested skills: {', '.join(report.tested_skills) or 'None'}")
    print(f"Untested threats: {len(report.not_tested_threats)}")

    print(f"\n=== FINDINGS ===")
    for i, finding in enumerate(report.findings, 1):
        print(f"\n{i}. {finding.threat_category.value}")
        print(f"   Result: {finding.result_state.value}")
        print(f"   Coverage: {finding.coverage_state.value}")
        print(f"   Status: {finding.validation_status.value}")
        print(f"   Summary: {finding.summary}")

    return report


def main():
    """CLI main."""
    if len(sys.argv) < 2:
        print("Fathom diagnostic framework")
        print("\nUsage:")
        print("  python -m fathom.cli interactive  - Interactive mode")
        print("  python -m fathom.cli demo         - Demo with mock agent")
        return

    command = sys.argv[1]

    if command == "interactive":
        profile = create_profile_interactive()
        run_diagnostic(profile)

    elif command == "demo":
        # Demo: profile → diagnose → export
        client = FathomClient()

        profile = client.create_profile("demo_agent")
        client.add_declared_fact(profile, "tools", "has_web_access", True)
        client.add_observed_fact(profile, "state", "persistent_memory", False)

        print("Demo profile created:")
        print(f"  System: {profile.system_id}")
        print(f"  Facts: {len(profile.facts)}")

        # Diagnose
        report = run_diagnostic(profile, executor_behavior="consistent")

        # Export
        export_path = "demo_report.json"
        client.export_report(report, export_path)
        print(f"\nReport exported to {export_path}")

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
