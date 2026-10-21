"""One-click MCP setup for open-computer-skills (via Alphalogic server).

Merges {"alphalogic": {...}} into each client's own config, backing up to *.bak.
Clients: opencode, claude-code, codex, gemini-cli.

Usage:
  python scripts/install.py --server "C:/path/to/backend/mcp_server.py" --clients opencode,claude-code
"""
import argparse, json, sys
from pathlib import Path

def backup(path: Path):
    if path.exists():
        bak = path.with_name(path.name + ".bak")
        bak.write_bytes(path.read_bytes())
        return str(bak)
    return None

def merge_json(path: Path, key: str, name: str, entry: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            data = {}
    except (OSError, json.JSONDecodeError):
        data = {}
    data.setdefault(key, {})[name] = entry
    bak = backup(path)
    path.write_text(json.dumps(data, indent=2))
    return str(path), bak

def merge_toml(path: Path, header: str, lines: list):
    import re
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        text = path.read_text()
    except OSError:
        text = ""
    if text and not text.endswith("\n"):
        text += "\n"
    section = header + "\n" + "\n".join(lines) + "\n"
    pat = re.compile(r"^" + re.escape(header) + r"\s*\n(?:^(?!\[).*\n?)*", re.MULTILINE)
    text = pat.sub(section, text) if pat.search(text) else (text + ("\n" if text and not text.endswith("\n\n") else "") + section)
    bak = backup(path)
    path.write_text(text)
    return str(path), bak

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", required=True, help="absolute path to Alphalogic backend/mcp_server.py")
    ap.add_argument("--clients", default="opencode,claude-code,codex,gemini-cli")
    ap.add_argument("--python", default=sys.executable)
    args = ap.parse_args()
    server = str(Path(args.server).resolve())
    if not Path(server).exists():
        sys.exit(f"server not found: {server}")
    home = Path.home()
    stdio = {"command": args.python, "args": [server]}
    for c in [x.strip() for x in args.clients.split(",") if x.strip()]:
        if c == "claude-code":
            p, b = merge_json(home / ".claude.json", "mcpServers", "alphalogic", stdio)
        elif c == "codex":
            p, b = merge_toml(home / ".codex" / "config.toml", "[mcp_servers.alphalogic]",
                              [f'command = "{Path(args.python).as_posix()}"', f'args = ["{Path(server).as_posix()}"]'])
        elif c == "gemini-cli":
            p, b = merge_json(home / ".gemini" / "settings.json", "mcpServers", "alphalogic", stdio)
        elif c == "opencode":
            p, b = merge_json(home / ".config" / "opencode" / "opencode.json", "mcp", "alphalogic",
                              {"type": "local", "command": [args.python, server], "enabled": True})
        else:
            print(f"skip unknown client: {c}")
            continue
        print(f"{c}: {p} (backup: {b})")
    print("Done. Restart your AI app.")

if __name__ == "__main__":
    main()
