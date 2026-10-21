#!/usr/bin/env python3
"""Butcher-only, fail-closed watchdog for the outbound Commander Secure MCP Tunnel.

Only manages this tunnel profile. Never copies or reads runtime key contents,
never exposes an inbound listener, and never manages Blade or Desktop Commander.
"""
from __future__ import annotations
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request

HOME = Path("/home/commander")
ROOT = HOME / "lab/talkpipe-mcp"
CLIENT = HOME / ".local/bin/tunnel-client"
PROFILE_DIR = HOME / ".config/tunnel-client"
STATE = HOME / ".local/state"
PROFILE = "windanvil-commander"
HEALTH_FILE = STATE / "windanvil-tunnel-health.url"
LOG = STATE / "windanvil-tunnel.log"
LOCK = STATE / "windanvil-tunnel-supervisor.lock"
EXPECTED_SHA256 = "01260ee973d5510861bc32979739561edd33869f99f9f8cd324f6d0da5b2e692"
VALID_URL = re.compile(r"http://127\.0\.0\.1:([0-9]{1,5})/?\Z")


def deny(message: str) -> None:
    raise RuntimeError(message)


def stat_private(path: Path, required_mode: int, *, directory: bool = False) -> None:
    if path.is_symlink() or not path.exists():
        deny(f"missing or symlinked private path: {path.name}")
    if path.stat().st_uid != os.getuid():
        deny(f"wrong owner on {path.name}")
    if path.stat().st_mode & 0o777 != required_mode:
        deny(f"unexpected permissions on {path.name}")
    if directory and not path.is_dir():
        deny(f"not a directory: {path.name}")
    if not directory and not path.is_file():
        deny(f"not a file: {path.name}")


def valid_health_base(candidate: str) -> str:
    candidate = candidate.strip()
    match = VALID_URL.fullmatch(candidate)
    if not match or not (1 <= int(match.group(1)) <= 65535):
        deny("health URL is not a loopback-only HTTP endpoint")
    return candidate.rstrip("/")


def readiness(base: str) -> bool:
    base = valid_health_base(base)
    for suffix in ("/healthz", "/readyz"):
        request = urllib.request.Request(base + suffix)
        try:
            with urllib.request.urlopen(request, timeout=2) as response:
                if response.status != 200:
                    return False
                response.read(256)
        except (OSError, ValueError):
            return False
    return True


def is_expected_process(pid: int) -> bool:
    try:
        cmdline = (Path("/proc") / str(pid) / "cmdline").read_bytes().split(b"\x00")
        args = [p.decode("utf-8", "strict") for p in cmdline if p]
        if len(args) < 6 or args[:5] != [
            str(CLIENT), "run", "--profile", PROFILE, "--profile-dir"
        ] or args[5] != str(PROFILE_DIR):
            return False
        if (Path("/proc") / str(pid)).stat().st_uid != os.getuid():
            return False
        return (Path("/proc") / str(pid) / "exe").resolve() == CLIENT.resolve()
    except (OSError, UnicodeError):
        return False


def running_pids() -> list[int]:
    found = []
    for path in Path("/proc").iterdir():
        if path.name.isdigit() and is_expected_process(int(path.name)):
            found.append(int(path.name))
    return sorted(found)


def verify_configuration() -> None:
    if os.getuid() != HOME.stat().st_uid:
        deny("Butcher account identity mismatch")
    stat_private(PROFILE_DIR, 0o700, directory=True)
    stat_private(PROFILE_DIR / (PROFILE + ".yaml"), 0o600)
    stat_private(PROFILE_DIR / "windanvil-runtime-key", 0o600)
    stat_private(STATE, 0o700, directory=True)
    if CLIENT.is_symlink() or not CLIENT.is_file() or CLIENT.stat().st_uid != os.getuid():
        deny("tunnel executable missing or not owned")
    if hashlib.sha256(CLIENT.read_bytes()).hexdigest() != EXPECTED_SHA256:
        deny("unreviewed tunnel-client executable (SHA-256 mismatch)")
    if not (ROOT / "windanvil_commander_mcp.py").is_file():
        deny("Commander MCP target is unavailable")
    audit = ROOT / "scripts/audit-tunnel-deployment.py"
    result = subprocess.run([sys.executable, str(audit)], capture_output=True, text=True,
                            cwd=ROOT, timeout=8, check=False)
    if result.returncode != 0:
        deny("tunnel profile audit failed")
    data = json.loads(result.stdout)
    if data.get("result") != "PASS" or data.get("runtime_key") != "file-present-secure-permissions":
        deny("tunnel profile or key is not verified")
    # The tunnel will reach the local Blade socket, so refuse to start when it is unavailable.
    blade = HOME / ".local/bin/windanvil-blade-boot"
    status = subprocess.run([str(blade), "check"], capture_output=True, text=True,
                            timeout=10, check=False)
    if status.returncode != 0 or "BLADE=healthy" not in status.stdout:
        deny("Blade signature/policy preflight not healthy")


def read_health_url() -> str | None:
    if not HEALTH_FILE.exists():
        return None
    stat_private(HEALTH_FILE, 0o600)
    return valid_health_base(HEALTH_FILE.read_text(encoding="utf-8"))


def outcome(status: str, **fields: object) -> None:
    print(json.dumps({"status": status, "remote_chatgpt_plugin_verified": False, **fields},
                     sort_keys=True))


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("check", "start"):
        deny("usage: supervise-commander-tunnel.py check|start")
    mode = sys.argv[1]
    os.umask(0o077)
    if STATE.is_symlink():
        deny("state directory is a symlink")
    STATE.mkdir(parents=True, exist_ok=True)
    STATE.chmod(0o700)
    stat_private(STATE, 0o700, directory=True)
    fd = os.open(LOCK, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        outcome("another-supervisor-running")
        return
    try:
        verify_configuration()
        pids = running_pids()
        if len(pids) > 1:
            deny("multiple Commander tunnel clients are running")
        if pids:
            base = read_health_url()
            if base is None:
                outcome("legacy-session-running", pid=pids[0], managed=False)
                return
            if readiness(base):
                outcome("healthy", pid=pids[0], managed=True)
                return
            deny("tunnel client running but readiness failed; manual review required")

        if mode == "check":
            outcome("not-running", managed=False)
            return

        if HEALTH_FILE.exists() or HEALTH_FILE.is_symlink():
            stat_private(HEALTH_FILE, 0o600)
            HEALTH_FILE.unlink()
        if LOG.is_symlink():
            deny("refusing symlinked tunnel log")
        logfd = os.open(LOG, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
        try:
            child = subprocess.Popen([
                str(CLIENT), "run", "--profile", PROFILE,
                "--profile-dir", str(PROFILE_DIR),
                "--health.url-file", str(HEALTH_FILE),
                "--log.level", "warn",
            ], cwd=ROOT, stdin=subprocess.DEVNULL, stdout=logfd,
               stderr=subprocess.STDOUT, close_fds=True, start_new_session=True)
        finally:
            os.close(logfd)
        deadline = time.monotonic() + 22
        while time.monotonic() < deadline:
            if child.poll() is not None:
                deny("tunnel client exited during startup; inspect private host log")
            if HEALTH_FILE.exists():
                try:
                    base = read_health_url()
                    if base is not None and readiness(base):
                        outcome("started", pid=child.pid, managed=True)
                        return
                except (ValueError, OSError, RuntimeError):
                    pass
            time.sleep(0.5)
        child.terminate()
        try:
            child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=3)
        deny("tunnel client did not become ready within the startup deadline")
    finally:
        os.close(fd)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)[:180],
                          "remote_chatgpt_plugin_verified": False}), file=sys.stderr)
        sys.exit(1)
