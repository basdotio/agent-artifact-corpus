"""script_writer: plain-English task -> small Python script -> user approves -> guarded run.

Two MCP tools, deliberately separate so a human always sits between "write" and "run":
  write_script(task)      writes the script and checks it, but does NOT run it
  run_script(script_id)   runs an approved script in sandbox_runner.py's guard rails

Safety layers: (1) import allow-list + banned calls (static check), (2) runtime audit hook
(writes only inside the workspace, no network/subprocess), (3) secrets stripped from the
environment, (4) 60 second timeout, (5) the user hears what will happen and says yes first.
"""
from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from analyze_data import WORKSPACE, _gemini_text

SCRIPTS = WORKSPACE / "scripts"
SCRIPTS.mkdir(parents=True, exist_ok=True)
RUNNER = Path(__file__).with_name("sandbox_runner.py")
RUN_TIMEOUT_S = 60
MAX_OUTPUT_CHARS = 4000
PENDING_TTL_S = 600  # a written script can be approved for 10 minutes, then it expires

ALLOWED_IMPORTS = {
    "pathlib", "os", "shutil", "json", "csv", "re", "datetime", "time", "math", "statistics",
    "collections", "itertools", "functools", "textwrap", "string", "zipfile", "glob", "fnmatch",
    "hashlib", "random", "typing", "io", "pandas", "numpy", "openpyxl", "pdf_utils",
}
BANNED_CALLS = {"eval", "exec", "compile", "__import__", "input", "breakpoint"}

WRITE_PROMPT = """You write small, safe Python 3 scripts that run on the user's laptop.
TASK: {task}

Environment:
- The script runs with the workspace folder as its working directory: {workspace}
- Files currently in the workspace (up to 80): {files}

Rules:
- Only read and write files inside the workspace, using relative paths. No network, no subprocess.
- Allowed imports ONLY: {imports}. For PDFs use: from pdf_utils import md_to_pdf
  (md_to_pdf(markdown_text, "out.pdf") writes a PDF).
- Never delete or overwrite existing files unless the task explicitly says to. To organize, MOVE
  files into subfolders; if the target name exists, add a numeric suffix.
- Print a short, clear summary of exactly what was done (counts and names, under 40 lines).
- Keep it simple: under 80 lines, no input() prompts.

Reply in EXACTLY this format and nothing else:
SUMMARY: <one or two plain sentences saying what the script will do, no jargon>
DESTRUCTIVE: <yes or no>
```python
<the script>
```
DESTRUCTIVE is "yes" only if the script deletes or overwrites existing files. Moving files into
subfolders is "no"."""


# ----------------------------- static check ----------------------------------
def static_check(code: str) -> list[str]:
    """Return a list of problems; an empty list means the script passed."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"syntax error: {e}"]
    problems = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            mods = [(node.module or "").split(".")[0]]
        else:
            mods = []
        problems += [f"import not allowed: {m}" for m in mods if m not in ALLOWED_IMPORTS]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in BANNED_CALLS:
            problems.append(f"call not allowed: {node.func.id}()")
    return problems


def _list_workspace(limit: int = 80) -> list[str]:
    skip = {"scripts"}
    out = []
    for p in sorted(WORKSPACE.rglob("*")):
        if p.is_file() and not (set(p.relative_to(WORKSPACE).parts) & skip):
            out.append(str(p.relative_to(WORKSPACE)))
        if len(out) >= limit:
            break
    return out


def _snapshot() -> dict[str, tuple[int, int]]:
    snap = {}
    for p in WORKSPACE.rglob("*"):
        if p.is_file() and "scripts" not in p.relative_to(WORKSPACE).parts:
            st = p.stat()
            snap[str(p.relative_to(WORKSPACE))] = (st.st_size, int(st.st_mtime))
    return snap


def _parse_reply(text: str):
    """Split the model reply into (summary, destructive, code, problems)."""
    summary = re.search(r"^SUMMARY:\s*(.+)$", text, re.M | re.I)
    destructive = re.search(r"^DESTRUCTIVE:\s*(yes|true)", text, re.M | re.I)
    code = re.search(r"```(?:python)?[ \t]*\n(.*?)```", text, re.S)
    if not code:
        return "", False, "", ["no complete ```python code block (reply may have been cut off)"]
    src = code.group(1).strip()
    problems = static_check(src) if src else ["empty script"]
    return (summary.group(1).strip() if summary else ""), bool(destructive), src, problems


def _is_pending(path: Path) -> bool:
    return (path.exists() and not path.with_suffix(".done").exists()
            and time.time() - path.stat().st_mtime <= PENDING_TTL_S)


def _latest_pending() -> Path | None:
    files = sorted(SCRIPTS.glob("script_*.py"), key=lambda p: p.stat().st_mtime, reverse=True)
    return next((p for p in files if _is_pending(p)), None)


# ----------------------------- MCP tools -------------------------------------
def write_script(task: str) -> dict:
    """Use when the user wants something DONE with files on the laptop: organize or rename files
    in a folder, move or sort files, generate a PDF or report from files, clean or convert a data
    file, and similar chores. Writes a small Python script for the task but does NOT run it.
    Returns summary_for_user, the code, and a script_id. Tell the user in one or two plain
    sentences what will happen and ask 'shall I run it?'. Never call run_script in the same turn;
    wait for the user's explicit yes."""
    prompt = (WRITE_PROMPT.replace("{task}", task).replace("{workspace}", str(WORKSPACE))
              .replace("{files}", str(_list_workspace()) or "[]")
              .replace("{imports}", ", ".join(sorted(ALLOWED_IMPORTS))))
    problems: list[str] = []
    summary, destructive, code = "", False, ""
    for _ in range(3):
        retry = f"\n\nYour previous reply was rejected: {problems}. Fix this and reply again in the same format." if problems else ""
        summary, destructive, code, problems = _parse_reply(_gemini_text(prompt + retry))
        if not problems:
            break
    if problems:
        raise RuntimeError(f"Could not produce a safe script for this task: {problems}")

    script_id = f"script_{datetime.now():%Y%m%d_%H%M%S}"
    (SCRIPTS / f"{script_id}.py").write_text(code, encoding="utf-8")
    return {
        "script_id": script_id,
        "summary_for_user": summary,
        "destructive": destructive,
        "code": code,
        "safety_check": "passed (allowed imports only; writes limited to the workspace; no network)",
        "next_step": "Tell the user what the script will do and ask for a clear yes before run_script.",
    }


def run_script(script_id: str = "") -> dict:
    """Run the script that write_script just created, ONLY after the user has said yes to it.
    `script_id` is the id write_script returned; if you do not have it, leave it empty and the
    most recent script waiting for approval runs. A script runs once and expires after 10
    minutes. It runs in a sandbox: it can only change files inside the workspace folder and has
    no network. Returns the printed output and the files created, changed or removed. Report
    that result to the user in one or two sentences."""
    path = SCRIPTS / f"{script_id}.py" if re.fullmatch(r"script_\d{8}_\d{6}", script_id or "") else None
    if path is None or not _is_pending(path):
        path = _latest_pending()
    if path is None:
        raise RuntimeError("No script is waiting for approval (they expire after 10 minutes). Call write_script first.")
    path.with_suffix(".done").write_text(datetime.now().isoformat())  # single use, even if it crashes
    problems = static_check(path.read_text(encoding="utf-8"))
    if problems:
        raise RuntimeError(f"Script failed the safety check: {problems}")

    env = {k: v for k, v in os.environ.items() if not re.search(r"KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL", k, re.I)}
    env.update(
        SANDBOX_WORKSPACE=str(WORKSPACE),
        PYTHONPATH=str(RUNNER.parent),
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONIOENCODING="utf-8",
    )
    before = _snapshot()
    try:
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", str(RUNNER), str(path)],
            cwd=WORKSPACE, env=env, capture_output=True, text=True,
            timeout=RUN_TIMEOUT_S, encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Script stopped: it ran longer than {RUN_TIMEOUT_S} seconds") from None
    after = _snapshot()

    created = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(f for f in set(before) & set(after) if before[f] != after[f])
    return {
        "script_id": path.stem,
        "succeeded": proc.returncode == 0,
        "output": (proc.stdout or "")[-MAX_OUTPUT_CHARS:],
        "errors": (proc.stderr or "")[-MAX_OUTPUT_CHARS:],
        "files_created": created[:30],
        "files_changed": changed[:30],
        "files_removed_or_moved_away": removed[:30],
    }