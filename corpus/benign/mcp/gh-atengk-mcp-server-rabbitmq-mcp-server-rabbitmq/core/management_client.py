"""RabbitMQ HTTP Management API 异步客户端与拓扑指标采集.

@author Ateng
@since 2026-10-04
"""

import logging
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)


class ManagementClient:
    """RabbitMQ Management HTTP 接口异步客户端封装."""

    def __init__(self, base_url: str | None, timeout: float = 10.0) -> None:
        """初始化 ManagementClient.

        @param base_url HTTP Management API 根地址，允许为 None
        @param timeout HTTP 请求超时时间（秒）
        """
        self.raw_base_url = base_url
        self.timeout = timeout
        self.base_url: str | None
        if base_url:
            cleaned = base_url.rstrip("/")
            self.base_url = cleaned if cleaned.endswith("/api") else f"{cleaned}/api"
        else:
            self.base_url = None

    @property
    def is_available(self) -> bool:
        """检查当前客户端是否已配置 Management API 地址."""
        return self.base_url is not None

    def _get_url(self, path: str) -> str:
        """拼装目标 API 完整路径.

        @param path API 相对子路径
        @return 完整 URL 路径
        @throws ValueError 当未配置 Management API 基地址时抛出
        """
        if not self.base_url:
            raise ValueError("未配置 RabbitMQ Management API 访问地址")
        clean_path = path.lstrip("/")
        return f"{self.base_url}/{clean_path}"

    async def _get_json(self, path: str) -> Any:
        """执行异步 GET 请求并解析 JSON 响应.

        @param path API 相对子路径
        @return 反序列化后的 JSON 数据
        @throws httpx.HTTPStatusError 当服务端返回非 2xx 状态码时抛出
        @throws httpx.RequestError 当发生底层网络通信异常时抛出
        """
        url = self._get_url(path)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data: Any = resp.json()
            return data

    async def get_overview(self) -> dict[str, Any]:
        """获取集群概览指标.

        @return 集群核心运行状态与统计指标字典
        """
        data: dict[str, Any] = await self._get_json("overview")
        return data

    async def list_exchanges(self, vhost: str | None = None) -> list[dict[str, Any]]:
        """查询交换机列表，支持指定 vhost 过滤.

        @param vhost 可选的虚拟主机名称
        @return 交换机信息字典列表
        """
        path = f"exchanges/{quote(vhost, safe='')}" if vhost else "exchanges"
        items: list[dict[str, Any]] = await self._get_json(path)
        return items

    async def list_queues(self, vhost: str | None = None) -> list[dict[str, Any]]:
        """查询队列列表及核心指标，支持指定 vhost 过滤.

        @param vhost 可选的虚拟主机名称
        @return 队列信息字典列表
        """
        path = f"queues/{quote(vhost, safe='')}" if vhost else "queues"
        items: list[dict[str, Any]] = await self._get_json(path)
        return items

    async def get_queue(self, queue: str, vhost: str = "/") -> dict[str, Any]:
        """获取指定队列的深度元数据.

        @param queue 目标队列名称
        @param vhost 虚拟主机名称，默认为 '/'
        @return 队列深度指标与策略参数字典
        """
        encoded_vhost = quote(vhost, safe="")
        encoded_queue = quote(queue, safe="")
        data: dict[str, Any] = await self._get_json(f"queues/{encoded_vhost}/{encoded_queue}")
        return data

    async def list_bindings(
        self,
        vhost: str | None = None,
        queue: str | None = None,
        exchange: str | None = None,
    ) -> list[dict[str, Any]]:
        """查询路由绑定关系，支持按 vhost、queue 或 exchange 过滤.

        @param vhost 可选的虚拟主机名称
        @param queue 可选的指定队列名称过滤
        @param exchange 可选的指定交换机名称过滤
        @return 路由绑定规则字典列表
        """
        target_vhost = vhost or ("/" if (queue or exchange) else None)
        if target_vhost and queue:
            path = f"queues/{quote(target_vhost, safe='')}/{quote(queue, safe='')}/bindings"
        elif target_vhost and exchange:
            path = f"exchanges/{quote(target_vhost, safe='')}/{quote(exchange, safe='')}/bindings/source"
        elif target_vhost:
            path = f"bindings/{quote(target_vhost, safe='')}"
        else:
            path = "bindings"

        items: list[dict[str, Any]] = await self._get_json(path)
        return items

    async def list_connections(self, vhost: str | None = None) -> list[dict[str, Any]]:
        """查询外部客户端连接列表，支持指定 vhost 过滤.

        @param vhost 可选的虚拟主机名称
        @return 客户端连接信息字典列表
        """
        path = f"vhosts/{quote(vhost, safe='')}/connections" if vhost else "connections"
        items: list[dict[str, Any]] = await self._get_json(path)
        if vhost:
            return [c for c in items if c.get("vhost") == vhost]
        return items

    async def list_channels(
        self,
        vhost: str | None = None,
        connection: str | None = None,
    ) -> list[dict[str, Any]]:
        """查询活跃信道列表，支持按 vhost 或特定客户端连接名称过滤.

        @param vhost 可选的虚拟主机名称
        @param connection 可选的客户端连接标识名称
        @return 信道信息字典列表
        """
        if connection:
            path = f"connections/{quote(connection, safe='')}/channels"
            items: list[dict[str, Any]] = await self._get_json(path)
            filtered = [
                ch
                for ch in items
                if (ch.get("connection_details", {}).get("name") or ch.get("connection")) == connection
            ]
            if vhost:
                filtered = [ch for ch in filtered if ch.get("vhost") == vhost]
            return filtered
        elif vhost:
            path = f"vhosts/{quote(vhost, safe='')}/channels"
            items = await self._get_json(path)
            return [ch for ch in items if ch.get("vhost") == vhost]
        else:
            path = "channels"
            items = await self._get_json(path)
            return items

