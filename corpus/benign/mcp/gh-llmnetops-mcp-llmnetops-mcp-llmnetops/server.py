"""MCP server exposing read-only network device operations."""
from __future__ import annotations

import argparse
import os
import re
import signal
import sys
from pathlib import Path

import inspect

from fastmcp import FastMCP
from fastmcp.tools.function_tool import FunctionTool

from . import __version__
from .config import APP_CONFIG_DIR, DeviceConfig, load_devices
from .platforms import CommandDef, Platform, list_platforms as _list_platforms
from .ssh_client import DeviceError, DeviceSession

MAX_OUTPUT_CHARS = 50_000
TARGET_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.\-:]*$")

mcp = FastMCP(
    "mcp-llmnetops",
    instructions=(
        "Read-only network device operations over SSH. "
        "Every whitelisted device command is exposed as its own tool, named "
        "<platform>_<command> (e.g. cisco_ios_show_ip_route, "
        "mikrotik_ros7_ip_route_print, huawei_vrp_display_version). "
        "Workflow: call list_devices to see configured devices, then call the "
        "tool matching the device's platform. Ping tools additionally require "
        "a 'target' argument (hostname or IP address). "
        "Commands are strictly whitelisted per platform."
    ),
)

_sessions: dict[str, DeviceSession] = {}
_config_override: str | None = None


# -- helpers -----------------------------------------------------------------


def _devices() -> dict[str, DeviceConfig]:
    return load_devices(_config_override)


def _get_device(name: str) -> DeviceConfig:
    devices = _devices()
    if name not in devices:
        available = ", ".join(sorted(devices)) or "(none configured)"
        raise ValueError(f"Unknown device '{name}'. Configured devices: {available}")
    return devices[name]


def _session_for(device: DeviceConfig) -> DeviceSession:
    if device.name not in _sessions:
        _sessions[device.name] = DeviceSession(device)
    return _sessions[device.name]


def _match_command(platform: Platform, command: str):
    norm = " ".join(command.strip().lower().split())
    for c in platform.commands:
        if c.name.lower() == norm:
            return c
        base = c.command.split("{")[0].strip().lower()
        if base == norm:
            return c
    return None


def _truncate(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[:MAX_OUTPUT_CHARS] + f"\n\n... [truncated {len(text) - MAX_OUTPUT_CHARS} characters]"


async def _run_fixed_command(
    device_name: str, platform: Platform, cmd: CommandDef, target: str = ""
) -> str:
    """Run one whitelisted command on a device and return its output."""
    dev = _get_device(device_name)
    if dev.platform != platform.key:
        raise ValueError(
            f"Device '{dev.name}' uses platform '{dev.platform}', but this tool is "
            f"for '{platform.key}' devices. Use the matching {dev.platform} tool instead."
        )
    if cmd.requires_target:
        if not target:
            raise ValueError(f"Command '{cmd.name}' requires a 'target' (hostname or IP address).")
        if not TARGET_RE.match(target):
            raise ValueError(f"Invalid target '{target}'. Use a plain hostname or IP address.")
        actual = cmd.command.format(target=target)
    else:
        actual = cmd.command

    session = _session_for(dev)
    try:
        output = await session.run(actual)
    except DeviceError as e:
        raise ValueError(str(e)) from e
    return _truncate(output) if output else "(no output)"


# -- tools ---------------------------------------------------------------------


async def list_devices() -> str:
    """List all configured network devices with host, port, and platform."""
    devices = _devices()
    if not devices:
        return (
            "No devices configured. Create a devices.yaml (see devices.example.yaml) "
            "and point to it with --config or the MCP_LLMNETOPS_CONFIG environment variable."
        )
    lines = []
    for d in devices.values():
        lines.append(f"- {d.name}: {d.host}:{d.port} [{d.platform}] user={d.username}")
    return "\n".join(lines)


async def list_platforms() -> str:
    """List all supported device platforms and their command counts."""
    lines = []
    for p in _list_platforms():
        lines.append(f"- {p.key}: {p.description} ({len(p.commands)} commands)")
    return "\n".join(lines)


async def test_connection(device: str) -> str:
    """Test the SSH connection to a device (connects and opens a shell).

    Args:
        device: Device name as returned by list_devices.
    """
    dev = _get_device(device)
    session = _session_for(dev)
    try:
        await session.connect()
    except DeviceError as e:
        return f"FAILED: {e}"
    return f"OK: connected to {dev.name} ({dev.host}:{dev.port}) as {dev.username}"


# -- permissive tool ---------------------------------------------------------------


class PermissiveFunctionTool(FunctionTool):
    """A FunctionTool that tolerates extra (unknown) keyword arguments.

    Some MCP clients/agents pass extra arguments a tool does not declare.
    Instead of failing with 'unexpected_keyword_argument', this subclass
    silently drops unknown keys before validation so the call still runs.
    """

    async def run(self, arguments):
        sig = inspect.signature(self.fn)
        valid = {p.name for p in sig.parameters.values()}
        filtered = {k: v for k, v in arguments.items() if k in valid}
        return await super().run(filtered)


def _register_meta_tools() -> None:
    """Register the meta tools as permissive tools (tolerate extra args)."""
    for fn in (list_devices, list_platforms, test_connection):
        tool = PermissiveFunctionTool.from_function(fn, name=fn.__name__)
        mcp.add_tool(tool)


_register_meta_tools()


# -- per-command tools (one MCP tool per whitelisted command) -------------------


def _command_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _build_command_tool(platform: Platform, cmd: CommandDef):
    """Build the async tool function for one whitelisted command."""
    if cmd.requires_target:

        async def runner(device: str, target: str) -> str:
            return await _run_fixed_command(device, platform, cmd, target)

        runner.__doc__ = (
            f"{cmd.description} (runs `{cmd.command}` on {platform.description} devices).\n\n"
            "Args:\n"
            "    device: Device name as returned by list_devices.\n"
            "    target: Hostname or IP address to ping."
        )
    else:

        async def runner(device: str) -> str:
            return await _run_fixed_command(device, platform, cmd)

        runner.__doc__ = (
            f"{cmd.description} (runs `{cmd.command}` on {platform.description} devices).\n\n"
            "Args:\n"
            "    device: Device name as returned by list_devices."
        )
    return runner


def _register_command_tools() -> None:
    """Register one MCP tool per whitelisted command, for every platform."""
    for platform in _list_platforms():
        plat = platform.key.replace("-", "_")
        for cmd in platform.commands:
            tool_name = f"{plat}_{_command_slug(cmd.name)}"
            fn = _build_command_tool(platform, cmd)
            tool = PermissiveFunctionTool.from_function(fn, name=tool_name)
            mcp.add_tool(tool)


_register_command_tools()


# -- daemon helpers ----------------------------------------------------------------


def _daemonize(pid_file: Path, log_file: Path) -> None:
    """Detach from the controlling terminal (Unix double-fork) and redirect stdio.

    After this returns, the caller is the daemon (session leader, no controlling
    terminal). stdin comes from /dev/null; stdout/stderr go to ``log_file``.
    The daemon's PID is written to ``pid_file``.
    """
    if os.name != "posix":
        raise SystemExit("--daemon is only supported on Unix/Linux")
    if os.fork() > 0:
        os._exit(0)
    os.setsid()
    if os.fork() > 0:
        os._exit(0)
    sys.stdout.flush()
    sys.stderr.flush()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_fd = os.open(str(log_file), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    devnull = os.open(os.devnull, os.O_RDONLY)
    os.dup2(devnull, 0)
    os.dup2(log_fd, 1)
    os.dup2(log_fd, 2)
    os.close(devnull)
    if log_fd > 2:
        os.close(log_fd)
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()))


def _stop_daemon(pid_file: Path) -> None:
    """Send SIGTERM to the daemon recorded in the PID file."""
    if not pid_file.exists():
        raise SystemExit(f"No PID file at {pid_file}; is the daemon running?")
    try:
        pid = int(pid_file.read_text().strip())
    except ValueError:
        raise SystemExit(f"Invalid PID file at {pid_file}")
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pid_file.unlink(missing_ok=True)
        print(f"Process {pid} not running; removed stale PID file.")
        return
    except PermissionError:
        raise SystemExit(f"Permission denied sending SIGTERM to pid {pid}")
    except OSError as e:
        # Windows: os.kill on a dead pid raises OSError (WinError 87).
        if getattr(e, "winerror", None) == 87:
            pid_file.unlink(missing_ok=True)
            print(f"Process {pid} not running; removed stale PID file.")
            return
        raise
    print(f"Sent SIGTERM to pid {pid}.")


# -- entry point -----------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mcp-llmnetops",
        description="MCP server for read-only network device operations",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to devices.yaml (default: $MCP_LLMNETOPS_CONFIG, ./devices.yaml, "
        "~/.config/mcp-llmnetops/devices.yaml)",
    )
    parser.add_argument(
        "--transport",
        default="streamable-http",
        choices=["stdio", "sse", "streamable-http"],
        help="MCP transport (default: streamable-http, served at http://<host>:<port>/mcp)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Bind address for HTTP transports (default: 0.0.0.0 = all interfaces)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5758,
        help="Port for HTTP transports (default: 5758)",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run in the background as a daemon (Unix/Linux only)",
    )
    parser.add_argument(
        "--pid-file",
        default=None,
        help="PID file path (default: ~/.config/mcp-llmnetops/mcp-llmnetops.pid)",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Log file for daemon stdout/stderr (default: ~/.config/mcp-llmnetops/mcp-llmnetops.log)",
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop a running daemon (reads the PID file and sends SIGTERM)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args()

    pid_file = Path(args.pid_file).expanduser() if args.pid_file else APP_CONFIG_DIR / "mcp-llmnetops.pid"
    log_file = Path(args.log_file).expanduser() if args.log_file else APP_CONFIG_DIR / "mcp-llmnetops.log"

    if args.stop:
        _stop_daemon(pid_file)
        return

    if args.daemon:
        if args.transport == "stdio":
            raise SystemExit("--daemon requires an HTTP transport (sse or streamable-http)")
        _daemonize(pid_file, log_file)
        print(
            f"[mcp-llmnetops] daemon started, pid={os.getpid()}, "
            f"listening on http://{args.host}:{args.port}/mcp"
        )

    global _config_override
    _config_override = args.config

    if args.transport in {"sse", "streamable-http"}:
        mcp.run(transport=args.transport, host=args.host, port=args.port)
    else:
        mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
