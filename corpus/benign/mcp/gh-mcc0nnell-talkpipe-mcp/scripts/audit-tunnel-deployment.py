#!/usr/bin/env python3
"""Audit a local Secure MCP Tunnel profile without reading any runtime key bytes.

Deployment authority is deliberately split: reproducible config is tracked;
user authorization, live runtime credentials, receipts, and private keys are not.
"""
import json
import os
from pathlib import Path
import re
import sys

PROFILE_NAME = "windanvil-commander"
TUNNEL_ID = re.compile(r"^tunnel_[A-Za-z0-9_-]{10,128}$")


def mode(path: Path) -> int:
    return path.stat().st_mode & 0o777


def quote_value(blob: str, field: str) -> str:
    matches = re.findall(r"(?m)^\s*" + re.escape(field) + r':\s*"([^"\n]*)"\s*$', blob)
    if len(matches) != 1:
        raise ValueError("missing or ambiguous profile setting: " + field)
    return matches[0]


def check(profile_dir: Path, root: Path, python: Path) -> dict:
    profile = profile_dir / (PROFILE_NAME + ".yaml")
    if profile_dir.is_symlink() or not profile_dir.is_dir():
        raise ValueError("profile directory missing or symlinked")
    if mode(profile_dir) != 0o700:
        raise ValueError("profile directory must be 0700")
    if profile.is_symlink() or not profile.is_file() or mode(profile) != 0o600:
        raise ValueError("tunnel profile missing, symlinked, or not 0600")
    if profile.stat().st_uid != os.getuid():
        raise ValueError("tunnel profile must be owned by the current user")
    content = profile.read_text(encoding="utf-8")
    tunnel_id = quote_value(content, "tunnel_id")
    if not TUNNEL_ID.fullmatch(tunnel_id) or "REPLACE" in tunnel_id:
        raise ValueError("invalid tunnel identifier")
    if quote_value(content, "base_url") != "https://api.openai.com":
        raise ValueError("unexpected control-plane URL")
    if quote_value(content, "listen_addr") != "127.0.0.1:0":
        raise ValueError("health listener must use ephemeral loopback port")
    if not re.search(r"(?m)^\s*open_browser:\s*false\s*$", content):
        raise ValueError("unexpected admin UI behavior")
    expected_key = profile_dir / "windanvil-runtime-key"
    if quote_value(content, "api_key") != "file:" + str(expected_key):
        raise ValueError("key must be a private file reference, not inline or environment")
    expected_command = str(python) + " -u " + str(root / "windanvil_commander_mcp.py")
    if quote_value(content, "command") != expected_command:
        raise ValueError("MCP command points outside the expected Commander server")
    if "sk-proj-" in content or "sk-" in content:
        raise ValueError("possible plaintext key inside tunnel profile")
    if not python.is_file() or not root.joinpath("windanvil_commander_mcp.py").is_file():
        raise ValueError("local Commander runtime missing")
    if expected_key.exists() or expected_key.is_symlink():
        if expected_key.is_symlink() or not expected_key.is_file():
            raise ValueError("runtime key path is unsafe")
        if mode(expected_key) != 0o600 or expected_key.stat().st_uid != os.getuid():
            raise ValueError("runtime key mode or owner is unsafe")
        key_state = "file-present-secure-permissions"
    else:
        key_state = "not-provisioned"
    return {
        "result": "PASS",
        "profile": PROFILE_NAME,
        "tunnel_id_configured": True,
        "stdio_command_verified": True,
        "loopback_only_health": True,
        "runtime_key": key_state,
        "remote_connected": False,
        "note": "Configuration audit is not a live tunnel or ChatGPT connectivity test",
    }


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    profile_dir = Path(os.environ.get("TUNNEL_CLIENT_PROFILE_DIR",
                                      str(Path.home() / ".config/tunnel-client")))
    python = Path(os.environ.get("TALKPIPE_PYTHON",
                                 str(Path.home() / "lab/talkpipe-runtime/.venv/bin/python")))
    try:
        print(json.dumps(check(profile_dir, root, python), sort_keys=True))
    except (ValueError, OSError, UnicodeError) as exc:
        print(json.dumps({"result": "BLOCKED", "reason": str(exc)[:160],
                          "remote_connected": False}, sort_keys=True), file=sys.stderr)
        sys.exit(1)
