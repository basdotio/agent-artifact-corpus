"""mcp-server-rabbitmq 核心包入口与元数据定义.

@author Ateng
@since 2026-10-04
"""

from mcp_server_rabbitmq.cli import main
from mcp_server_rabbitmq.server import create_mcp_server

__version__ = "1.0.4"

__all__ = [
    "create_mcp_server",
    "main",
]
