#!/usr/bin/env python3
"""Validate the files and metadata required for a releaseable skill package."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from audit_instructions import parse_frontmatter


ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise SystemExit(f"validation failed: {message}")


def main() -> int:
    required = [
        "SKILL.md",
        "README.md",
        "README.zh-CN.md",
        "RELEASE.md",
        "LICENSE",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "pyproject.toml",
        "scripts/audit_instructions.py",
        "references/official-guidance.md",
        "references/token-criteria.md",
        "references/report-schema.md",
        "tests/test_audit_instructions.py",
        ".github/workflows/validate.yml",
    ]
    for relative in required:
        if not (ROOT / relative).is_file():
            fail(f"missing {relative}")

    fields, issues = parse_frontmatter(ROOT / "SKILL.md")
    if issues:
        fail("SKILL.md frontmatter: " + "; ".join(issue.detail for issue in issues))
    if fields.get("name") != ROOT.name:
        fail("frontmatter name must match the skill directory")

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    version = re.search(r'^version\s*=\s*"([^"]+)"\s*$', pyproject, re.M)
    if not version or 'requires-python = ">=3.9"' not in pyproject or '"PyYAML>=6.0,<7"' not in pyproject:
        fail("pyproject.toml must declare a version, Python >=3.9, and PyYAML 6.x")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## [{version.group(1)}]" not in changelog:
        fail(f"CHANGELOG.md must contain the {version.group(1)} entry")
    print("package validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
