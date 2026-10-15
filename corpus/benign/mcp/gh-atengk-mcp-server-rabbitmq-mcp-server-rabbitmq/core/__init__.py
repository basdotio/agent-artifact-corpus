"""RabbitMQ MCP 服务端核心驱动与基础设施模块.

@author Ateng
@since 2026-10-04
"""

from mcp_server_rabbitmq.core.amqp_client import get_amqp_channel, get_amqp_connection
from mcp_server_rabbitmq.core.config import (
    RabbitMQConnectionConfig,
    RabbitMQServerConfig,
    build_amqp_url,
    build_management_url,
    get_global_config,
    load_config,
    mask_dict_credentials,
    mask_url,
    merge_amqp_url,
    merge_management_url,
    parse_amqp_url,
    parse_management_url,
    reset_global_config,
    set_global_config,
)
from mcp_server_rabbitmq.core.management_client import ManagementClient
from mcp_server_rabbitmq.core.security import (
    WriteGateError,
    check_confirmation,
    check_write_permission,
    require_write,
)

__all__ = [
    "ManagementClient",
    "RabbitMQConnectionConfig",
    "RabbitMQServerConfig",
    "WriteGateError",
    "build_amqp_url",
    "build_management_url",
    "check_confirmation",
    "check_write_permission",
    "get_amqp_channel",
    "get_amqp_connection",
    "get_global_config",
    "load_config",
    "mask_dict_credentials",
    "mask_url",
    "merge_amqp_url",
    "merge_management_url",
    "parse_amqp_url",
    "parse_management_url",
    "require_write",
    "reset_global_config",
    "set_global_config",
]
