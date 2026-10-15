"""
Client configuration installer for Preflight.
Configures Preflight MCP server across AI coding assistants:
Claude Code, Claude Desktop, Cursor, and OpenCode.
"""

import os
import sys
import json
import shutil
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("preflight.client_installer")

SUPPORTED_CLIENTS = ["claude-code", "claude-desktop", "cursor", "opencode"]


class ClientConfigConflictError(Exception):
    """Raised when preflight is already configured and force=False."""
    pass


@dataclass
class InstallResult:
    client: str
    config_path: Path
    action: str  # "CREATED", "UPDATED"
    server_key: str
    command: str
    args: List[str]
    message: str


def resolve_executable_command() -> Tuple[str, List[str]]:
    """
    Resolve the most portable, robust command and arguments to launch Preflight.
    """
    # 1. Global PATH check
    global_bin = shutil.which("preflight")
    if global_bin:
        return "preflight", ["serve"]

    # 2. Virtualenv binary check
    exe_name = "preflight.exe" if sys.platform == "win32" else "preflight"
    venv_bin = Path(sys.executable).parent / exe_name
    if venv_bin.exists():
        return str(venv_bin), ["serve"]

    # 3. Fallback to sys.executable
    return sys.executable, ["-m", "preflight.cli", "serve"]


def get_config_path(
    client: str,
    is_global: bool = False,
    project_dir: Optional[Path] = None,
    home_dir: Optional[Path] = None,
) -> Path:
    """Resolve the platform-specific config file path for the given client."""
    home = home_dir or Path.home()
    proj = project_dir or Path.cwd()

    if client == "claude-code":
        claude_config_dir = os.environ.get("CLAUDE_CONFIG_DIR")
        if claude_config_dir:
            return Path(claude_config_dir) / ".claude.json"
        return home / ".claude.json"

    elif client == "claude-desktop":
        if sys.platform == "win32":
            appdata = os.environ.get("APPDATA")
            base = Path(appdata) if appdata else home / "AppData" / "Roaming"
            return base / "Claude" / "claude_desktop_config.json"
        elif sys.platform == "darwin":
            return home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        else:  # Linux / other
            xdg = os.environ.get("XDG_CONFIG_HOME")
            base = Path(xdg) if xdg else home / ".config"
            return base / "Claude" / "claude_desktop_config.json"

    elif client == "cursor":
        if is_global:
            return home / ".cursor" / "mcp.json"
        return proj / ".cursor" / "mcp.json"

    elif client == "opencode":
        if is_global:
            xdg = os.environ.get("XDG_CONFIG_HOME")
            base = Path(xdg) if xdg else home / ".config"
            return base / "opencode" / "opencode.json"

        # Check if project has .opencode folder
        if (proj / ".opencode").is_dir():
            return proj / ".opencode" / "opencode.json"
        return proj / "opencode.json"

    else:
        raise ValueError(f"Unknown client '{client}'. Supported clients: {', '.join(SUPPORTED_CLIENTS)}")


def merge_config_data(
    existing: Dict[str, Any],
    server_key: str,
    server_entry: Dict[str, Any],
    client: str,
    force: bool = False,
) -> Tuple[Dict[str, Any], str]:
    """
    Non-destructively merge server_entry into existing configuration.
    Returns (updated_dict, action) where action is 'CREATED' or 'UPDATED'.
    Preserves foreign keys and auto-prunes legacy prototype 'fact-dock' entries.
    """
    if not isinstance(existing, dict):
        data = {}
    else:
        data = dict(existing)

    # Determine container key: 'mcp' or 'mcpServers'
    if client == "opencode" and "mcp" in data and "mcpServers" not in data:
        container_key = "mcp"
        formatted_entry = {
            "type": "local",
            "command": [server_entry["command"]] + server_entry["args"],
            "enabled": True,
        }
    else:
        container_key = "mcpServers"
        formatted_entry = server_entry

    if container_key not in data or not isinstance(data[container_key], dict):
        data[container_key] = {}

    container = data[container_key]

    # Automatically clean up legacy prototype "fact-dock" key if present
    if "fact-dock" in container:
        del container["fact-dock"]
        logger.info("Auto-pruned legacy prototype 'fact-dock' server entry.")

    if server_key in container:
        if not force:
            raise ClientConfigConflictError(
                f"'{server_key}' is already configured in this file. Pass --force to overwrite."
            )
        action = "UPDATED"
    else:
        action = "CREATED"

    container[server_key] = formatted_entry
    return data, action


def atomic_write_json(config_path: Path, data: dict) -> None:
    """
    Atomically write JSON data preserving original file permissions
    and creating a .bak backup copy if the file already exists.
    """
    config_path.parent.mkdir(parents=True, exist_ok=True)

    exists = config_path.exists()
    orig_mode = None
    if exists:
        try:
            orig_mode = config_path.stat().st_mode
            shutil.copy2(config_path, config_path.with_name(config_path.name + ".bak"))
        except OSError as e:
            logger.debug(f"Backup copy skipped or failed: {e}")

    tmp = config_path.with_name(config_path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            pass

    if orig_mode is not None:
        try:
            os.chmod(tmp, orig_mode)
        except OSError:
            pass

    os.replace(tmp, config_path)


def install_client(
    client: str,
    is_global: bool = False,
    project_dir: Optional[Path] = None,
    home_dir: Optional[Path] = None,
    force: bool = False,
    command_override: Optional[str] = None,
    args_override: Optional[List[str]] = None,
) -> InstallResult:
    """Execute installation and configuration for a specified client."""
    config_path = get_config_path(
        client,
        is_global=is_global,
        project_dir=project_dir,
        home_dir=home_dir,
    )

    # Resolve executable
    if command_override:
        cmd, args = command_override, (args_override or ["serve"])
    else:
        cmd, args = resolve_executable_command()

    server_entry = {
        "command": cmd,
        "args": args,
    }

    server_key = "preflight"

    # Read existing
    existing_data: Dict[str, Any] = {}
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    existing_data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Existing config file at '{config_path}' contains invalid JSON: {e}")

    updated_data, action = merge_config_data(
        existing_data,
        server_key=server_key,
        server_entry=server_entry,
        client=client,
        force=force,
    )

    # Write back atomically with backup and permission preservation
    atomic_write_json(config_path, updated_data)

    return InstallResult(
        client=client,
        config_path=config_path,
        action=action,
        server_key=server_key,
        command=cmd,
        args=args,
        message=f"Successfully {action.lower()} Preflight MCP entry in {config_path}",
    )
