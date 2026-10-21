#!/usr/bin/env python3
"""Deterministically package a PRIVATE plugin for an existing, authorized tunnel.

Reads only the tunnel ID supplied via environment; never reads runtime tokens,
private keys or the live host profile. The bundle is not a tunnel deployment.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "plugin/windanvil-commander"
ALLOWED_ID = re.compile(r"tunnel_[a-z0-9]{32}\Z")


def build(tunnel_id: str, destination: Path) -> None:
    if not ALLOWED_ID.fullmatch(tunnel_id):
        raise ValueError("Expected a verified tunnel_ ID with exactly 32 lowercase alphanumeric characters")
    plugin = json.loads((SOURCE / "plugin.json").read_text(encoding="utf-8"))
    if plugin.get("name") != "windanvil-commander":
        raise ValueError("Unexpected plugin name")
    mcp = json.loads((SOURCE / "mcp.template.json").read_text(encoding="utf-8"))
    item = mcp["mcpServers"]["windanvil-commander"]
    if item.get("type") != "streamable-http" or "url" in item or "server_url" in item:
        raise ValueError("A tunneled connection must not specify a public MCP URL")
    if item["extensions"]["com.openai"]["tunnelId"] != "TUNNEL_ID_PLACEHOLDER":
        raise ValueError("MCP template placeholder changed")
    item["extensions"]["com.openai"]["tunnelId"] = tunnel_id
    skill = (SOURCE / "skills/commander-ops/SKILL.md").read_text(encoding="utf-8")
    if not skill.startswith("---\nname: commander-ops\n"):
        raise ValueError("Invalid Commander skill metadata")
    subtitle = plugin["extensions"]["com.openai"]["interface"]["shortDescription"]
    if len(subtitle) > 30:
        raise ValueError("Plugin subtitle too long")
    files = {
        "windanvil-commander/plugin.json": json.dumps(plugin, indent=2, sort_keys=True) + "\n",
        "windanvil-commander/mcp.json": json.dumps(mcp, indent=2, sort_keys=True) + "\n",
        "windanvil-commander/skills/commander-ops/SKILL.md": skill,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.is_symlink():
        raise ValueError("Refusing symlinked archive destination")
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for filename, contents in sorted(files.items()):
            item = zipfile.ZipInfo(filename, date_time=(2026, 10, 19, 0, 0, 0))
            item.external_attr = 0o100644 << 16
            item.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(item, contents.encode("utf-8"))
    destination.chmod(0o600)
    verify = zipfile.ZipFile(destination)
    if set(verify.namelist()) != set(files):
        raise ValueError("Unexpected archive members")
    for member in verify.infolist():
        if member.filename.startswith("/") or ".." in Path(member.filename).parts:
            raise ValueError("Unsafe archive member")
    print(json.dumps({
        "result": "PACKAGED",
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "members": sorted(files),
        "credential_included": False,
        "connected_to_chatgpt": False,
    }, sort_keys=True))


if __name__ == "__main__":
    token = os.getenv("CONTROL_PLANE_TUNNEL_ID", "")
    target = Path(sys.argv[1]) if len(sys.argv) == 2 else ROOT / "dist/windanvil-commander-private.zip"
    try:
        os.umask(0o077)
        build(token, target)
    except (KeyError, OSError, ValueError) as exc:
        print("BLOCKED: " + str(exc)[:150], file=sys.stderr)
        sys.exit(1)
