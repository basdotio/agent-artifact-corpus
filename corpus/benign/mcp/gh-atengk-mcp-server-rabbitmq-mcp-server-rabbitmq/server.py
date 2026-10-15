"""RabbitMQ FastMCP 服务实例装配与全量工具注册.

@author Ateng
@since 2026-10-04
"""

import logging
from collections.abc import Callable
from typing import Any

from mcp.server import MCPServer

from mcp_server_rabbitmq.tools import (
    rabbitmq_bind_queue,
    rabbitmq_declare_exchange,
    rabbitmq_declare_queue,
    rabbitmq_delete_exchange,
    rabbitmq_delete_queue,
    rabbitmq_get_messages,
    rabbitmq_get_queue,
    rabbitmq_list_bindings,
    rabbitmq_list_channels,
    rabbitmq_list_client_connections,
    rabbitmq_list_configured_brokers,
    rabbitmq_list_connections,
    rabbitmq_list_exchanges,
    rabbitmq_list_queues,
    rabbitmq_overview,
    rabbitmq_peek_messages,
    rabbitmq_ping,
    rabbitmq_publish_message,
    rabbitmq_purge_queue,
    rabbitmq_unbind_queue,
)

logger = logging.getLogger(__name__)

# FastMCP 类型别名，保持与规范及 ADR-0001 命名对齐
FastMCP = MCPServer

# 全量注册挂载的 MCP 运维与消息工具集
ALL_TOOLS: list[Callable[..., Any]] = [
    rabbitmq_list_connections,
    rabbitmq_list_configured_brokers,
    rabbitmq_ping,
    rabbitmq_overview,
    rabbitmq_list_exchanges,
    rabbitmq_declare_exchange,
    rabbitmq_delete_exchange,
    rabbitmq_list_queues,
    rabbitmq_get_queue,
    rabbitmq_declare_queue,
    rabbitmq_purge_queue,
    rabbitmq_delete_queue,
    rabbitmq_list_bindings,
    rabbitmq_bind_queue,
    rabbitmq_unbind_queue,
    rabbitmq_publish_message,
    rabbitmq_peek_messages,
    rabbitmq_get_messages,
    rabbitmq_list_client_connections,
    rabbitmq_list_channels,
]


def create_mcp_server(name: str = "atengk-mcp-server-rabbitmq") -> FastMCP:
    """装配 FastMCP 服务实例并挂载全量运维与消息管理工具.

    @param name 服务端应用名称，默认为 'atengk-mcp-server-rabbitmq'
    @return 已完成全部工具注册挂载的 FastMCP 服务端实例
    """
    server = FastMCP(
        name=name,
        instructions=(
            "🐰 生产级 RabbitMQ Model Context Protocol (MCP) 服务端。\n"
            "提供 AMQP 0-9-1 拓扑声明、消息无损采样、受控消费与排障诊断全套工具。"
        ),
    )

    # 循环遍历并挂载全部工具
    for tool_fn in ALL_TOOLS:
        server.add_tool(tool_fn)
        tool_name = getattr(tool_fn, "__name__", str(tool_fn))
        logger.debug("已成功挂载 MCP 工具: %s", tool_name)

    return server
