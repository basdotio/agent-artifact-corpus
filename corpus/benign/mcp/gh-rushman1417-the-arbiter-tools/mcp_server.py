"""IBM Bob 2.0 MCP Server — Governance Tribunal Tool Interface.

Exposes four tools to the MCP host (IBM Bob 2.0):
    run_pytest       — Run the test suite inside the repository
    run_secret_scan  — Detect hardcoded secrets (fails CLOSED on error)
    read_file        — Read a source file from the target repository
    write_file       — Write/patch a file in the target repository (sandboxed)

Start with:
    python src/tools/mcp_server.py
or via the .bob/mcp.json configuration.
"""

import json
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path when started as __main__
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as _err:
    raise SystemExit(
        "The 'mcp' package is required.  Install with:  pip install \"mcp[cli]\""
    ) from _err

from src.evidence.collector import EvidenceCollector

# ── Server initialisation ─────────────────────────────────────────────────────

mcp: FastMCP = FastMCP(
    "governance-tribunal",
    description=(
        "The Governance Tribunal MCP server for IBM Bob 2.0. "
        "Provides forensic analysis, test execution, and sandboxed file I/O "
        "so Bob can drive the full remediation loop autonomously."
    ),
)

# Default repo path — overridable per-call via repo_path parameter
_DEFAULT_REPO: str = os.environ.get(
    "TRIBUNAL_REPO_PATH",
    str(_PROJECT_ROOT / "demo_repo"),
)

# ── Tool: run_pytest ──────────────────────────────────────────────────────────

@mcp.tool()
def run_pytest(repo_path: str = _DEFAULT_REPO) -> dict:
    """Run the test suite for the target repository.

    Parameters
    ----------
    repo_path:
        Absolute path to the repository whose ``tests/`` directory should be
        executed.  Defaults to the bundled ``demo_repo``.

    Returns
    -------
    dict
        ``passed`` (bool), ``total`` (int), ``failed`` (int),
        ``details`` (list of failing test node IDs),
        and optionally ``error`` (str) if execution failed.
    """
    import subprocess
    report_file = Path(repo_path) / "mcp_pytest_report.json"
    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                str(Path(repo_path) / "tests"),
                "--json-report", f"--json-report-file={report_file}",
                "--tb=short", "-q",
            ],
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=120,
        )
    except Exception as exc:
        return {"passed": False, "error": str(exc), "details": [], "total": 0, "failed": 0}

    if report_file.exists():
        try:
            with open(report_file) as f:
                report = json.load(f)
            failed_tests = [
                t["nodeid"]
                for t in report.get("tests", [])
                if t["outcome"] == "failed"
            ]
            return {
                "passed":  len(failed_tests) == 0,
                "total":   report.get("summary", {}).get("total", 0),
                "failed":  len(failed_tests),
                "details": failed_tests,
            }
        except (json.JSONDecodeError, KeyError) as exc:
            return {
                "passed":  result.returncode == 0,
                "error":   str(exc),
                "details": [],
                "total":   0,
                "failed":  0,
            }

    return {
        "passed":  result.returncode == 0,
        "total":   0,
        "failed":  0 if result.returncode == 0 else 1,
        "details": [],
    }


# ── Tool: run_secret_scan ─────────────────────────────────────────────────────

@mcp.tool()
def run_secret_scan(repo_path: str = _DEFAULT_REPO) -> dict:
    """Scan the repository for hardcoded secrets using detect-secrets.

    Security-critical: this tool ALWAYS fails closed — if the scanner
    cannot run or produces unreadable output, the result is
    ``{"passed": False, ...}`` rather than silently allowing the commit.

    Parameters
    ----------
    repo_path:
        Absolute path to the repository to scan.

    Returns
    -------
    dict
        ``passed`` (bool), ``findings`` (dict), and optionally ``error`` (str).
    """
    collector = EvidenceCollector(repo_path, str(_PROJECT_ROOT / "policies"))
    return collector.run_secret_scan()


# ── Tool: read_file ───────────────────────────────────────────────────────────

@mcp.tool()
def read_file(file_path: str, repo_path: str = _DEFAULT_REPO) -> dict:
    """Read a file from the target repository.

    Bob calls this to inspect source code before generating a patch.

    Parameters
    ----------
    file_path:
        Path to the file, either absolute or relative to ``repo_path``.
    repo_path:
        Absolute path to the repository root used to resolve relative paths.

    Returns
    -------
    dict
        ``content`` (str) on success, or ``error`` (str) and ``content: ""``
        on failure.
    """
    target = Path(file_path)
    if not target.is_absolute():
        target = Path(repo_path) / file_path

    try:
        content = target.read_text(encoding="utf-8")
        return {"content": content, "lines": content.count("\n") + 1}
    except FileNotFoundError:
        return {"content": "", "error": f"File not found: {target}"}
    except (OSError, UnicodeDecodeError) as exc:
        return {"content": "", "error": str(exc)}


# ── Tool: write_file ──────────────────────────────────────────────────────────

@mcp.tool()
def write_file(
    file_path: str,
    content: str,
    repo_path: str = _DEFAULT_REPO,
) -> dict:
    """Write (patch) a file in the target repository.

    Bob calls this to apply a generated fix.  The tool is sandboxed —
    any path that would escape the repo root is rejected.

    Parameters
    ----------
    file_path:
        Path to the file, either absolute or relative to ``repo_path``.
    content:
        Full replacement content to write.  Bob must supply the *entire*
        new file content, not a diff.
    repo_path:
        Absolute path to the repository root used to resolve relative paths.

    Returns
    -------
    dict
        ``success`` (bool) and optionally ``error`` (str).
    """
    repo_root = Path(repo_path).resolve()
    target = Path(file_path)
    if not target.is_absolute():
        target = (repo_root / file_path).resolve()

    # Sandbox check — must stay inside the repo
    try:
        target.relative_to(repo_root)
    except ValueError:
        return {
            "success": False,
            "error": f"Security: write path '{target}' escapes repo boundary '{repo_root}'",
        }

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"success": True, "bytes_written": len(content.encode("utf-8"))}
    except (OSError, UnicodeEncodeError) as exc:
        return {"success": False, "error": str(exc)}


# ── Entry-point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
