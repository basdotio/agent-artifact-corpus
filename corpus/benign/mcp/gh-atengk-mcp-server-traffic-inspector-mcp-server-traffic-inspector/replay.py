"""基于 httpx 的历史 HttpFlow 参数变异重放 (FlowReplay) 与响应 Diff 对比模块。

@author Ateng
@since 2026-10-13
"""

from __future__ import annotations

import difflib
import json
import time
from collections.abc import Mapping
from typing import Any

import httpx

from mcp_server_traffic_inspector.storage import (
    DEFAULT_PREVIEW_CHARS,
    StorageBus,
    _decode_preview,
    _is_binary_payload,
)


def _merge_request_headers(
    original_headers: Mapping[str, str],
    overrides: Mapping[str, str] | None,
) -> dict[str, str]:
    merged: dict[str, str] = {}
    lower_to_key: dict[str, str] = {}

    for key, val in original_headers.items():
        key_lower = key.lower()
        if key_lower in {"host", "content-length"}:
            continue
        merged[key] = str(val)
        lower_to_key[key_lower] = key

    if overrides:
        for key, val in overrides.items():
            key_lower = key.lower()
            if key_lower in lower_to_key:
                del merged[lower_to_key[key_lower]]
            merged[key] = str(val)
            lower_to_key[key_lower] = key

    return merged


def _build_body_diff_preview(
    old_bytes: bytes,
    new_bytes: bytes,
    is_old_binary: bool,
    is_new_binary: bool,
) -> str:
    if old_bytes == new_bytes:
        return ""
    if is_old_binary or is_new_binary:
        return f"<binary payload changed: {len(old_bytes)} bytes -> {len(new_bytes)} bytes>"

    old_lines = old_bytes.decode("utf-8", errors="replace").splitlines(keepends=True)
    new_lines = new_bytes.decode("utf-8", errors="replace").splitlines(keepends=True)
    diff_iter = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile="original_response",
        tofile="replayed_response",
        n=2,
    )
    diff_text = "".join(diff_iter).strip()
    if len(diff_text) > DEFAULT_PREVIEW_CHARS:
        return diff_text[:DEFAULT_PREVIEW_CHARS] + "\n... [truncated]"
    return diff_text


class FlowReplayEngine:
    """历史 HttpFlow 参数变异重放与响应差异对比引擎。

    从 StorageBus 读取完整无损的原始请求载荷，支持按需覆盖 URL、Headers 与 Body 后
    通过独立 httpx 客户端重发请求，并生成新旧响应的结构化 Diff 摘要。
    """

    def __init__(
        self,
        storage: StorageBus,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        """初始化重放引擎。

        Args:
            storage: 共享 SQLite WAL 数据总线实例。
            transport: 可选的自定义 httpx 异步传输层（供测试替身注入），默认使用真实网络传输。
            timeout_seconds: 单次重放请求超时时间（秒），默认 30.0。
        """
        self.storage = storage
        self._transport = transport
        self._timeout = timeout_seconds

    async def replay(
        self,
        flow_id: str,
        *,
        modify_headers: Mapping[str, str] | None = None,
        modify_body: str | Mapping[str, Any] | list[Any] | None = None,
        modify_url: str | None = None,
    ) -> dict[str, Any]:
        """对指定历史 HttpFlow 执行参数变异重放并计算新旧响应差异。

        Args:
            flow_id: 目标历史 HttpFlow 的唯一 ID。
            modify_headers: 可选的覆盖或新增请求头字典。
            modify_body: 可选覆盖请求体文本或 JSON；为 None 时使用无损原始请求体字节。
            modify_url: 可选的覆盖请求目标 URL；为 None 时使用历史原 URL。

        Returns:
            包含原响应摘要、新响应摘要及结构化 diff 对比信息的字典。

        Raises:
            ValueError: 当指定的 flow_id 不存在时抛出。
        """
        # 1. 读取完整无损的历史 HttpFlow 与原始请求/响应字节
        flow_data = self.storage.get_flow_for_replay(flow_id)
        if flow_data is None:
            raise ValueError(f"未找到指定的历史 HttpFlow 记录: {flow_id}")

        target_url = (
            modify_url.strip() if modify_url and modify_url.strip() else str(flow_data["url"])
        )
        method = str(flow_data["method"]).upper()
        headers = _merge_request_headers(flow_data["request_headers"], modify_headers)
        if modify_body is None:
            content_bytes = bytes(flow_data["request_body_bytes"])
        elif isinstance(modify_body, str):
            content_bytes = modify_body.encode("utf-8")
        else:
            content_bytes = json.dumps(modify_body, ensure_ascii=False).encode("utf-8")

        # 2. 通过 httpx 发起独立异步重放请求并统计耗时
        started_at = time.perf_counter()
        async with httpx.AsyncClient(
            verify=False,
            follow_redirects=False,
            timeout=self._timeout,
            transport=self._transport,
        ) as client:
            response = await client.request(
                method=method,
                url=target_url,
                headers=headers,
                content=content_bytes,
            )
        replayed_duration_ms = round((time.perf_counter() - started_at) * 1000.0, 2)

        # 3. 解析新响应载荷并构建新旧对比 Diff 报告
        new_body_bytes = response.content
        new_ct = response.headers.get("content-type")
        is_new_binary = _is_binary_payload(new_body_bytes, new_ct)
        new_preview, new_truncated = _decode_preview(
            new_body_bytes, is_new_binary, DEFAULT_PREVIEW_CHARS
        )

        old_body_bytes = bytes(flow_data["response_body_bytes"])
        is_old_binary = bool(flow_data["is_response_binary"])
        old_preview, old_truncated = _decode_preview(
            old_body_bytes, is_old_binary, DEFAULT_PREVIEW_CHARS
        )

        old_status = flow_data["status_code"]
        new_status = int(response.status_code)
        old_duration = flow_data["duration_ms"]
        duration_delta = (
            round(replayed_duration_ms - float(old_duration), 2)
            if old_duration is not None
            else None
        )

        diff_preview = _build_body_diff_preview(
            old_body_bytes,
            new_body_bytes,
            is_old_binary,
            is_new_binary,
        )

        return {
            "flow_id": flow_id,
            "method": method,
            "target_url": target_url,
            "original_response": {
                "status_code": old_status,
                "duration_ms": old_duration,
                "headers": flow_data["response_headers"],
                "body_size": len(old_body_bytes),
                "body_preview": old_preview,
                "body_truncated": old_truncated,
            },
            "replayed_response": {
                "status_code": new_status,
                "duration_ms": replayed_duration_ms,
                "headers": dict(response.headers),
                "body_size": len(new_body_bytes),
                "body_preview": new_preview,
                "body_truncated": new_truncated,
            },
            "diff": {
                "status_code_before": old_status,
                "status_code_after": new_status,
                "status_code_changed": old_status != new_status,
                "duration_ms_before": old_duration,
                "duration_ms_after": replayed_duration_ms,
                "duration_ms_delta": duration_delta,
                "body_size_before": len(old_body_bytes),
                "body_size_after": len(new_body_bytes),
                "body_size_delta": len(new_body_bytes) - len(old_body_bytes),
                "body_changed": old_body_bytes != new_body_bytes,
                "body_diff_preview": diff_preview,
            },
        }
