"""RabbitMQ 实例基础探活、集群概览与连接配置工具实现.

@author Ateng
@since 2026-10-04
"""

import logging
import time
from typing import Any

import aio_pika
import httpx

from mcp_server_rabbitmq.core.config import get_global_config, mask_url

logger = logging.getLogger(__name__)


def rabbitmq_list_connections() -> list[dict[str, Any]]:
    """列出当前 MCP 服务配置的所有 RabbitMQ 实例连接清单与脱敏地址.

    [注意区分] 本工具返回的是配置中心中管理的目标 Broker 实例（如 connections.yaml 中配置的连接别名），
    若要排查微服务应用连入 RabbitMQ 的物理客户端 TCP 链路，请调用 rabbitmq_list_client_connections。

    @return 脱敏后的 Broker 实例配置信息列表
    """
    config = get_global_config()
    return config.list_connections()


def rabbitmq_list_configured_brokers() -> list[dict[str, Any]]:
    """列出当前 MCP 服务配置的所有 RabbitMQ 目标 Broker 实例清单与脱敏地址.

    为 rabbitmq_list_connections 的语义强化别名，用于清晰区分 Broker 实例配置与外部客户端 TCP 链路。

    @return 脱敏后的 Broker 实例配置信息列表
    """
    return rabbitmq_list_connections()


async def rabbitmq_ping(connection: str = "default") -> dict[str, Any]:
    """测量与 RabbitMQ Broker 的 AMQP 链路往返延迟.

    建立底层 TCP/AMQP 会话与信道后立即安全关闭，用于网络可达性与响应时间探活。

    @param connection 目标连接别名，默认为 'default'
    @return 包含探活状态与延迟（毫秒）的结构化报告
    """
    config = get_global_config()
    conn_cfg = config.get_connection(connection)
    masked_url = conn_cfg.masked_amqp_url

    start_time = time.perf_counter()
    try:
        # 建立 AMQP 连接与信道以测量完整链路延迟
        conn = await aio_pika.connect_robust(conn_cfg.amqp_url)
        try:
            channel = await conn.channel()
            await channel.close()
        finally:
            await conn.close()

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": "ok",
            "connection": connection,
            "masked_url": masked_url,
            "latency_ms": latency_ms,
            "message": f"成功连接至 RabbitMQ Broker，往返延迟 {latency_ms} ms",
        }
    except (aio_pika.exceptions.AMQPError, OSError, TimeoutError) as err:
        safe_err_msg = mask_url(str(err)) or str(err)
        logger.warning("RabbitMQ ping 探测失败 [%s]: %s", connection, safe_err_msg)
        return {
            "status": "error",
            "connection": connection,
            "masked_url": masked_url,
            "error": type(err).__name__,
            "message": f"连接 RabbitMQ Broker 失败: {safe_err_msg}",
        }


async def rabbitmq_overview(connection: str = "default") -> dict[str, Any]:
    """获取 RabbitMQ 集群节点状态、队列统计与全局消息吞吐大盘.

    依据 ADR-0001 双核架构设计，当未配置 Management API 时自动优雅降级。

    @param connection 目标连接别名，默认为 'default'
    @return 集群指标概览字典或降级提示
    """
    config = get_global_config()
    conn_cfg = config.get_connection(connection)

    # 检查 Management API 配置并执行优雅降级 (ADR-0001)
    if not conn_cfg.management_url:
        return {
            "status": "degraded",
            "connection": connection,
            "message": (
                "未配置 RabbitMQ Management API 访问地址 (MCP_RABBITMQ_MANAGEMENT_URL)，"
                "无法获取集群全景指标概览，已优雅降级为仅 AMQP 基础模式。"
            ),
            "management_url": None,
        }

    base = conn_cfg.management_url.rstrip("/")
    target_url = f"{base}/overview" if base.endswith("/api") else f"{base}/api/overview"
    masked_mgmt_url = conn_cfg.masked_management_url

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(target_url)
            resp.raise_for_status()
            data = resp.json()

        return {
            "status": "ok",
            "connection": connection,
            "cluster_name": data.get("cluster_name"),
            "rabbitmq_version": data.get("rabbitmq_version"),
            "erlang_version": data.get("erlang_version"),
            "node": data.get("node"),
            "queue_totals": data.get("queue_totals", {}),
            "object_totals": data.get("object_totals", {}),
            "message_stats": data.get("message_stats", {}),
        }
    except httpx.HTTPStatusError as err:
        logger.warning("请求 RabbitMQ Management API 响应异常: %s", err)
        return {
            "status": "error",
            "connection": connection,
            "masked_url": masked_mgmt_url,
            "error": "HTTPStatusError",
            "message": f"Management API 请求失败，状态码: {err.response.status_code}",
        }
    except (httpx.RequestError, OSError, TimeoutError) as err:
        safe_err_msg = mask_url(str(err)) or str(err)
        logger.warning("请求 RabbitMQ Management API 发生网络错误: %s", safe_err_msg)
        return {
            "status": "error",
            "connection": connection,
            "masked_url": masked_mgmt_url,
            "error": type(err).__name__,
            "message": f"无法连通 RabbitMQ Management API: {safe_err_msg}",
        }
