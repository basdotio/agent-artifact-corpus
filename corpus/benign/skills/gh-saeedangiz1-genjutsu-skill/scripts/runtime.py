#!/usr/bin/env python3
"""Portable entry point for the bundled Genjutsu runtime."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "assets" / "workflow"
COMMANDS = ("doctor", "preflight", "prepare", "resume-preparation", "submit", "review", "status", "resume", "hd", "repair-rgb", "launch")


def worker_python() -> Path:
    return WORKFLOW / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def command_argv(command: str, arguments: list[str]) -> list[str]:
    if command not in COMMANDS:
        raise ValueError(f"Unknown command: {command}")
    worker = worker_python()
    helper = {"doctor": "doctor.py", "preflight": "preflight.py", "launch": "launch.py"}.get(command, "workflow.py")
    script = WORKFLOW / helper
    if not script.is_file():
        raise ValueError(f"Bundled runtime resource missing: {helper}. Reinstall the complete skill.")
    offline = command in {"doctor", "preflight"} or "--help" in arguments or "-h" in arguments
    if not worker.is_file() and not offline:
        if os.name == "nt":
            raise ValueError("Runtime environment missing. Supported Windows setup uses WSL2 Ubuntu: open the skill there and run bash assets/workflow/setup.sh. Native Windows runtime has not been live-validated. No WSL2 or admin installation is performed automatically.")
        raise ValueError("Runtime environment missing. Run bash assets/workflow/setup.sh (Python 3.12+ and Rubber Band CLI required).")
    argv = [str(worker if worker.is_file() else sys.executable), str(script)]
    if helper == "workflow.py":
        argv.append(command)
    return argv + list(arguments)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, epilog="Examples: runtime.py doctor | runtime.py preflight clip.mp4 --mode depth | runtime.py prepare --help. Commands forward arguments without shell interpolation.")
    parser.add_argument("command", choices=COMMANDS, help="Offline checks, job CLI, or local web UI.")
    parser.add_argument("arguments", nargs=argparse.REMAINDER, help="Arguments forwarded unchanged to the selected helper.")
    args = parser.parse_args(argv)
    try:
        command = command_argv(args.command, args.arguments)
        return subprocess.run(command, check=False).returncode
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Runtime unavailable: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
