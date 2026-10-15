#!/usr/bin/env python3
"""
MCP Server Installer Script
Installs the Vercel MCP Bridge to Claude Desktop and Cursor configurations
"""

import json
import os
import platform
import sys
from pathlib import Path

# INJECTED_SERVER_URL = None


def get_server_url():
    """Get server URL from injected value, command line arguments, or user input"""
    # Check if server URL was injected by the server
    injected_url = globals().get("INJECTED_SERVER_URL")
    if injected_url:
        return injected_url

    # Check if server URL was provided as argument
    if len(sys.argv) >= 2:
        return sys.argv[1].rstrip("/")

    # Ask user for server URL as fallback
    print("Please provide the server URL for the MCP bridge.")
    print("Example: https://mcp-fass.vercel.app")
    print()

    while True:
        server_url = input("Server URL: ").strip()
        if server_url:
            # Add https:// if no scheme provided
            if not server_url.startswith(("http://", "https://")):
                server_url = "https://" + server_url
            return server_url.rstrip("/")
        print("Please enter a valid server URL.")


def get_api_key():
    """Get optional API key from user input"""
    print("Optional: Enter an API key for authentication (leave empty to skip):")
    api_key = input("API Key: ").strip()
    return api_key if api_key else None


def get_config_paths():
    """Get the config file paths for Claude Desktop and Cursor"""
    system = platform.system()

    if system == "Darwin":  # macOS
        claude_config = (
            Path.home()
            / "Library/Application Support/Claude/claude_desktop_config.json"
        )
        cursor_config = Path.home() / ".cursor/mcp.json"
    elif system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        claude_config = Path(appdata) / "Claude/claude_desktop_config.json"
        cursor_config = Path.home() / ".cursor/mcp.json"
    else:  # Linux and others
        claude_config = Path.home() / ".config/Claude/claude_desktop_config.json"
        cursor_config = Path.home() / ".cursor/mcp.json"

    return claude_config, cursor_config


def load_or_create_config(config_path):
    """Load existing config or create a new one"""
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            print(f"Warning: Could not read {config_path}, creating new config")

    # Create new config structure
    return {"mcpServers": {}}


def save_config(config_path, config_data):
    """Save config to file, creating directories if needed"""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config_data, f, indent=2)


def get_uv_command():
    """Get the uv command path"""
    # Common uv installation paths
    possible_paths = [
        "/opt/homebrew/bin/uv",  # Homebrew on macOS
        "/usr/local/bin/uv",  # Manual install
        "uv",  # In PATH
    ]

    for path in possible_paths:
        if Path(path).exists() or path == "uv":
            return path

    return "uv"  # Fallback


def install_to_config(config_path, server_url, bridge_url, server_name, api_key=None):
    """Install MCP server configuration to a config file"""
    config = load_or_create_config(config_path)

    # Ensure mcpServers exists
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    # Use consistent argument format for both clients
    # The extra quotes were causing issues with argument parsing
    mcp_version_arg = "mcp>=1.0.0"

    # Build server configuration
    server_config = {
        "command": get_uv_command(),
        "args": ["run", "--with", mcp_version_arg, bridge_url, server_url],
    }

    # Add environment variables if API key is provided
    if api_key:
        server_config["env"] = {"MCP_API_KEY": api_key}

    # Add our server configuration
    config["mcpServers"][server_name] = server_config

    save_config(config_path, config)
    return True


def main():
    """Install MCP server to local configurations"""

    # Get server URL
    server_url = get_server_url()
    bridge_url = f"{server_url}/bridge.py"

    # Get optional API key
    api_key = get_api_key()

    # Extract server name from URL for config
    from urllib.parse import urlparse

    parsed = urlparse(server_url)
    hostname = parsed.hostname or "unknown"
    if hostname.endswith(".vercel.app"):
        server_name = hostname[:-11]  # Remove '.vercel.app'
    else:
        server_name = hostname.replace(".", "_").replace("-", "_")

    print("MCP Server Installer")
    print("===================")
    print()
    print("This will install the MCP Bridge to your local client configurations.")
    print(f"Server URL: {server_url}")
    print(f"Bridge URL: {bridge_url}")
    print(f"Server name: {server_name}")
    if api_key:
        print(f"API Key: {'*' * len(api_key)}")  # Hide the actual key
    else:
        print("API Key: Not set")
    print()

    # Ask for confirmation
    while True:
        response = (
            input("Do you want to proceed with the installation? (y/n): ")
            .lower()
            .strip()
        )
        if response in ["y", "yes"]:
            break
        elif response in ["n", "no"]:
            print("Installation cancelled.")
            sys.exit(0)
        else:
            print("Please enter 'y' for yes or 'n' for no.")

    print()

    # Get config paths
    claude_config, cursor_config = get_config_paths()
    installed_to = []

    # Install to Claude Desktop
    try:
        install_to_config(claude_config, server_url, bridge_url, server_name, api_key)
        print(f"✓ Installed to Claude Desktop: {claude_config}")
        installed_to.append("Claude Desktop")
    except Exception as e:
        print(f"✗ Failed to install to Claude Desktop: {e}")

    # Install to Cursor (if config directory exists)
    if cursor_config.parent.exists():
        try:
            install_to_config(
                cursor_config, server_url, bridge_url, server_name, api_key
            )
            print(f"✓ Installed to Cursor: {cursor_config}")
            installed_to.append("Cursor")
        except Exception as e:
            print(f"✗ Failed to install to Cursor: {e}")
    else:
        print("• Cursor config directory not found, skipping")

    print()
    if installed_to:
        print("Installation completed successfully!")
        print(f"Installed to: {', '.join(installed_to)}")
        print()
        print("Please restart your client(s) to use the MCP server.")
    else:
        print("Installation failed - no configurations were updated.")
        sys.exit(1)


if __name__ == "__main__":
    main()
