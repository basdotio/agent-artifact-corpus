"""Normal pytest hooks for CI evidence; runtime product code is untouched."""
import json
import os
import sys
from pathlib import Path


class Report:
    def __init__(self, destination):
        self.destination = destination
        self.outcomes = {}
        self.collection_failed = False

    def pytest_collectreport(self, report):
        if report.failed:
            self.collection_failed = True

    def pytest_runtest_logreport(self, report):
        phases = self.outcomes.setdefault(report.nodeid, {})
        outcome = "fail" if report.failed else "skip" if report.skipped else "pass"
        # Subtest reports reuse the parent's nodeid. A skipped context cannot
        # prove an exact independently declared skip identity, so fail closed.
        if (report.skipped and hasattr(report, "context")) or (
                report.passed and hasattr(report, "wasxfail")):
            outcome = "fail"
        priority = {"pass": 0, "skip": 1, "fail": 2}
        previous = phases.get(report.when, "pass")
        phases[report.when] = max((previous, outcome), key=priority.__getitem__)

    def pytest_sessionfinish(self, session, exitstatus):
        tests = []
        collected = {item.nodeid for item in session.items}
        for item in session.items:
            phases = self.outcomes.get(item.nodeid, {})
            outcome = ("fail" if not phases or "fail" in phases.values()
                       else "skip" if "skip" in phases.values()
                       else "pass" if phases.get("call") == "pass" and phases.get("teardown") == "pass"
                       else "fail")
            tests.append({"testId": item.nodeid, "outcome": outcome})
        # Every observed record must survive accounting. An unexpected parent
        # cannot prove a selected test result, regardless of its claimed outcome.
        for nodeid in self.outcomes:
            if nodeid not in collected:
                tests.append({"testId": nodeid, "outcome": "fail"})
        counts = {key: sum(test["outcome"] == key for test in tests)
                  for key in ("pass", "skip", "fail")}
        self.destination.write_text(json.dumps({
            "schema": "portfolio-pytest-report-v1", "tests": tests, **counts
        }, ensure_ascii=True) + "\n", encoding="utf-8")


def main():
    if len(sys.argv) < 2:
        raise SystemExit("pytest report destination required")
    destination = Path(sys.argv[1])
    # Executing a script normally puts its helper folder first. Match python -m
    # pytest's project import behavior without inherited PYTHONPATH or user site.
    sys.path.insert(0, os.getcwd())
    import pytest
    plugin = Report(destination)
    result = pytest.main(sys.argv[2:], plugins=[plugin])
    if plugin.collection_failed and result == 0:
        result = 1
    raise SystemExit(result)


if __name__ == "__main__":
    main()
