"""DartLab MCP server public facade.

설정 정본은 사전 설치된 `dartlab` entry point 직접 호출이다.

```json
{
  "mcpServers": {
    "dartlab": {
      "command": "dartlab",
      "args": ["mcp"],
      "env": {"PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1"}
    }
  }
}
```
"""

from __future__ import annotations

# Namespace collision 가드 — `dartlab/mcp/` 디렉토리가 editable install 시 sys.path
# 의 'src/dartlab' 를 통해 standalone 'mcp' SDK 의 top-level 로 잘못 잡히는 경우
# 차단. 이 경로로 import 됐다면 sys.modules 에서 즉시 제거 후 ImportError 발생.
# transports.py / server.py 의 fallback 가 cleanup 후 standalone mcp 재 import.
if __name__ == "mcp":  # pragma: no cover
    import sys as _sys

    _sys.modules.pop("mcp", None)
    raise ImportError(
        "dartlab.mcp 는 standalone 'mcp' SDK 가 아님. "
        "site-packages 의 mcp 가 sys.path 에서 안 잡힘 — editable install layout 확인."
    )

from dartlab.mcp.config import installMcpConfig
from dartlab.mcp.protocol import (
    MCP_INSTRUCTIONS as _MCP_INSTRUCTIONS,
)
from dartlab.mcp.protocol import (
    advertisedTools as _advertisedTools,
)
from dartlab.mcp.protocol import (
    executeWorkspaceAgentTool as _executeWorkspaceAgentTool,
)
from dartlab.mcp.protocol import (
    recipeSkillsForPrompts as _recipeSkillsForPrompts,
)
from dartlab.mcp.protocol import (
    resourcePayload as _resourcePayload,
)
from dartlab.mcp.server import createServer
from dartlab.mcp.transports import (
    createSseApp,
    createStreamableHttpApp,
    runSse,
    runStdio,
    runStreamableHttp,
)

__all__ = [
    "createServer",
    "createSseApp",
    "createStreamableHttpApp",
    "installMcpConfig",
    "runSse",
    "runStdio",
    "runStreamableHttp",
]
