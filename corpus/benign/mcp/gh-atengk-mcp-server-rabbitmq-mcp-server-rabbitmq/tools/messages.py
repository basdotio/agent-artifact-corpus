"""RabbitMQ 消息可靠发布、无损采样 (Peek) 与受控消费工具实现.

@author Ateng
@since 2026-10-04
"""

import base64
import json
import logging
from typing import Any

import aio_pika.exceptions
import aiormq.exceptions
from aio_pika import DeliveryMode, Message

from mcp_server_rabbitmq.core.amqp_client import get_amqp_channel
from mcp_server_rabbitmq.core.config import get_global_config
from mcp_server_rabbitmq.core.security import check_write_permission, require_write

logger = logging.getLogger(__name__)


def _encode_payload(payload: Any) -> tuple[bytes, str]:
    """将各类 Python 对象序列化为字节载荷并推导 MIME 类型.

    @param payload 待发布的消息载荷（字典、列表、字符串或二进制）
    @return (字节数据, 推导的内容类型)
    """
    if isinstance(payload, (dict, list)):
        return json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json"
    if isinstance(payload, (bytes, bytearray)):
        return bytes(payload), "application/octet-stream"
    if isinstance(payload, str):
        return payload.encode("utf-8"), "text/plain"
    return str(payload).encode("utf-8"), "text/plain"


def _decode_body(body: bytes, content_type: str | None = None) -> tuple[Any, str]:
    """安全解析消息体字节流，文本尝试 JSON 反序列化，二进制回退为 Base64.

    @param body 原始消息体字节数组
    @param content_type 消息元数据声明的 MIME 类型
    @return (解析后的载荷对象, 编码方式 'utf-8' 或 'base64')
    """
    try:
        text = body.decode("utf-8")
        if content_type == "application/json" or (
            text and text[0] in ("{", "[") and text[-1] in ("}", "]")
        ):
            try:
                return json.loads(text), "utf-8"
            except (json.JSONDecodeError, ValueError):
                return text, "utf-8"
        return text, "utf-8"
    except UnicodeDecodeError:
        b64_str = base64.b64encode(body).decode("ascii")
        return b64_str, "base64"


def _format_message_record(msg: Any) -> dict[str, Any]:
    """提取并在格式化消息元数据与载荷字典.

    @param msg aio-pika IncomingMessage 对象
    @return 结构化消息报告字典
    """
    body_data, encoding = _decode_body(msg.body, getattr(msg, "content_type", None))
    deliv_mode = getattr(msg, "delivery_mode", None)
    if deliv_mode is not None and hasattr(deliv_mode, "value"):
        deliv_val = int(deliv_mode.value)
    elif deliv_mode is not None:
        deliv_val = int(deliv_mode)
    else:
        deliv_val = 1

    return {
        "message_id": getattr(msg, "message_id", None),
        "delivery_mode": deliv_val,
        "priority": getattr(msg, "priority", 0) or 0,
        "content_type": getattr(msg, "content_type", None),
        "headers": getattr(msg, "headers", {}) or {},
        "routing_key": getattr(msg, "routing_key", ""),
        "exchange": getattr(msg, "exchange", ""),
        "redelivered": getattr(msg, "redelivered", False),
        "encoding": encoding,
        "payload": body_data,
        "payload_size": len(msg.body),
    }


@require_write("publish_message")
async def rabbitmq_publish_message(
    exchange: str,
    routing_key: str = "",
    payload: Any = "",
    delivery_mode: int = 2,
    priority: int | None = None,
    expiration: float | str | None = None,
    headers: dict[str, Any] | None = None,
    connection: str = "default",
) -> dict[str, Any]:
    """向指定交换机与路由键发布消息，支持 JSON 自动序列化与持久化配置.

    受全局写保护门禁 (--allow-write) 约束。

    @param exchange 目标交换机名称
    @param routing_key 路由寻址键，默认为空
    @param payload 消息载荷，支持 dict, list, str 或 bytes
    @param delivery_mode 投递模式，1=非持久化，2=持久化（默认 2）
    @param priority 消息优先级（0-255）
    @param expiration 消息过期时间（毫秒数字或字符串）
    @param headers 自定义消息属性头字典
    @param connection 目标连接别名，默认为 'default'
    @return 消息投递确认报告
    """
    config = get_global_config()
    conn_cfg = config.get_connection(connection)

    body_bytes, content_type = _encode_payload(payload)

    # 处理 TTL 过期参数（毫秒数字或字符串统一换算为秒）
    exp_val: float | None = None
    if expiration is not None:
        try:
            exp_val = float(expiration) / 1000.0
        except (ValueError, TypeError):
            exp_val = None

    deliv_enum = DeliveryMode.PERSISTENT if delivery_mode == 2 else DeliveryMode.NOT_PERSISTENT
    msg = Message(
        body=body_bytes,
        content_type=content_type,
        delivery_mode=deliv_enum,
        priority=priority,
        expiration=exp_val,
        headers=headers,
    )

    async with get_amqp_channel(conn_cfg.amqp_url) as ch:
        ex = await ch.get_exchange(exchange) if exchange else ch.default_exchange
        await ex.publish(msg, routing_key=routing_key)

    return {
        "status": "ok",
        "connection": connection,
        "exchange": exchange,
        "routing_key": routing_key,
        "content_type": content_type,
        "delivery_mode": delivery_mode,
        "payload_size": len(body_bytes),
        "message": "消息发布成功",
    }


async def rabbitmq_peek_messages(
    queue: str,
    count: int = 10,
    connection: str = "default",
) -> dict[str, Any]:
    """对队列头部消息实施无损诊断采样 (Peek).

    读取消息后延迟在循环结束后统一触发 reject(requeue=True)，确保数据零丢失且不出队，同时防止重复读取同一条消息 (ADR-0002)。

    @param queue 目标队列名称
    @param count 采样数量限制（1-50，默认 10）
    @param connection 目标连接别名，默认为 'default'
    @return 采样消息清单报告
    """
    safe_count = max(1, min(count, 50))
    config = get_global_config()
    conn_cfg = config.get_connection(connection)

    results: list[dict[str, Any]] = []
    fetched_messages: list[Any] = []

    async with get_amqp_channel(conn_cfg.amqp_url) as ch:
        q = await ch.get_queue(queue)
        try:
            for _ in range(safe_count):
                msg = await q.get(no_ack=False, fail=False)
                if msg is None:
                    break
                fetched_messages.append(msg)
                record = _format_message_record(msg)
                results.append(record)
        finally:
            # 核心安全契约：在信道关闭前，统一将所有抓取的消息归还队首，避免迭代期间重复读取同一条消息
            for msg in fetched_messages:
                try:
                    await msg.reject(requeue=True)
                except (aio_pika.exceptions.AMQPError, aiormq.exceptions.AMQPError, OSError, TimeoutError) as err:
                    logger.debug("批量归还采样消息时忽略异常: %s", err)

    return {
        "status": "ok",
        "connection": connection,
        "queue": queue,
        "count": len(results),
        "peeked": True,
        "messages": results,
    }


async def rabbitmq_get_messages(
    queue: str,
    count: int = 10,
    ack: bool = False,
    connection: str = "default",
) -> dict[str, Any]:
    """受控拉取队列消息，默认 ack=False 仅采样不删除，传 ack=True 物理确认出队.

    当传入 ack=True 时受全局写保护门禁 (--allow-write) 约束，防范在途数据误删。

    @param queue 目标队列名称
    @param count 拉取条数上限（1-50，默认 10）
    @param ack 是否物理确认并从队列移除，默认为 False（仅拉取）
    @param connection 目标连接别名，默认为 'default'
    @return 拉取消息清单报告
    """
    if ack:
        check_write_permission("ack_messages")

    safe_count = max(1, min(count, 50))
    config = get_global_config()
    conn_cfg = config.get_connection(connection)

    results: list[dict[str, Any]] = []
    unacked_messages: list[Any] = []

    async with get_amqp_channel(conn_cfg.amqp_url) as ch:
        q = await ch.get_queue(queue)
        try:
            for _ in range(safe_count):
                msg = await q.get(no_ack=False, fail=False)
                if msg is None:
                    break

                if not ack:
                    unacked_messages.append(msg)

                record = _format_message_record(msg)
                results.append(record)

                if ack:
                    await msg.ack()
        finally:
            if not ack:
                for msg in unacked_messages:
                    try:
                        await msg.reject(requeue=True)
                    except (aio_pika.exceptions.AMQPError, aiormq.exceptions.AMQPError, OSError, TimeoutError) as err:
                        logger.debug("受控消费归还未确认消息时忽略异常: %s", err)

    return {
        "status": "ok",
        "connection": connection,
        "queue": queue,
        "count": len(results),
        "acknowledged": ack,
        "messages": results,
    }
