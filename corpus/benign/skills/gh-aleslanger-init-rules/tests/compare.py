#!/usr/bin/env python3
"""Repeatable, side-by-side Claude skill comparison on three isolated fixtures.

Run:   python3 tests/compare.py run --plugin-dir PATH --output-dir /tmp/init-rules-benchmark
Score: python3 tests/compare.py score --output-dir /tmp/init-rules-benchmark

The run command calls Claude Code and incurs API cost. It never edits this repo.
"""

import argparse
import json
import re
import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
CASES = {
    "demo": {
        "commands": ["make test", "make lint", "make typecheck", "make gen"],
        "forbidden": ["npm test", "change-me"],
        "preserved": ["owner_id", "404"],
        "paths": ["proto/orders.proto", "app/gen"],
    },
    "go_cli": {
        "commands": ["make test", "make vet"],
        "forbidden": ["npm test"],
        "preserved": ["0600"],
        "paths": ["internal/config"],
    },
    "web_app": {
        "commands": ["npm test", "npm run lint", "npm run build"],
        "forbidden": ["yarn test"],
        "preserved": ["credentials", "include"],
        "paths": ["src/api/client.js"],
    },
}
GENERIC = ("write clean code", "follow best practices")
ALLOWED_CHANGES = re.compile(r"^(CLAUDE\.md|\.claude/rules/[^/]+\.md)$")


def command(argv, cwd, timeout=900):
    start = time.monotonic()
    try:
        result = subprocess.run(
            argv, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False
        )
        return {
            "exit_code": result.returncode,
            "seconds": round(time.monotonic() - start, 1),
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "exit_code": 124,
            "seconds": round(time.monotonic() - start, 1),
            "stdout": (exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
            "stderr": (exc.stderr or b"").decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
        }


def prepare(case, candidate, output_dir):
    destination = output_dir / case / candidate
    if destination.exists():
        raise SystemExit(f"Refusing to overwrite {destination}; use a new --output-dir")
    shutil.copytree(FIXTURES / case, destination)
    (destination / "CLAUDE.md.fixture").rename(destination / "CLAUDE.md")
    for argv in (
        ["git", "init", "-q"],
        ["git", "add", "-A"],
        ["git", "-c", "user.email=test@example.com", "-c", "user.name=test", "commit", "-qm", "fixture"],
    ):
        result = command(argv, destination)
        if result["exit_code"]:
            raise SystemExit(f"Setup failed in {destination}: {result['stderr']}")
    return destination


def run_case(case, candidate, output_dir, plugin_dir):
    repo = prepare(case, candidate, output_dir)
    if candidate == "local":
        steps = [command([
            "claude", "-p", "/init-rules", "--permission-mode", "acceptEdits",
            "--add-dir", str(ROOT / "references"),
            "--allowedTools", "Read,Write,Edit,Glob,Grep,TodoWrite,Agent,"
            "Edit(.claude/rules/**),Edit(CLAUDE.md),Bash(mkdir *),Bash(git *),"
            "Bash(ls *),Bash(find *),Bash(cat *),Bash(grep *),Bash(python3 *),"
            "Bash(wc *),Bash(head *),Bash(make -n *)",
        ], repo)]
        report = steps[0]["stdout"]
    else:
        if not plugin_dir:
            raise SystemExit("--plugin-dir is required for the official candidate")
        first = command([
            "claude", "-p", "/claude-md-management:claude-md-improver "
            "Audit and improve this repository CLAUDE.md. This is an isolated test fixture. "
            "Present your report and proposed changes first; I will approve in the next turn.",
            "--plugin-dir", str(plugin_dir), "--output-format", "json",
            "--permission-mode", "acceptEdits",
        ], repo)
        steps = [first]
        try:
            payload = json.loads(first["stdout"])
            report = payload.get("result", "")
            session_id = payload["session_id"]
        except (ValueError, KeyError):
            report = first["stdout"]
            session_id = None
        if session_id and first["exit_code"] == 0:
            second = command([
                "claude", "-p", "I approve the proposed CLAUDE.md changes in this isolated test fixture. "
                "Apply them and inspect the diff.", "--resume", session_id,
                "--plugin-dir", str(plugin_dir), "--permission-mode", "acceptEdits",
            ], repo)
            steps.append(second)
            report += "\n\n## Approval turn\n" + second["stdout"]

    (repo / "benchmark-report.txt").write_text(report)
    # The report is an output artifact, not a change to the fixture under evaluation.
    (repo / "benchmark-steps.json").write_text(json.dumps(steps, indent=2))
    print(f"{case}/{candidate}: exits {[step['exit_code'] for step in steps]}", flush=True)


def evaluate(case, candidate, output_dir):
    repo = output_dir / case / candidate
    content = (repo / "CLAUDE.md").read_text() if (repo / "CLAUDE.md").exists() else ""
    report = (repo / "benchmark-report.txt").read_text() if (repo / "benchmark-report.txt").exists() else ""
    steps = json.loads((repo / "benchmark-steps.json").read_text()) if (repo / "benchmark-steps.json").exists() else []
    status = command(["git", "status", "--porcelain", "--untracked-files=all"], repo)["stdout"]
    changed = [line[3:] for line in status.splitlines() if line[3:] not in {"benchmark-report.txt", "benchmark-steps.json"}]
    expected = CASES[case]
    rules = list((repo / ".claude" / "rules").glob("*.md")) if (repo / ".claude" / "rules").exists() else []
    blocked = bool(re.search(
        r"sensitive file|write.{0,30}denied|zápis.{0,30}zablok|nešlo schválit",
        report, re.I))
    proposed = re.findall(r"^\*{0,2}`(\.claude/rules/[^`]+\.md)`\*{0,2}:?\s*$", report, re.M)
    drafts = re.findall(r"```markdown\s*\n---\npaths:.*?\n---\n.*?\n```", report, re.S)
    return {
        "case": case,
        "candidate": candidate,
        "commands": {value: value in content for value in expected["commands"]},
        "forbidden_absent": {value: value not in content for value in expected["forbidden"]},
        "preserved": {value: value in content for value in expected["preserved"]},
        "paths": {value: value in content or any(value in rule.read_text() for rule in rules)
                  for value in expected["paths"]},
        "generic_absent": not any(value in content.lower() for value in GENERIC),
        "scope_ok": all(ALLOWED_CHANGES.fullmatch(value) for value in changed),
        "changed_files": changed,
        "lines": len(content.splitlines()),
        "written_rules": len(rules),
        "blocked_rule_drafts": len(drafts) if blocked or proposed else None,
        "exit_codes": [step["exit_code"] for step in steps],
        "seconds": round(sum(step["seconds"] for step in steps), 1),
    }


def write_summary(output_dir, cases):
    results = [evaluate(case, candidate, output_dir) for case in cases for candidate in ("local", "official")]
    (output_dir / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    lines = ["# Skill comparison", "", "The same fixture is used for each candidate. No composite score is calculated.", "",
             "| Case | Candidate | Commands | Forbidden absent | Preserved | Paths | Generic absent | Scope | Lines | Rules written | Drafts if blocked | Seconds | Exits |",
             "|---|---|---:|---:|---:|---:|---|---|---:|---:|---:|---:|---|"]
    for row in results:
        count = lambda key: f"{sum(row[key].values())}/{len(row[key])}"
        lines.append("| " + " | ".join([
            row["case"], row["candidate"], count("commands"), count("forbidden_absent"),
            count("preserved"), count("paths"), str(row["generic_absent"]), str(row["scope_ok"]),
            str(row["lines"]), str(row["written_rules"]), str(row["blocked_rule_drafts"]),
            str(row["seconds"]), ",".join(map(str, row["exit_codes"])),
        ]) + " |")
    lines += ["", "Inspect each CLAUDE.md and benchmark-report.txt for unsupported claims and useful detail; the checks above are deliberately narrow."]
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "score"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--plugin-dir", type=Path)
    parser.add_argument("--case", choices=CASES, action="append")
    args = parser.parse_args()
    cases = args.case or list(CASES)
    if args.action == "run":
        if shutil.which("claude") is None:
            raise SystemExit("claude CLI is required")
        if not args.plugin_dir or not (args.plugin_dir / ".claude-plugin" / "plugin.json").exists():
            raise SystemExit("--plugin-dir must point to the installed claude-md-management plugin")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for case in cases:
            for candidate in ("local", "official"):
                run_case(case, candidate, args.output_dir, args.plugin_dir)
    write_summary(args.output_dir, cases)


if __name__ == "__main__":
    main()
