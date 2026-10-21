#!/usr/bin/env python3
"""Idempotently add only the tracked WindAnvil tunnel cron lines on Butcher."""
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "ops/tunnel-cron.example"
SUPERVISOR = ROOT / "scripts/supervise-commander-tunnel.py"
HOME = Path("/home/commander")
STATE = HOME / ".local/state"


def fail(message: str) -> None:
    raise RuntimeError(message)


def reconcile(mode: str) -> None:
    if mode not in ("check", "install"):
        fail("usage: manage-tunnel-cron.py check|install")
    if os.getuid() != HOME.stat().st_uid:
        fail("wrong host UID")
    if not SUPERVISOR.is_file() or not (SUPERVISOR.stat().st_mode & 0o111):
        fail("tracked executable supervisor missing")
    actual = subprocess.run(["crontab", "-l"], text=True, capture_output=True)
    if actual.returncode != 0 and "no crontab for " not in actual.stderr.lower():
        fail("unable to read existing crontab")
    current = actual.stdout.splitlines()
    expected = [s for s in TEMPLATE.read_text().splitlines()
                if s.strip() and not s.lstrip().startswith("#")]
    if len(expected) != 2 or len(set(expected)) != 2:
        fail("tunnel cron template must contain exactly two unique entries")
    marker = "/scripts/supervise-commander-tunnel.py"
    unknown = [line for line in current if marker in line and line not in expected]
    duplicates = [line for line in expected if current.count(line) > 1]
    if unknown or duplicates:
        fail("unexpected or duplicated tunnel cron entries; manual review required")
    missing = [line for line in expected if line not in current]
    if mode == "check":
        if missing:
            fail("missing " + str(len(missing)) + " expected tunnel cron entries")
        print("PASS: both tracked tunnel cron lines are installed; unrelated jobs preserved")
        return
    if STATE.is_symlink() or not STATE.is_dir() or STATE.stat().st_uid != os.getuid():
        fail("unsafe private state directory")
    os.chmod(STATE, 0o700)
    logfile = STATE / "windanvil-tunnel-cron.log"
    if logfile.is_symlink():
        fail("cron log must not be a symlink")
    logfd = os.open(logfile, os.O_CREAT | os.O_APPEND | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(logfd, 0o600)
    finally:
        os.close(logfd)
    if not missing:
        print("PASS: cron already matches tracked tunnel entries; no changes")
        return
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = STATE / ("crontab-backup-tunnel-" + timestamp + "-" + str(os.getpid()))
    with open(backup, "x", encoding="utf-8") as f:
        os.fchmod(f.fileno(), 0o600)
        f.write(actual.stdout)
    fd, tmp = tempfile.mkstemp(prefix="tunnel-cron-", dir=STATE, text=True)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(actual.stdout)
            if actual.stdout and not actual.stdout.endswith("\n"):
                f.write("\n")
            f.write("\n".join(missing) + "\n")
        result = subprocess.run(["crontab", tmp], capture_output=True, text=True)
        if result.returncode != 0:
            fail("crontab write failed; backup retained")
        print("PASS: installed " + str(len(missing)) + " tunnel cron entries; backup saved privately")
    finally:
        Path(tmp).unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        reconcile(sys.argv[1] if len(sys.argv) == 2 else "")
    except (OSError, RuntimeError) as error:
        print("BLOCKED: " + str(error)[:160], file=sys.stderr)
        sys.exit(1)
