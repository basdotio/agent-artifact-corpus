"""mitmdump 流量采集与非阻塞规则拦截插件模块，负责采集过滤、规则 Mock/改写、解压与入库。

@author Ateng
@since 2026-10-13
"""

from __future__ import annotations

import fnmatch
import gzip
import logging
import os
import re
import time
import zlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from uuid import uuid4

from mitmproxy import http as mitm_http

from mcp_server_traffic_inspector.config import LOGGER_NAME
from mcp_server_traffic_inspector.storage import StorageBus, _format_url

logger = logging.getLogger(LOGGER_NAME)


def _matches_filter_host(request_host: str, filter_host: str | None) -> bool:
    if not filter_host or not filter_host.strip():
        return True
    target = filter_host.strip().lower()
    host_lower = (request_host or "").strip().lower()
    if not host_lower:
        return False
    return host_lower == target or host_lower.endswith(f".{target}") or target in host_lower


def _extract_flow_url(req: Any) -> str:
    pretty_url = getattr(req, "pretty_url", None)
    if pretty_url:
        return str(pretty_url)
    scheme = str(getattr(req, "scheme", "http"))
    host = str(getattr(req, "pretty_host", None) or getattr(req, "host", "") or "")
    port = int(getattr(req, "port", 443 if scheme == "https" else 80))
    path = str(getattr(req, "path", "/"))
    return _format_url(scheme, host, port, path)


def _matches_url_pattern(url: str, pattern: str) -> bool:
    if not pattern:
        return False
    if pattern in url:
        return True
    if "*" in pattern or "?" in pattern:
        if fnmatch.fnmatch(url, pattern) or fnmatch.fnmatch(url, f"*{pattern}*"):
            return True
    try:
        if re.search(pattern, url):
            return True
    except re.error:
        return False
    return False


def _extract_headers_dict(headers_obj: Any) -> dict[str, str]:
    if not headers_obj:
        return {}
    if isinstance(headers_obj, Mapping):
        return {str(k): str(v) for k, v in headers_obj.items()}
    if hasattr(headers_obj, "items"):
        return {str(k): str(v) for k, v in headers_obj.items()}
    return {}


def _apply_headers_mutation(target_obj: Any, headers_to_set: Mapping[str, str]) -> None:
    if target_obj is None or not headers_to_set:
        return
    headers_attr = getattr(target_obj, "headers", None)
    if headers_attr is None:
        return
    for key, val in headers_to_set.items():
        headers_attr[str(key)] = str(val)


def _extract_decompressed_body(message_obj: Any, headers: Mapping[str, str]) -> bytes:
    if message_obj is None:
        return b""

    if hasattr(message_obj, "get_content"):
        try:
            content = message_obj.get_content(strict=False)
            if content is not None:
                return bytes(content)
        except Exception as exc:
            logger.debug("调用 mitmproxy get_content 解压失败，回退至原始字节: %s", exc)

    raw = getattr(message_obj, "raw_content", None) or getattr(message_obj, "content", None) or b""
    raw_bytes = bytes(raw)
    if not raw_bytes:
        return b""

    encoding = ""
    for k, v in headers.items():
        if k.lower() == "content-encoding" and v:
            encoding = v.strip().lower()
            break

    try:
        if encoding == "gzip":
            return gzip.decompress(raw_bytes)
        if encoding == "deflate":
            return zlib.decompress(raw_bytes)
    except Exception as exc:
        logger.debug("手动解压 %s 载荷失败，保留原始字节: %s", encoding, exc)

    return raw_bytes


def _calculate_duration_ms(request_obj: Any, response_obj: Any) -> float | None:
    req_start = getattr(request_obj, "timestamp_start", None)
    if req_start is None:
        return None
    resp_end = (
        getattr(response_obj, "timestamp_end", None)
        or getattr(response_obj, "timestamp_start", None)
        or getattr(request_obj, "timestamp_end", None)
    )
    if resp_end is None:
        return None
    return round(max(0.0, (float(resp_end) - float(req_start)) * 1000.0), 2)


class TrafficCaptureAddon:
    """挂载于 mitmdump 子进程的 HTTP/HTTPS 流量录制与非阻塞规则拦截插件。

    支持从 SQLite 热同步 InterceptRule（Mock 短路返回与请求/响应头动态改写），
    根据 filter_host 执行非侵入采集过滤，并自动解压 BodyPayload 写入共享 SQLite WAL 总线。
    """

    def __init__(
        self,
        storage: StorageBus,
        session_id: str,
        filter_host: str | None = None,
    ) -> None:
        """初始化抓包与拦截插件实例。

        Args:
            storage: 指向共享 SQLite WAL 的 StorageBus 实例。
            session_id: 当前抓包会话 CaptureSession 的唯一 ID。
            filter_host: 可选的目标采集域名过滤条件。
        """
        self.storage = storage
        self.session_id = session_id
        self.filter_host = filter_host.strip() if filter_host and filter_host.strip() else None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> TrafficCaptureAddon:
        """从子进程环境变量初始化插件实例。

        Args:
            env: 环境变量映射表，为 None 时默认读取 os.environ。

        Returns:
            绑定了共享数据库与会话配置的 TrafficCaptureAddon 实例。
        """
        env_map = env if env is not None else os.environ
        db_path = Path(env_map["MCP_CAPTURE_DB_PATH"]).resolve()
        bodies_dir = Path(
            env_map.get("MCP_CAPTURE_BODIES_DIR") or db_path.parent / "bodies"
        ).resolve()
        session_id = env_map.get("MCP_CAPTURE_SESSION_ID") or f"sess_{uuid4().hex[:12]}"
        filter_host = env_map.get("MCP_CAPTURE_FILTER_HOST") or None

        storage = StorageBus(db_path=db_path, bodies_dir=bodies_dir, preserve_db=True)
        storage.initialize()
        return cls(storage=storage, session_id=session_id, filter_host=filter_host)

    def _load_matching_rules(self, url: str) -> list[dict[str, Any]]:
        try:
            active_rules = self.storage.list_intercept_rules(only_enabled=True)
        except Exception as exc:
            logger.debug("读取动态拦截规则失败: %s", exc)
            return []
        return [r for r in active_rules if _matches_url_pattern(url, str(r["url_pattern"]))]

    def request(self, flow: Any) -> None:
        """mitmproxy 请求到达阶段钩子，热读取规则执行请求头改写或 Mock 短路返回。

        Args:
            flow: mitmproxy HTTPFlow 实例。
        """
        req = getattr(flow, "request", None)
        if req is None:
            return

        # 1. 热查询匹配当前请求 URL 的生效拦截规则
        url = _extract_flow_url(req)
        matched_rules = self._load_matching_rules(url)
        if not matched_rules:
            return

        # 2. 按序应用请求头改写、延迟注入或触发 Mock/Abort
        for rule in matched_rules:
            rule_id = rule.get("id")
            # 1. 延迟注入仿真
            delay_ms = int(rule.get("delay_ms") or 0)
            if delay_ms > 0:
                time.sleep(delay_ms / 1000.0)

            # 2. 统计命中并触发原子递增
            if rule_id:
                try:
                    self.storage.increment_rule_hit(rule_id)
                except Exception as exc:
                    logger.debug("累加规则命中计数失败: %s", exc)

            # 3. 故障模拟：主动强制切断连接 (abort)
            if rule.get("action") == "abort":
                if hasattr(flow, "kill"):
                    flow.kill()
                return

            req_mods = rule.get("modify_request_headers") or {}
            if req_mods:
                _apply_headers_mutation(req, req_mods)

            if rule.get("action") == "mock":
                status_code = int(rule.get("mock_status") or 200)
                body_str = rule.get("mock_body") or ""
                body_bytes = body_str.encode("utf-8")
                headers_dict = {str(k): str(v) for k, v in (rule.get("mock_headers") or {}).items()}
                flow.response = mitm_http.Response.make(
                    status_code=status_code,
                    content=body_bytes,
                    headers=headers_dict,
                )
                return

    def _persist_flow(self, flow: Any, has_error: bool = False) -> None:
        req = getattr(flow, "request", None)
        if req is None:
            return

        # 1. 执行 filter_host 采集过滤（非匹配域名直接跳过入库，不影响代理正常转发）
        host = str(getattr(req, "pretty_host", None) or getattr(req, "host", "") or "")
        if not _matches_filter_host(host, self.filter_host):
            return

        # 2. 提取并解压请求与响应头部及 BodyPayload
        resp = getattr(flow, "response", None)
        err = getattr(flow, "error", None)
        flow_id = str(getattr(flow, "id", None) or uuid4().hex)
        timestamp = float(getattr(req, "timestamp_start", None) or time.time())
        method = str(getattr(req, "method", "GET"))
        scheme = str(getattr(req, "scheme", "http"))
        port = int(getattr(req, "port", 443 if scheme == "https" else 80))
        path = str(getattr(req, "path", "/"))

        req_headers = _extract_headers_dict(getattr(req, "headers", None))
        resp_headers = _extract_headers_dict(getattr(resp, "headers", None)) if resp else {}
        req_body = _extract_decompressed_body(req, req_headers)
        resp_body = _extract_decompressed_body(resp, resp_headers) if resp else b""

        status_code = int(getattr(resp, "status_code", 0)) if resp is not None else None
        duration_ms = _calculate_duration_ms(req, resp)
        error_msg = str(getattr(err, "msg", err)) if err is not None else None

        # 3. 写入 SQLite WAL 共享数据总线
        try:
            self.storage.record_http_flow(
                flow_id=flow_id,
                session_id=self.session_id,
                timestamp=timestamp,
                method=method,
                scheme=scheme,
                host=host,
                port=port,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
                request_headers=req_headers,
                response_headers=resp_headers,
                request_body=req_body,
                response_body=resp_body,
                has_error=has_error or (err is not None),
                error_message=error_msg,
            )
        except Exception as exc:
            logger.warning("写入 HttpFlow (%s) 至 SQLite 失败: %s", flow_id, exc)

    def response(self, flow: Any) -> None:
        """mitmproxy 响应完成事件钩子，执行响应头改写规则并持久化流记录。

        Args:
            flow: mitmproxy HTTPFlow 实例。
        """
        req = getattr(flow, "request", None)
        resp = getattr(flow, "response", None)
        if req is not None and resp is not None:
            url = _extract_flow_url(req)
            for rule in self._load_matching_rules(url):
                resp_mods = rule.get("modify_response_headers") or {}
                if resp_mods:
                    _apply_headers_mutation(resp, resp_mods)

        self._persist_flow(flow, has_error=False)

    def error(self, flow: Any) -> None:
        """mitmproxy 请求/响应发生传输错误事件钩子。

        Args:
            flow: mitmproxy HTTPFlow 实例。
        """
        self._persist_flow(flow, has_error=True)

    def websocket_message(self, flow: Any) -> None:
        """mitmproxy WebSocket 帧到达事件钩子，提取消息方向、Opcode 与载荷写入 SQLite。

        Args:
            flow: mitmproxy HTTPFlow 实例。
        """
        ws = getattr(flow, "websocket", None)
        if ws is None:
            return
        messages = getattr(ws, "messages", None)
        if not messages:
            return
        latest_msg = messages[-1]

        # 1. 过滤 host 采集规则
        req = getattr(flow, "request", None)
        host = str(getattr(req, "pretty_host", None) or getattr(req, "host", "") or "")
        if not _matches_filter_host(host, self.filter_host):
            return

        # 2. 提取帧属性
        flow_id = str(getattr(flow, "id", None) or uuid4().hex)
        from_client = bool(getattr(latest_msg, "from_client", True))
        direction = "client_to_server" if from_client else "server_to_client"
        msg_type = getattr(latest_msg, "type", 1)

        opcode = 1
        opcode_name = "TEXT"
        if hasattr(msg_type, "value") and hasattr(msg_type, "name"):
            try:
                opcode = int(msg_type.value)
            except (ValueError, TypeError):
                opcode = 1
            opcode_name = str(msg_type.name)
        elif isinstance(msg_type, int):
            opcode = msg_type
            opcode_map = {1: "TEXT", 2: "BINARY", 8: "CLOSE", 9: "PING", 10: "PONG"}
            opcode_name = opcode_map.get(opcode, "UNKNOWN")
        elif isinstance(msg_type, str):
            opcode_name = msg_type.upper()
            reverse_map = {"TEXT": 1, "BINARY": 2, "CLOSE": 8, "PING": 9, "PONG": 10}
            opcode = reverse_map.get(opcode_name, 1)

        content = getattr(latest_msg, "content", b"")
        timestamp = float(getattr(latest_msg, "timestamp", None) or time.time())

        # 3. 写入共享存储
        try:
            self.storage.record_websocket_message(
                flow_id=flow_id,
                session_id=self.session_id,
                timestamp=timestamp,
                direction=direction,
                opcode=opcode,
                opcode_name=opcode_name,
                content=content,
            )
        except Exception as exc:
            logger.warning("写入 WebSocket 帧消息失败 (flow=%s): %s", flow_id, exc)


addons: list[TrafficCaptureAddon] = (
    [TrafficCaptureAddon.from_env()] if os.environ.get("MCP_CAPTURE_DB_PATH") else []
)
