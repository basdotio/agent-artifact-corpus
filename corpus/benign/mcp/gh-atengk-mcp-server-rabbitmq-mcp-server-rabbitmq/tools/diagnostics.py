"""RabbitMQ 客户端连接与活跃信道排障诊断工具实现.

@author Ateng
@since 2026-10-04
"""

import logging
from typing import Any

import httpx

from mcp_server_rabbitmq.core.config import get_global_config, mask_dict_credentials, mask_url
from mcp_server_rabbitmq.core.management_client import ManagementClient

logger = logging.getLogger(__name__)


async def rabbitmq_list_client_connections(
    connection: str = "default",
    vhost: str | None = None,
) -> dict[str, Any]:
    """查询外部微服务客户端 TCP 连接列表、信道数与收发吞吐速率.

    [注意区分] 本工具用于排查外部应用连入 RabbitMQ 的物理 TCP 链路与信道泄露；
    若要查看 MCP 服务端自身配置的目标 Broker 实例清单，请调用 rabbitmq_list_connections 或 rabbitmq_list_configured_brokers。
    未配置 Management API 时依据 ADR-0001 优雅降级。

    @param connection 目标 Broker 连接配置别名，默认为 'default'
    @param vhost 可选的虚拟主机名称过滤
    @return 结构化的客户端连接诊断清单
    """
    # 1. 校验配置并执行优雅降级检查
    config = get_global_config()
    conn_cfg = config.get_connection(connection)

    if not conn_cfg.management_url:
        return {
            "status": "degraded",
            "connection": connection,
            "message": (
                "未配置 RabbitMQ Management API 访问地址 (MCP_RABBITMQ_MANAGEMENT_URL)，"
                "无法采集客户端连接诊断指标，已优雅降级。"
            ),
            "client_connections": [],
            "total": 0,
        }

    # 2. 请求 Management API 采集外部连接指标
    client = ManagementClient(conn_cfg.management_url)
    try:
        raw_items = await client.list_connections(vhost=vhost)

        # 3. 提取核心性能指标并完成敏感属性脱敏（防御嵌套为 None 字段）
        cleaned_items: list[dict[str, Any]] = []
        for item in raw_items:
            recv_details = item.get("recv_oct_details") or {}
            send_details = item.get("send_oct_details") or {}
            recv_rate = recv_details.get("rate", 0.0)
            send_rate = send_details.get("rate", 0.0)
            raw_props = item.get("client_properties")
            cleaned_items.append({
                "name": item.get("name"),
                "node": item.get("node"),
                "host": item.get("host"),
                "port": item.get("port"),
                "peer_host": item.get("peer_host"),
                "peer_port": item.get("peer_port"),
                "protocol": item.get("protocol"),
                "auth_mechanism": item.get("auth_mechanism"),
                "ssl": item.get("ssl", False),
                "user": item.get("user"),
                "vhost": item.get("vhost"),
                "state": item.get("state"),
                "channels": item.get("channels", 0),
                "recv_oct": item.get("recv_oct", 0),
                "send_oct": item.get("send_oct", 0),
                "recv_rate": recv_rate,
                "send_rate": send_rate,
                "connected_at": item.get("connected_at"),
                "client_properties": mask_dict_credentials(raw_props),
            })

        return {
            "status": "ok",
            "connection": connection,
            "total": len(cleaned_items),
            "client_connections": cleaned_items,
        }
    except httpx.HTTPStatusError as err:
        logger.warning("请求客户端连接指标返回异常 HTTP 状态 [%s]: %s", connection, err)
        return {
            "status": "error",
            "connection": connection,
            "error": "HTTPStatusError",
            "message": f"Management API 请求失败，状态码: {err.response.status_code}",
            "client_connections": [],
            "total": 0,
        }
    except (httpx.RequestError, OSError, TimeoutError) as err:
        safe_msg = mask_url(str(err)) or str(err)
        logger.warning("请求客户端连接指标发生网络错误 [%s]: %s", connection, safe_msg)
        return {
            "status": "error",
            "connection": connection,
            "error": type(err).__name__,
            "message": f"无法连通 RabbitMQ Management API: {safe_msg}",
            "client_connections": [],
            "total": 0,
        }


async def rabbitmq_list_channels(
    connection: str = "default",
    vhost: str | None = None,
    connection_name: str | None = None,
) -> dict[str, Any]:
    """查询活跃信道指标、未确认消息堆积、Prefetch 与消费活跃度.

    用于精准排查客户端信道未确认消息积压、消费阻塞与信道异常。
    未配置 Management API 时依据 ADR-0001 优雅降级。

    @param connection 目标 Broker 连接配置别名，默认为 'default'
    @param vhost 可选的虚拟主机名称过滤
    @param connection_name 可选的客户端连接标识过滤
    @return 结构化的信道诊断清单
    """
    # 1. 校验配置并执行优雅降级检查
    config = get_global_config()
    conn_cfg = config.get_connection(connection)

    if not conn_cfg.management_url:
        return {
            "status": "degraded",
            "connection": connection,
            "message": (
                "未配置 RabbitMQ Management API 访问地址 (MCP_RABBITMQ_MANAGEMENT_URL)，"
                "无法采集信道诊断指标，已优雅降级。"
            ),
            "channels": [],
            "total": 0,
        }

    # 2. 请求 Management API 采集信道诊断指标
    client = ManagementClient(conn_cfg.management_url)
    try:
        raw_items = await client.list_channels(vhost=vhost, connection=connection_name)

        # 3. 提取未确认消息数、预取限额与速率指标（防御嵌套为 None 字段）
        cleaned_channels: list[dict[str, Any]] = []
        for item in raw_items:
            conn_details = item.get("connection_details") or {}
            msg_stats = item.get("message_stats") or {}
            publish_details = msg_stats.get("publish_details") or {}
            deliver_details = msg_stats.get("deliver_get_details") or {}
            ack_details = msg_stats.get("ack_details") or {}
            publish_rate = publish_details.get("rate", 0.0)
            deliver_rate = deliver_details.get("rate", 0.0)
            ack_rate = ack_details.get("rate", 0.0)

            cleaned_channels.append({
                "name": item.get("name"),
                "number": item.get("number"),
                "node": item.get("node"),
                "user": item.get("user"),
                "vhost": item.get("vhost"),
                "connection_name": conn_details.get("name") or item.get("connection"),
                "peer_host": conn_details.get("peer_host"),
                "peer_port": conn_details.get("peer_port"),
                "state": item.get("state"),
                "messages_unacknowledged": item.get("messages_unacknowledged", 0),
                "messages_uncommitted": item.get("messages_uncommitted", 0),
                "acks_uncommitted": item.get("acks_uncommitted", 0),
                "prefetch_count": item.get("prefetch_count", 0),
                "global_prefetch_count": item.get("global_prefetch_count", 0),
                "consumer_count": item.get("consumer_count", 0),
                "publish_rate": publish_rate,
                "deliver_rate": deliver_rate,
                "ack_rate": ack_rate,
            })

        return {
            "status": "ok",
            "connection": connection,
            "total": len(cleaned_channels),
            "channels": cleaned_channels,
        }
    except httpx.HTTPStatusError as err:
        logger.warning("请求信道诊断指标返回异常 HTTP 状态 [%s]: %s", connection, err)
        return {
            "status": "error",
            "connection": connection,
            "error": "HTTPStatusError",
            "message": f"Management API 请求失败，状态码: {err.response.status_code}",
            "channels": [],
            "total": 0,
        }
    except (httpx.RequestError, OSError, TimeoutError) as err:
        safe_msg = mask_url(str(err)) or str(err)
        logger.warning("请求信道诊断指标发生网络错误 [%s]: %s", connection, safe_msg)
        return {
            "status": "error",
            "connection": connection,
            "error": type(err).__name__,
            "message": f"无法连通 RabbitMQ Management API: {safe_msg}",
            "channels": [],
            "total": 0,
        }
