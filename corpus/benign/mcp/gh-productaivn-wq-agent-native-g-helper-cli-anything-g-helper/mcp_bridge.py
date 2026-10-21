"""FastMCP Server Adapter for cli-anything-g_helper."""
import subprocess
import json
import sys
from typing import Optional

try:
    from mcp.server.fastmcp import FastMCP
except Exception:
    try:
        from mcp.server.mcpserver import MCPServer as FastMCP
    except Exception:
        class FastMCP:
            def __init__(self, name): self.name = name
            def tool(self): return lambda f: f
            def run(self): pass

mcp = FastMCP("g_helper-agent-harness")

def _run_cli(args: list[str]) -> str:
    """Helper to run cli-anything-g_helper commands and capture stdout."""
    cmd = [sys.executable, "-m", "cli_anything_g_helper.cli", "--json"] + args
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.stdout or res.stderr

# ==========================================
# Core & Daemon Tools
# ==========================================
@mcp.tool()
def get_daemon_status() -> str:
    """Inspect backend daemon status and hardware telemetry via cli-anything-g_helper."""
    return _run_cli(["daemon", "status"])

@mcp.tool()
def undo_last_action() -> str:
    """Revert last harness state modification via Memento stack."""
    return _run_cli(["session", "undo"])

# ==========================================
# 1. Performance Profile Tools
# ==========================================
@mcp.tool()
def set_performance_mode(mode: str) -> str:
    """Set ASUS performance profile (options: silent, balanced, turbo) via OpenJev discrete selection."""
    return _run_cli(["profile", "set", "--mode", mode])

@mcp.tool()
def get_performance_profile() -> str:
    """Get active ASUS performance profile and full hardware state."""
    return _run_cli(["profile", "get"])

# ==========================================
# 2. GPU Mode Tools (MUX & dGPU Power)
# ==========================================
@mcp.tool()
def set_gpu_mode(mode: str) -> str:
    """Set GPU mode (options: eco [dGPU off], standard [hybrid], ultimate [MUX direct dGPU])."""
    return _run_cli(["gpu", "set-mode", "--mode", mode])

@mcp.tool()
def get_gpu_mode() -> str:
    """Get active GPU mode (Eco, Standard, Ultimate) and MUX status."""
    return _run_cli(["gpu", "get"])

# ==========================================
# 3. Battery Health & Charging Limit Tools
# ==========================================
@mcp.tool()
def set_battery_limit(percent: int) -> str:
    """Set ASUS battery charge threshold (options: 60, 80, 100)."""
    return _run_cli(["battery", "set-limit", "--percent", str(percent)])

@mcp.tool()
def get_battery_limit() -> str:
    """Get active battery charge threshold percentage."""
    return _run_cli(["battery", "get-limit"])

# ==========================================
# 4. Display Refresh Rate & Overdrive Tools
# ==========================================
@mcp.tool()
def set_display_config(refresh_rate: Optional[int] = None, overdrive: Optional[bool] = None, auto: Optional[bool] = None) -> str:
    """Configure screen refresh rate (60, 120, 165, -1), LCD overdrive, and AC/DC auto-switch."""
    args = ["display", "set"]
    if refresh_rate is not None:
        args += ["--refresh-rate", str(refresh_rate)]
    if overdrive is not None:
        args += ["--overdrive" if overdrive else "--no-overdrive"]
    if auto is not None:
        args += ["--auto" if auto else "--no-auto"]
    return _run_cli(args)

@mcp.tool()
def get_display_config() -> str:
    """Get current screen refresh rate, max frequency, overdrive, and auto-switching settings."""
    return _run_cli(["display", "get"])

# ==========================================
# 5. Keyboard Backlight & Aura RGB Tools
# ==========================================
@mcp.tool()
def set_keyboard_backlight(brightness: Optional[int] = None, aura_mode: Optional[str] = None) -> str:
    """Configure keyboard backlight brightness (0-3) and Aura effect (static, breathing, color_cycle, strobing)."""
    args = ["keyboard", "set"]
    if brightness is not None:
        args += ["--brightness", str(brightness)]
    if aura_mode is not None:
        args += ["--aura", aura_mode]
    return _run_cli(args)

@mcp.tool()
def get_keyboard_backlight() -> str:
    """Get active keyboard brightness and Aura RGB configuration."""
    return _run_cli(["keyboard", "get"])

# ==========================================
# 6. Power Limit Tuning Tools
# ==========================================
@mcp.tool()
def set_power_limits(total_w: Optional[int] = None, cpu_w: Optional[int] = None, slow_w: Optional[int] = None, fast_w: Optional[int] = None) -> str:
    """Set custom CPU and platform wattage limits (SPL, sPPT, fPPT)."""
    args = ["power", "set-limits"]
    if total_w is not None:
        args += ["--total-w", str(total_w)]
    if cpu_w is not None:
        args += ["--cpu-w", str(cpu_w)]
    if slow_w is not None:
        args += ["--slow-w", str(slow_w)]
    if fast_w is not None:
        args += ["--fast-w", str(fast_w)]
    return _run_cli(args)

@mcp.tool()
def get_power_limits() -> str:
    """Get active platform wattage limits."""
    return _run_cli(["power", "get-limits"])

if __name__ == "__main__":
    mcp.run()
