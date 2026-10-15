"""MCP client configuration helpers."""

from __future__ import annotations

import json
from pathlib import Path


def installMcpConfig(targetDir: str | None = None) -> str:
    """프로젝트에 .mcp.json을 자동 생성한다.

    Args:
        targetDir: `.mcp.json` 을 생성할 디렉터리. None 이면 현재 작업 디렉터리.

    Returns:
        str: 생성 또는 기존 등록 상태 메시지.

    Example:
        `message = installMcpConfig(".")`

    Raises:
        OSError: `.mcp.json` 쓰기에 실패할 때.
    """
    root = Path(targetDir) if targetDir else Path.cwd()
    mcpFile = root / ".mcp.json"

    config: dict = {}
    if mcpFile.exists():
        try:
            config = json.loads(mcpFile.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            config = {}

    servers = config.setdefault("mcpServers", {})
    if "dartlab" in servers:
        return f"이미 등록됨: {mcpFile}"

    servers["dartlab"] = {
        "command": "dartlab",
        "args": ["mcp"],
        "env": {"PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1"},
    }
    mcpFile.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    return f"생성 완료: {mcpFile}"
