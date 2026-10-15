"""RabbitMQ 异步 AMQP 客户端与信道连接池生命周期管理.

@author Ateng
@since 2026-10-04
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractConnection

from mcp_server_rabbitmq.core.config import mask_url

logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_amqp_connection(amqp_url: str) -> AsyncIterator[AbstractConnection]:
    """获取一个健壮的 AMQP 异步物理连接并在退出时确保关闭.

    @param amqp_url AMQP 连接串
    @return 异步连接迭代器
    """
    connection = await aio_pika.connect_robust(amqp_url)
    try:
        yield connection
    finally:
        try:
            await connection.close()
        except (aio_pika.exceptions.AMQPError, OSError, TimeoutError) as err:
            safe_err = mask_url(str(err)) or str(err)
            logger.debug("关闭 AMQP 连接时忽略非致命异常: %s", safe_err)


@asynccontextmanager
async def get_amqp_channel(amqp_url: str) -> AsyncIterator[AbstractChannel]:
    """获取一个独立的 AMQP 信道上下文管理器并在退出时确保资源回收.

    @param amqp_url AMQP 连接串
    @return 异步信道迭代器
    """
    async with get_amqp_connection(amqp_url) as conn:
        channel = await conn.channel()
        try:
            yield channel
        finally:
            try:
                await channel.close()
            except (aio_pika.exceptions.AMQPError, OSError, TimeoutError) as err:
                safe_err = mask_url(str(err)) or str(err)
                logger.debug("关闭 AMQP 信道时忽略非致命异常: %s", safe_err)
