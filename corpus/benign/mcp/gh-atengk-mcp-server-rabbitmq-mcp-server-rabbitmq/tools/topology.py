"""RabbitMQ 交换机、队列与绑定关系拓扑管理工具实现.

@author Ateng
@since 2026-10-04
"""

import logging
from typing import Any

import httpx

from mcp_server_rabbitmq.core.amqp_client import get_amqp_channel
from mcp_server_rabbitmq.core.config import get_global_config, mask_url
from mcp_server_rabbitmq.core.management_client import ManagementClient
from mcp_server_rabbitmq.core.security import check_confirmation, require_write

logger = logging.getLogger(__name__)

_DEGRADED_MESSAGE = (
    "未配置 RabbitMQ Management API 访问地址 (MCP_RABBITMQ_MANAGEMENT_URL)，"
    "无法获取全局拓扑指标，已优雅降级为纯 AMQP 模式。"
)


async def rabbitmq_list_exchanges(
    connection: str = "default",
    vhost: str | None = None,
) -> dict[str, Any]:
    """查询指定实例的交换机列表及类型、持久化配置.

    @param connection 目标连接别名，默认为 'default'
    @param vhost 可选的虚拟主机过滤
    @return 交换机元数据列表报告或降级提示
    """
    config = get_global_config()
    conn_cfg = config.get_connection(connection)
    client = ManagementClient(conn_cfg.management_url)

    if not client.is_available:
        return {
            "status": "degraded",
            "connection": connection,
            "message": _DEGRADED_MESSAGE,
            "exchanges": [],
        }

    try:
        exchanges = await client.list_exchanges(vhost=vhost)
        return {
            "status": "ok",
            "connection": connection,
            "vhost": vhost,
            "exchanges": exchanges,
        }
    except (httpx.HTTPError, OSError, TimeoutError) as err:
        safe_err = mask_url(str(err)) or str(err)
        logger.warning("查询交换机列表失败 [%s]: %s", connection, safe_err)
        return {
            "status": "error",
            "connection": connection,
            "message": f"查询交换机列表失败: {safe_err}",
        }


@require_write("declare_exchange")
async def rabbitmq_declare_exchange(
    name: str,
    type: str = "direct",
    durable: bool = True,
    auto_delete: bool = False,
    internal: bool = False,
    arguments: dict[str, Any] | None = None,
    connection: str = "default",
) -> dict[str, Any]:
    """在 Broker 中受控声明交换机.

    受全局写保护门禁 (--allow-write) 约束。

    @param name 交换机名称
    @param type 交换机类型（direct, fanout, topic, headers），默认为 'direct'
    @param durable 是否持久化，默认为 True
    @param auto_delete 是否自动删除，默认为 False
    @param internal 是否为内部交换机，默认为 False
    @param arguments 可选扩展参数
    @param connection 目标连接别名，默认为 'default'
    @return 声明成功的交换机元数据
    """
    valid_types = {"direct", "fanout", "topic", "headers"}
    if type not in valid_types:
        raise ValueError(f"不支持的交换机类型: '{type}'，仅支持: {sorted(valid_types)}")

    config = get_global_config()
    conn_cfg = config.get_connection(connection)

    async with get_amqp_channel(conn_cfg.amqp_url) as ch:
        await ch.declare_exchange(
            name,
            type=type,
            durable=durable,
            auto_delete=auto_delete,
            internal=internal,
            arguments=arguments,
        )

    return {
        "status": "ok",
        "connection": connection,
        "name": name,
        "type": type,
        "durable": durable,
        "auto_delete": auto_delete,
        "internal": internal,
        "arguments": arguments or {},
    }


@require_write("delete_exchange")
async def rabbitmq_delete_exchange(
    name: str,
    confirm: bool = False,
    if_unused: bool = False,
    connection: str = "default",
) -> dict[str, Any]:
    """受控删除指定的交换机.

    强制要求二次确认 (confirm: bool = False)，未确认时仅返回受影响预估报告 (ADR-0002)。

    @param name 待删除的交换机名称
    @param confirm 二次确认标识，默认为 False
    @param if_unused 是否仅在无绑定且未被使用时才删除，默认为 False
    @param connection 目标连接别名，默认为 'default'
    @return 删除结果或二次确认预估报告
    """
    gate = check_confirmation(
        action="delete_exchange",
        confirm=confirm,
        target=name,
        impact_estimate=f"将永久删除交换机 '{name}' 及其所有关联路由绑定",
    )
    if gate is not None:
        return gate

    config = get_global_config()
    conn_cfg = config.get_connection(connection)

    async with get_amqp_channel(conn_cfg.amqp_url) as ch:
        await ch.exchange_delete(name, if_unused=if_unused)

    return {
        "status": "ok",
        "connection": connection,
        "name": name,
        "message": f"成功删除交换机 '{name}'",
    }


async def rabbitmq_list_queues(
    connection: str = "default",
    vhost: str | None = None,
) -> dict[str, Any]:
    """查询指定实例的全部队列及其积压消息、未确认数与消费者全景指标.

    @param connection 目标连接别名，默认为 'default'
    @param vhost 可选的虚拟主机过滤
    @return 队列列表报告或降级提示
    """
    config = get_global_config()
    conn_cfg = config.get_connection(connection)
    client = ManagementClient(conn_cfg.management_url)

    if not client.is_available:
        return {
            "status": "degraded",
            "connection": connection,
            "message": _DEGRADED_MESSAGE,
            "queues": [],
        }

    try:
        queues = await client.list_queues(vhost=vhost)
        return {
            "status": "ok",
            "connection": connection,
            "vhost": vhost,
            "queues": queues,
        }
    except (httpx.HTTPError, OSError, TimeoutError) as err:
        safe_err = mask_url(str(err)) or str(err)
        logger.warning("查询队列列表失败 [%s]: %s", connection, safe_err)
        return {
            "status": "error",
            "connection": connection,
            "message": f"查询队列列表失败: {safe_err}",
        }


async def rabbitmq_get_queue(
    queue: str,
    connection: str = "default",
    vhost: str = "/",
) -> dict[str, Any]:
    """获取指定队列的深度元数据（包括死信交换机 dlx、TTL 策略与消费者明细）.

    @param queue 目标队列名称
    @param connection 目标连接别名，默认为 'default'
    @param vhost 虚拟主机，默认为 '/'
    @return 单个队列的深度指标报告
    """
    config = get_global_config()
    conn_cfg = config.get_connection(connection)
    client = ManagementClient(conn_cfg.management_url)

    if not client.is_available:
        return {
            "status": "degraded",
            "connection": connection,
            "message": _DEGRADED_MESSAGE,
            "queue": None,
        }

    try:
        data = await client.get_queue(queue=queue, vhost=vhost)
        return {
            "status": "ok",
            "connection": connection,
            "vhost": vhost,
            "queue": data,
        }
    except (httpx.HTTPError, OSError, TimeoutError) as err:
        safe_err = mask_url(str(err)) or str(err)
        logger.warning("获取队列详情失败 [%s]: %s", connection, safe_err)
        return {
            "status": "error",
            "connection": connection,
            "message": f"获取队列详情失败: {safe_err}",
        }


@require_write("declare_queue")
async def rabbitmq_declare_queue(
    name: str,
    durable: bool = True,
    exclusive: bool = False,
    auto_delete: bool = False,
    arguments: dict[str, Any] | None = None,
    connection: str = "default",
) -> dict[str, Any]:
    """在 Broker 中声明队列，支持死信路由 (x-dead-letter-exchange) 与 TTL 等高级参数.

    受全局写保护门禁 (--allow-write) 约束。

    @param name 队列名称
    @param durable 是否持久化，默认为 True
    @param exclusive 是否为排他队列，默认为 False
    @param auto_delete 是否自动删除，默认为 False
    @param arguments 可选扩展参数（如 x-dead-letter-exchange, x-message-ttl）
    @param connection 目标连接别名，默认为 'default'
    @return 声明成功的队列元数据
    """
    config = get_global_config()
    conn_cfg = config.get_connection(connection)

    async with get_amqp_channel(conn_cfg.amqp_url) as ch:
        await ch.declare_queue(
            name,
            durable=durable,
            exclusive=exclusive,
            auto_delete=auto_delete,
            arguments=arguments,
        )

    return {
        "status": "ok",
        "connection": connection,
        "name": name,
        "durable": durable,
        "exclusive": exclusive,
        "auto_delete": auto_delete,
        "arguments": arguments or {},
    }


@require_write("purge_queue")
async def rabbitmq_purge_queue(
    name: str,
    confirm: bool = False,
    connection: str = "default",
) -> dict[str, Any]:
    """受控清空指定队列中的全部待消费消息.

    强制要求二次确认 (confirm: bool = False)，未确认时仅返回受影响预估报告 (ADR-0002)。

    @param name 目标队列名称
    @param confirm 二次确认标识，默认为 False
    @param connection 目标连接别名，默认为 'default'
    @return 清空结果或二次确认预估报告
    """
    gate = check_confirmation(
        action="purge_queue",
        confirm=confirm,
        target=name,
        impact_estimate=f"将清空队列 '{name}' 中的全部积压消息，操作不可撤回",
    )
    if gate is not None:
        return gate

    config = get_global_config()
    conn_cfg = config.get_connection(connection)

    async with get_amqp_channel(conn_cfg.amqp_url) as ch:
        q = await ch.get_queue(name)
        purged = await q.purge()
        count = getattr(purged, "message_count", purged)
        purged_count = int(count) if isinstance(count, (int, float)) else 0

    return {
        "status": "ok",
        "connection": connection,
        "name": name,
        "purged_count": purged_count,
        "message": f"成功清空队列 '{name}'，共清除 {purged_count} 条消息",
    }


@require_write("delete_queue")
async def rabbitmq_delete_queue(
    name: str,
    confirm: bool = False,
    if_unused: bool = False,
    if_empty: bool = False,
    connection: str = "default",
) -> dict[str, Any]:
    """受控删除指定队列.

    强制要求二次确认 (confirm: bool = False)，未确认时仅返回受影响预估报告 (ADR-0002)。

    @param name 待删除的队列名称
    @param confirm 二次确认标识，默认为 False
    @param if_unused 是否仅在无消费者时删除，默认为 False
    @param if_empty 是否仅在队列为空时删除，默认为 False
    @param connection 目标连接别名，默认为 'default'
    @return 删除结果或二次确认预估报告
    """
    gate = check_confirmation(
        action="delete_queue",
        confirm=confirm,
        target=name,
        impact_estimate=f"将物理销毁队列 '{name}'，未消费消息将全部丢失",
    )
    if gate is not None:
        return gate

    config = get_global_config()
    conn_cfg = config.get_connection(connection)

    async with get_amqp_channel(conn_cfg.amqp_url) as ch:
        deleted = await ch.queue_delete(name, if_unused=if_unused, if_empty=if_empty)
        count = getattr(deleted, "message_count", deleted)
        msg_count = int(count) if isinstance(count, (int, float)) else 0

    return {
        "status": "ok",
        "connection": connection,
        "name": name,
        "message_count": msg_count,
        "message": f"成功删除队列 '{name}'",
    }


async def rabbitmq_list_bindings(
    connection: str = "default",
    vhost: str | None = None,
    queue: str | None = None,
    exchange: str | None = None,
) -> dict[str, Any]:
    """查询交换机与队列之间的绑定映射规则.

    @param connection 目标连接别名，默认为 'default'
    @param vhost 可选的虚拟主机过滤
    @param queue 可选的指定队列过滤
    @param exchange 可选的指定交换机过滤
    @return 绑定关系列表报告或降级提示
    """
    config = get_global_config()
    conn_cfg = config.get_connection(connection)
    client = ManagementClient(conn_cfg.management_url)

    if not client.is_available:
        return {
            "status": "degraded",
            "connection": connection,
            "message": _DEGRADED_MESSAGE,
            "bindings": [],
        }

    try:
        bindings = await client.list_bindings(vhost=vhost, queue=queue, exchange=exchange)
        return {
            "status": "ok",
            "connection": connection,
            "vhost": vhost,
            "bindings": bindings,
        }
    except (httpx.HTTPError, OSError, TimeoutError) as err:
        safe_err = mask_url(str(err)) or str(err)
        logger.warning("查询绑定关系失败 [%s]: %s", connection, safe_err)
        return {
            "status": "error",
            "connection": connection,
            "message": f"查询绑定关系失败: {safe_err}",
        }


@require_write("bind_queue")
async def rabbitmq_bind_queue(
    queue: str,
    exchange: str,
    routing_key: str = "",
    arguments: dict[str, Any] | None = None,
    connection: str = "default",
) -> dict[str, Any]:
    """将队列绑定至指定交换机并配置路由键 (Routing Key).

    受全局写保护门禁 (--allow-write) 约束。

    @param queue 目标队列名称
    @param exchange 目标交换机名称
    @param routing_key 路由键，默认为空字符串
    @param arguments 可选绑定参数
    @param connection 目标连接别名，默认为 'default'
    @return 绑定结果报告
    """
    config = get_global_config()
    conn_cfg = config.get_connection(connection)

    async with get_amqp_channel(conn_cfg.amqp_url) as ch:
        q = await ch.get_queue(queue)
        await q.bind(exchange, routing_key=routing_key, arguments=arguments)

    return {
        "status": "ok",
        "connection": connection,
        "queue": queue,
        "exchange": exchange,
        "routing_key": routing_key,
        "arguments": arguments or {},
    }


@require_write("unbind_queue")
async def rabbitmq_unbind_queue(
    queue: str,
    exchange: str,
    routing_key: str = "",
    arguments: dict[str, Any] | None = None,
    connection: str = "default",
) -> dict[str, Any]:
    """解除队列与指定交换机之间的路由绑定.

    受全局写保护门禁 (--allow-write) 约束。

    @param queue 目标队列名称
    @param exchange 目标交换机名称
    @param routing_key 路由键，默认为空字符串
    @param arguments 可选绑定参数
    @param connection 目标连接别名，默认为 'default'
    @return 解绑结果报告
    """
    config = get_global_config()
    conn_cfg = config.get_connection(connection)

    async with get_amqp_channel(conn_cfg.amqp_url) as ch:
        q = await ch.get_queue(queue)
        await q.unbind(exchange, routing_key=routing_key, arguments=arguments)

    return {
        "status": "ok",
        "connection": connection,
        "queue": queue,
        "exchange": exchange,
        "routing_key": routing_key,
        "arguments": arguments or {},
    }
