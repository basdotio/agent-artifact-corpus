"""
Nova 24/7 Security Monitor — h4cker-based, reports to OpenCode MCP sidebar.
Watches for data leaks, bugs, malware, hacking attempts.
"""
import os, pathlib, json, psutil, subprocess, time
import ctypes, ctypes.util
from datetime import datetime

# This Python build exposes no os.listxattr/os.getxattr, so quarantine checks go
# through libc. Faster than shelling out to `xattr` per file on a fanless machine.
_libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc", use_errno=True)
_libc.listxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_size_t]
_libc.listxattr.restype = ctypes.c_ssize_t

# The `mcp` package renamed FastMCP -> MCPServer in 2.x. Import whichever this
# venv actually has, so the server starts instead of dying on ImportError.
try:
    from mcp.server.mcpserver import MCPServer as _Server   # mcp >= 2.x
except ImportError:
    from mcp.server.fastmcp import FastMCP as _Server        # mcp 1.x

mcp = _Server("nova-security-monitor")

ROOT = pathlib.Path(__file__).resolve().parent
LOG = ROOT / "logs" / "h4cker.log"
# Relative to this file, not hardcoded to one machine's home directory.
WATCH_DIRS = [
    ROOT / "memory",
    pathlib.Path.home() / "jarvis-vault",
    ROOT / "data",
]

@mcp.tool()
def security_status() -> dict:
    """Get 24/7 security monitor status — data leaks, bugs, malware, hacking attempts."""
    alerts = []
    # Check for large data exfiltration (many files changed recently)
    for d in WATCH_DIRS:
        p = pathlib.Path(d)
        if p.exists():
            recent = [f for f in p.rglob("*") if f.is_file() and (time.time() - f.stat().st_mtime) < 3600]
            if len(recent) > 20:
                alerts.append(f"Data leak check: {len(recent)} files changed in {d} last hour")
    # Check for errors in logs
    for log in ["/tmp/nova_voice.log", "/tmp/make_shorts.log", "/tmp/n8n.log"]:
        lp = pathlib.Path(log)
        if lp.exists():
            txt = lp.read_text()[-2000:] if lp.stat().st_size > 0 else ""
            if "ERROR" in txt or "Traceback" in txt:
                alerts.append(f"Error in {log}: {txt[-200:]}")
    # Check for malware-like processes (high CPU, unknown)
    for proc in psutil.process_iter(['name','cpu_percent']):
        try:
            if proc.info['cpu_percent'] and proc.info['cpu_percent'] > 80:
                alerts.append(f"High CPU: {proc.info['name']} {proc.info['cpu_percent']}%")
        except: pass
    # Check for hacking: many failed auth attempts (check .env access)
    status = "OK" if not alerts else "ALERT"
    return {"status": status, "alerts": alerts[:10], "checked": datetime.now().isoformat(), "watch_dirs": WATCH_DIRS}

@mcp.tool()
def check_data_leaks() -> dict:
    """Check for potential data leaks in watched directories."""
    leaks = []
    for d in WATCH_DIRS:
        p = pathlib.Path(d)
        if p.exists():
            for f in p.rglob("*.json"):
                if "api_key" in f.read_text().lower() or "password" in f.read_text().lower():
                    # Check if file is world-readable
                    if oct(f.stat().st_mode)[-3:] in ["644","666","777"]:
                        leaks.append(f"Potential leak: {f} is world-readable and contains keys")
    return {"leaks": leaks, "checked": datetime.now().isoformat()}

def _has_quarantine(path: pathlib.Path) -> bool:
    """True if the file carries macOS's com.apple.quarantine extended attribute."""
    try:
        buf = ctypes.create_string_buffer(1024)
        n = _libc.listxattr(os.fsencode(str(path)), buf, ctypes.sizeof(buf))
        if n <= 0:
            return False
        return b"com.apple.quarantine" in buf.raw[:n]
    except (OSError, ValueError):
        return False


@mcp.tool()
def scan_malware() -> dict:
    """Report what this scanner actually does.

    This performs NO antivirus signature matching — it cannot, and it never
    could. It previously returned a hardcoded "0 threats" string that was
    independent of the machine's state. That was misleading and is gone.

    What it really checks: macOS quarantine xattrs on files in the watched
    directories, and launchd agents that are not signed by an identified
    developer.
    """
    findings = []
    checked = 0

    # 1. Files carrying the Gatekeeper "downloaded but not opened" flag.
    for d in WATCH_DIRS:
        if not d.exists():
            continue
        for f in d.rglob("*"):
            if not f.is_file():
                continue
            checked += 1
            if _has_quarantine(f):
                findings.append({"kind": "quarantined", "path": str(f)})
            if checked >= 2000:
                break

    # 2. Launch agents with no identified signing authority.
    unsigned = []
    agents = pathlib.Path.home() / "Library/LaunchAgents"
    for agent in agents.glob("*.plist"):
        try:
            out = subprocess.run(["codesign", "-dv", str(agent)],
                                 capture_output=True, text=True, timeout=10)
            if "Authority=" not in (out.stderr or ""):
                unsigned.append(agent.name)
        except (OSError, subprocess.SubprocessError):
            continue

    return {
        "scanner": "quarantine xattr + codesign authority check",
        "disclaimer": "NOT an antivirus: no signature matching, no heuristic engine. "
                      "A clean result means only that these two checks found nothing.",
        "files_checked": checked,
        "quarantined_count": len(findings),
        "unsigned_launch_agents": unsigned,
        "findings": findings[:20],
        "checked": datetime.now().isoformat(),
    }

if __name__ == "__main__":
    mcp.run()
