"""FastMCP 服务主控底座、MCP 工具注册与进程生命周期清理编排模块。

@author Ateng
@since 2026-10-13
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_server_traffic_inspector.capture_manager import HttpCaptureManager
from mcp_server_traffic_inspector.config import LOGGER_NAME, ServerConfig
from mcp_server_traffic_inspector.diagnostics import NetworkDiagnostics
from mcp_server_traffic_inspector.doctor import (
    get_ca_env_vars,
)
from mcp_server_traffic_inspector.doctor import (
    trust_ca_certificate as do_trust_ca,
)
from mcp_server_traffic_inspector.har_exporter import HarExporter
from mcp_server_traffic_inspector.pcap import PcapCaptureManager
from mcp_server_traffic_inspector.replay import FlowReplayEngine
from mcp_server_traffic_inspector.storage import DEFAULT_PREVIEW_CHARS, StorageBus
from mcp_server_traffic_inspector.system_proxy import (
    SystemProxyManager,
)
from mcp_server_traffic_inspector.system_proxy import (
    get_ca_certificate as get_ca_cert_info,
)

logger = logging.getLogger(LOGGER_NAME)

SERVER_NAME = "mcp-server-traffic-inspector"
SERVER_INSTRUCTIONS = (
    "全栈网络流量巡检与抓包 MCP Server。"
    "支持 HTTP/HTTPS 代理抓包会话 (CaptureSession)、流量检索 (HttpFlow)、"
    "报文载荷预览与转储 (BodyPayload)、非阻塞规则拦截 (InterceptRule)、"
    "请求变异重放 (FlowReplay)、网卡/离线 PCAP 协议分析 (PcapCapture) "
    "及智能根因诊断 (SessionDiagnosis)。"
)


class LifecycleManager:
    """主控进程退出钩子管理器，负责按逆序安全回收子进程、系统代理与临时存储。"""

    def __init__(self) -> None:
        self._callbacks: list[Callable[[], None]] = []
        self._cleaned_up = False

    def register(self, callback: Callable[[], None]) -> None:
        """注册退出清理回调函数。

        Args:
            callback: 无参清理回调，将在服务终止时按后进先出顺序执行。
        """
        self._callbacks.append(callback)

    def run_cleanup(self) -> None:
        """幂等执行全部已注册的清理回调，单项异常不中断后续回收流程。"""
        if self._cleaned_up:
            return
        self._cleaned_up = True

        for callback in reversed(self._callbacks):
            try:
                callback()
            except Exception as exc:
                logger.warning("执行退出清理回调时发生异常: %s", exc)


def _register_http_tools(
    mcp: FastMCP,
    storage: StorageBus,
    manager: HttpCaptureManager,
    system_proxy: SystemProxyManager,
    har_exporter: HarExporter,
) -> None:
    @mcp.tool()
    def start_http_capture(
        port: int = 8080,
        listen_host: str = "0.0.0.0",
        filter_host: str | None = None,
        ssl_insecure: bool = True,
        auto_set_system_proxy: bool = False,
    ) -> dict[str, Any]:
        """启动受控 mitmdump 后台代理会话 (CaptureSession) 捕获 HTTP/HTTPS 流量。

        Args:
            port: 代理监听端口，默认 8080。
            listen_host: 代理监听地址，默认 "0.0.0.0"。
            filter_host: 可选的目标采集域名（非目标域名正常转发，仅目标域名写入数据库）。
            ssl_insecure: 是否忽略上游服务端 TLS 证书错误，默认 True。
            auto_set_system_proxy: 是否启动后自动将系统代理设为当前端口，默认 False。

        Returns:
            包含状态、端口、session_id、db_path、ca_cert_path 及系统代理信息的字典。
        """
        res = manager.start_capture(
            port=port,
            listen_host=listen_host,
            filter_host=filter_host,
            ssl_insecure=ssl_insecure,
        )
        if auto_set_system_proxy:
            proxy_res = system_proxy.toggle_proxy(enable=True, host="127.0.0.1", port=port)
            res["system_proxy"] = proxy_res
        return res

    @mcp.tool()
    def stop_http_capture(
        auto_export_har: bool = True,
        har_output_path: str | None = None,
        restore_system_proxy: bool = True,
    ) -> dict[str, Any]:
        """停止 HTTP 抓包代理，支持自动导出 HAR 归档并按所有权安全复位系统代理。

        Args:
            auto_export_har: 是否自动将当前会话全量数据导出为 HAR 1.2 归档文件，默认 True。
            har_output_path: 导出的目标 HAR 文件路径；为空时自动在系统临时目录生成。
            restore_system_proxy: 是否在停止抓包后安全复位操作系统代理状态，默认 True。

        Returns:
            包含 status、session_id、total_captured_flows、har_export 及 system_proxy 的字典。
        """
        running_port = manager._port or 8080
        running_host = manager._listen_host or "127.0.0.1"

        res = manager.stop_capture()
        session_id = res.get("session_id")

        # 1. 自动导出 HAR 1.2 归档文件
        if auto_export_har and session_id:
            try:
                if not har_output_path or not har_output_path.strip():
                    temp_dir = Path(tempfile.gettempdir()) / "har_captures"
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    resolved_output = temp_dir / f"traffic_{session_id}_{int(time.time())}.har"
                else:
                    resolved_output = Path(har_output_path).resolve()

                export_res = har_exporter.export_session(
                    output_path=resolved_output,
                    session_id=session_id,
                    format="har",
                )
                res["har_export"] = {
                    "exported": True,
                    "file_path": export_res["exported_path"],
                    "flow_count": export_res["flow_count"],
                    "file_size_bytes": export_res["file_size_bytes"],
                }
            except Exception as exc:
                logger.warning("停止抓包时自动导出 HAR 发生异常: %s", exc)
                res["har_export"] = {
                    "exported": False,
                    "error": str(exc),
                }

        # 2. 智能安全复位系统代理 (Proxy Ownership Check)
        if restore_system_proxy:
            proxy_res = system_proxy.smart_restore(
                expected_host=running_host,
                expected_port=running_port,
            )
            res["system_proxy"] = proxy_res

        return res

    @mcp.tool()
    def get_capture_status() -> dict[str, Any]:
        """查询当前 HTTP 抓包代理运行状态、会话 ID、已捕获流数量与运行时长。

        Returns:
            包含 is_capturing、listen_host、port、session_id、flow_count 与 uptime_seconds 的字典。
        """
        return manager.get_status()

    @mcp.tool()
    def list_http_flows(
        limit: int = 20,
        offset: int = 0,
        session_id: str | None = None,
        host: str | None = None,
        query: str | None = None,
        status_code: int | None = None,
        status_family: str | None = None,
        method: str | None = None,
        min_duration_ms: float | None = None,
        sort_by: str = "timestamp",
        compact: bool = False,
    ) -> dict[str, Any]:
        """按多维条件分页检索已捕获的 HttpFlow 轻量元数据列表（支持全文模糊过滤与紧凑模式）。

        Args:
            limit: 单页返回最大条数，默认 20。
            offset: 分页起始偏移量，默认 0。
            session_id: 可选抓包会话 ID；未指定时检索全部已录制会话。
            host: 按目标域名子串过滤（不区分大小写）。
            query: 按 URL 路径、完整地址或主机名进行模糊匹配，提升检索效率。
            status_code: 按精确 HTTP 状态码过滤。
            status_family: 按状态码族过滤（可选: 2xx, 3xx, 4xx, 5xx, error）。
            method: 按 HTTP 方法过滤（如 GET、POST）。
            min_duration_ms: 按最小请求耗时（毫秒）过滤慢请求。
            sort_by: 排序字段（timestamp、duration_ms、size）。
            compact: 是否开启紧凑模式（仅保留核心调试字段，节约 Token），默认 False。

        Returns:
            包含 total、summary_metrics、session_id 与 flows 的字典；无匹配时 flows 为 []。
        """
        return storage.list_http_flows(
            limit=limit,
            offset=offset,
            session_id=session_id,
            host=host,
            query=query,
            status_code=status_code,
            status_family=status_family,
            method=method,
            min_duration_ms=min_duration_ms,
            sort_by=sort_by,
            compact=compact,
        )

    @mcp.tool()
    def get_http_flow_detail(
        flow_id: str,
        include_headers: bool = True,
        include_body: bool = True,
        max_body_chars: int = DEFAULT_PREVIEW_CHARS,
        dump_body_to_file: bool = False,
    ) -> dict[str, Any]:
        """查询单条 HttpFlow 的完整请求/响应头与截断预览 BodyPayload，支持导出完整载荷文件。

        Args:
            flow_id: 目标 HttpFlow 的唯一 ID。
            include_headers: 是否包含请求与响应 Headers，默认 True。
            include_body: 是否包含请求与响应 BodyPayload 预览，默认 True。
            max_body_chars: 文本载荷预览最大截断字符数，默认 2048。
            dump_body_to_file: 是否将完整原始载荷写出为本地文件并返回绝对路径，默认 False。

        Returns:
            包含请求行、状态码、耗时、Headers、截断预览与文件路径的详情字典。

        Raises:
            ValueError: 当指定的 flow_id 不存在时抛出。
        """
        detail = storage.get_http_flow_detail(
            flow_id,
            include_headers=include_headers,
            include_body=include_body,
            max_body_chars=max_body_chars,
            dump_body_to_file=dump_body_to_file,
        )
        if detail is None:
            raise ValueError(f"未找到指定的 HttpFlow 记录: {flow_id}")
        return detail


def _register_manipulation_tools(
    mcp: FastMCP,
    storage: StorageBus,
    replay_engine: FlowReplayEngine,
) -> None:
    @mcp.tool()
    async def replay_http_request(
        flow_id: str,
        modify_headers: dict[str, str] | None = None,
        modify_body: str | dict[str, Any] | list[Any] | None = None,
        modify_url: str | None = None,
    ) -> dict[str, Any]:
        """基于已捕获的历史 HttpFlow 执行参数变异重放 (FlowReplay)，并对比新旧响应差异。

        Args:
            flow_id: 待重放的历史 HttpFlow 唯一 ID。
            modify_headers: 可选的覆盖或新增请求头字典。
            modify_body: 可选的覆盖请求体文本；不传时使用存储层完整无损的原始请求体。
            modify_url: 可选的覆盖目标 URL；不传时使用原请求 URL。

        Returns:
            包含原响应摘要、新响应摘要及状态码、耗时与正文 Diff 预览的结构化对比字典。
        """
        return await replay_engine.replay(
            flow_id=flow_id,
            modify_headers=modify_headers,
            modify_body=modify_body,
            modify_url=modify_url,
        )

    @mcp.tool()
    def add_intercept_rule(
        url_pattern: str,
        action: str = "mock",
        mock_status: int = 200,
        mock_headers: dict[str, str] | None = None,
        mock_body: str | dict[str, Any] | list[Any] | None = None,
        modify_request_headers: dict[str, str] | None = None,
        modify_response_headers: dict[str, str] | None = None,
        delay_ms: int = 0,
        max_hits: int | None = None,
    ) -> dict[str, Any]:
        """新增一条非阻塞动态拦截规则 (InterceptRule)，支持 Mock、Header 改写、延迟与混沌故障注入。

        Args:
            url_pattern: 目标 URL 匹配模式（支持正则、通配符或子串）。
            action: 规则动作，可选 'mock'、'modify'、'delay' 或 'abort'（模拟连接异常断开），
                默认 'mock'。
            mock_status: 当 action='mock' 时返回的状态码，默认 200。
            mock_headers: 当 action='mock' 时返回的自定义响应头。
            mock_body: 当 action='mock' 时返回的响应正文。
            modify_request_headers: 转发前注入或改写的请求头。
            modify_response_headers: 返回前注入或改写的响应头。
            delay_ms: 注入的响应前置延迟（毫秒），用于仿真慢接口或超时边界，默认 0。
            max_hits: 最大触发次数上限；达到指定命中次数后规则自动安全失活（None 表示持续有效）。

        Returns:
            包含 rule_id、action、url_pattern、delay_ms、max_hits 与 status ("active") 的字典。
        """
        return storage.add_intercept_rule(
            url_pattern=url_pattern,
            action=action,
            mock_status=mock_status,
            mock_headers=mock_headers,
            mock_body=mock_body,
            modify_request_headers=modify_request_headers,
            modify_response_headers=modify_response_headers,
            delay_ms=delay_ms,
            max_hits=max_hits,
        )

    @mcp.tool()
    def list_intercept_rules() -> list[dict[str, Any]]:
        """查看当前配置的全部动态拦截与改写规则 (InterceptRule)。

        Returns:
            拦截规则字典列表；无规则时固定返回 []。
        """
        return storage.list_intercept_rules()

    @mcp.tool()
    def clear_intercept_rules(rule_id: str | None = None) -> dict[str, Any]:
        """清空全部动态拦截规则，或按指定 rule_id 移除单条规则。

        Args:
            rule_id: 可选的目标规则 ID；为空时清空全部规则。

        Returns:
            包含 cleared_count 与 target_rule_id 的清理结果字典。
        """
        return storage.clear_intercept_rules(rule_id=rule_id)

    @mcp.tool()
    def list_websocket_messages(
        flow_id: str | None = None,
        session_id: str | None = None,
        include_heartbeats: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """按握手流或会话分页查询已捕获的 WebSocket 消息帧列表（可过滤心跳帧）。

        Args:
            flow_id: 可选的握手 HttpFlow 唯一 ID。
            session_id: 可选的抓包会话 ID。
            include_heartbeats: 是否包含 PING/PONG 心跳消息帧，默认 False（自动抑制）。
            limit: 单页返回最大帧数，默认 100。
            offset: 分页偏移量，默认 0。

        Returns:
            包含 total、flow_id 与 messages 列表的字典；无匹配时 messages 固定为 []。
        """
        return storage.list_websocket_messages(
            flow_id=flow_id,
            session_id=session_id,
            include_heartbeats=include_heartbeats,
            limit=limit,
            offset=offset,
        )

    @mcp.tool()
    def get_websocket_message_detail(
        message_id: str,
        max_body_chars: int = 2048,
        dump_to_file: bool = False,
    ) -> dict[str, Any] | None:
        """获取单个 WebSocket 消息帧的完整解码内容、Opcode 属性与可选落盘文件路径。

        Args:
            message_id: 目标 WebSocket 消息的唯一 ID。
            max_body_chars: 文本预览最大截断字符数，默认 2048。
            dump_to_file: 是否将完整载荷导出为独立本地文件并返回绝对路径。

        Returns:
            消息详情字典；若 message_id 不存在则返回 None。
        """
        return storage.get_websocket_message_detail(
            message_id=message_id,
            max_body_chars=max_body_chars,
            dump_to_file=dump_to_file,
        )


def _register_pcap_tools(
    mcp: FastMCP,
    pcap_manager: PcapCaptureManager,
) -> None:
    @mcp.tool()
    def list_network_interfaces() -> list[dict[str, Any]]:
        """枚举当前主机可用于抓包的网络接口列表。

        Returns:
            包含 index、name 与 description 的网卡列表；未安装 tshark 或无网卡时返回 []。
        """
        return pcap_manager.list_interfaces()

    @mcp.tool()
    def start_pcap_capture(
        interface: int | str | list[int | str] = 1,
        output_path: str | None = None,
        bpf_filter: str | None = None,
        max_packets: int = 2000,
        duration_seconds: int = 60,
        process_path: str | None = None,
        process_name: str | None = None,
        target_pids: list[int] | None = None,
        include_child_processes: bool = True,
        keep_raw_pcap: bool = False,
    ) -> dict[str, Any]:
        """在指定网卡启动原始网络层数据包捕获 (PcapCapture)，支持进程树过滤与多服务器拓扑审计。

        Args:
            interface: 网卡索引、名称、'loopback'、'auto' 或网卡标识符列表，默认 1。
            output_path: 保存目标 .pcap 文件绝对路径；为空时自动生成。
            bpf_filter: 可选的 Berkeley Packet Filter 表达式（如 'tcp and port 443'）。
            max_packets: 最大抓包数熔断上限，默认 2000 包。
            duration_seconds: 最大抓包时长熔断上限，默认 60 秒。
            process_path: 可选的目标可执行文件绝对路径（如 'C:\\Program Files\\...\\Weixin.exe'）。
            process_name: 可选的目标进程名称通配符（如 'Weixin*.exe'）。
            target_pids: 可选的显式指定目标 PID 列表。
            include_child_processes: 是否递归追踪目标进程的所有派生子进程，默认 True。
            keep_raw_pcap: 是否保留全量中间抓包文件，默认 False（自动清理）。

        Returns:
            包含状态、网卡、产出文件绝对路径与熔断限制的字典。
        """
        return pcap_manager.start_capture(
            interface=interface,
            output_path=output_path,
            bpf_filter=bpf_filter,
            max_packets=max_packets,
            duration_seconds=duration_seconds,
            process_path=process_path,
            process_name=process_name,
            target_pids=target_pids,
            include_child_processes=include_child_processes,
            keep_raw_pcap=keep_raw_pcap,
        )

    @mcp.tool()
    def stop_pcap_capture() -> dict[str, Any]:
        """停止当前正在运行的实时 PCAP 网卡抓包任务并返回数据包统计。

        Returns:
            包含 status ("stopped")、pcap_file 与 packet_count 的字典。
        """
        return pcap_manager.stop_capture()

    @mcp.tool()
    def analyze_pcap_file(
        file_path: str,
        display_filter: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """调用 tshark 对离线 .pcap/.pcapng 报文执行协议分布、TCP 重传率与 DNS 深度分析。

        Args:
            file_path: 本地 .pcap / .pcapng 文件路径。
            display_filter: 可选的 Wireshark Display Filter 过滤表达式。
            limit: 分析的最大报文上限数，默认 50。

        Returns:
            包含总报文数、协议占比、TCP 质量指标与 DNS 统计的诊断字典。
        """
        return pcap_manager.analyze_pcap(
            file_path=file_path,
            display_filter=display_filter,
            limit=limit,
        )

    @mcp.tool()
    def list_tcp_streams(
        file_path: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """从指定的离线 PCAP 文件中提取并枚举所有 TCP 会话流及其端点、包数与载荷大小。

        Args:
            file_path: 目标 PCAP 本地文件路径。
            limit: 最大返回流条数，默认 50。

        Returns:
            按 stream_id 升序排列的 TCP 流列表；无匹配时返回空列表 []。
        """
        return pcap_manager.list_tcp_streams(file_path=file_path, limit=limit)

    @mcp.tool()
    def follow_tcp_stream(
        file_path: str,
        stream_id: int,
        format: str = "turns",
    ) -> dict[str, Any]:
        """重组并跟踪指定 TCP 流的数据交互，按客户端与服务端方向聚合为回合 (Turns)。

        Args:
            file_path: 目标 PCAP 本地文件路径。
            stream_id: 待跟踪的 TCP 流 ID（如 0, 1）。
            format: 数据组织格式，支持 'turns'（默认回合制）、'raw' 与 'hex'。

        Returns:
            包含客户端/服务端端点、回合统计与时序报文数据的结构化字典。
        """
        return pcap_manager.follow_tcp_stream(
            file_path=file_path,
            stream_id=stream_id,
            format=format,
        )


def _register_diagnostic_tools(
    mcp: FastMCP,
    diagnostics: NetworkDiagnostics,
) -> None:
    @mcp.tool()
    def analyze_http_traffic(
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """统计慢请求 Top 5、状态码分布、高频端点 Top 10 与总吞吐流量。

        Args:
            session_id: 可选的目标抓包会话 ID；未提供时默认统计最近一次抓包会话。

        Returns:
            包含慢请求排行、错误分布、高频端点及大报文消耗的聚合统计字典。
        """
        return diagnostics.analyze_http_traffic(session_id=session_id)

    @mcp.tool()
    def diagnose_network_session(
        session_type: str = "http",
        target: str | None = None,
    ) -> dict[str, Any]:
        """对 HTTP 流量或 PCAP 报文生成结构化健康度评分、异常项与根因诊断报告。

        Args:
            session_type: 诊断类型，可选 'http' 或 'pcap'，默认 'http'。
            target: 当 session_type='http' 时为可选 session_id；当 'pcap' 时为必填文件路径。

        Returns:
            包含健康度评分、健康状态、异常清单与排障建议的诊断报告。
        """
        return diagnostics.diagnose_network_session(
            session_type=session_type,
            target=target,
        )


def _register_ops_tools(
    mcp: FastMCP,
    system_proxy: SystemProxyManager,
    har_exporter: HarExporter,
) -> None:
    """注册 CA 证书指引、跨平台系统代理托管与 HAR 会话归档导出工具集。"""

    @mcp.tool()
    def trust_ca_certificate(
        system_wide: bool = False,
        ca_cert_path: str | None = None,
    ) -> dict[str, Any]:
        """将 mitmproxy CA 根证书导入系统信任库并提供常见运行时环境变量字典。

        在 Windows 默认免 UAC 提权注入当前用户证书库 (CurrentUser\\Root)；
        自动生成 NODE_EXTRA_CA_CERTS、SSL_CERT_FILE、REQUESTS_CA_BUNDLE 等环境配置。

        Args:
            system_wide: 是否尝试安装至系统级受信任根证书库（需要管理员权限），默认 False。
            ca_cert_path: 可选的显式 CA 证书路径；为空时自动检索本地 ~/.mitmproxy 目录。

        Returns:
            包含 status、ca_cert_path、platform、system_wide、env_vars 及 details 的字典。
        """
        return do_trust_ca(system_wide=system_wide, ca_cert_path=ca_cert_path)

    @mcp.tool()
    def get_ca_certificate(
        install_to_system: bool = False,
    ) -> dict[str, Any]:
        """获取 mitmproxy 本地 CA 根证书路径及跨平台信任安装指引，在 Windows 上支持自动导入。

        Args:
            install_to_system: 是否在 Windows 自动执行 certutil 安装至受信任根证书库，
                默认 False。

        Returns:
            包含证书文件路径、安装指引及可选安装执行结果的结构化字典。
        """
        return get_ca_cert_info(install_to_system=install_to_system)

    @mcp.tool()
    def toggle_system_proxy(
        enable: bool,
        port: int = 8080,
        host: str = "127.0.0.1",
    ) -> dict[str, Any]:
        """开启或关闭操作系统全局代理（Windows 注册表托管；非 Windows 优雅降级指引）。

        Args:
            enable: 是否开启系统代理。
            port: 代理端口，默认 8080。
            host: 代理主机地址，默认 127.0.0.1。

        Returns:
            包含平台支持状态、当前代理开启状态及详细说明的结构化字典。
        """
        return system_proxy.toggle_proxy(enable=enable, host=host, port=port)

    @mcp.tool()
    def get_system_proxy_status(
        port: int = 8080,
        host: str = "127.0.0.1",
    ) -> dict[str, Any]:
        """主动探查宿主机当前操作系统全局代理配置、状态及其与本服务端口的绑定关系。

        Args:
            port: 待比对的目标代理端口，默认 8080。
            host: 待比对的目标代理主机地址，默认 127.0.0.1。

        Returns:
            包含 supported、system_proxy_enabled、proxy_server、is_pointing 的字典。
        """
        return system_proxy.get_proxy_status(expected_host=host, expected_port=port)

    @mcp.tool()
    def export_http_session(
        output_path: str,
        session_id: str | None = None,
        format: str = "har",
    ) -> dict[str, Any]:
        """将指定或最近一次抓包会话的全部流量与完整载荷导出为标准 HAR 1.2 归档文件。

        Args:
            output_path: 导出的目标 HAR 文件路径。
            session_id: 可选的目标会话 ID；未提供时自动定位最近一次抓包会话。
            format: 导出文件格式，默认 'har'。

        Returns:
            包含导出文件路径、格式、流条目数量与文件字节大小的结构化字典。
        """
        return har_exporter.export_session(
            output_path=output_path,
            session_id=session_id,
            format=format,
        )


def _register_process_tools(
    mcp: FastMCP,
    capture_manager: HttpCaptureManager,
    pcap_manager: PcapCaptureManager,
    lifecycle: LifecycleManager | None = None,
) -> None:
    """注册进程主动受管拉起、环境变量自动注入与双轨时空切片抓包工具集。"""

    @mcp.tool()
    def launch_and_inspect_process(
        command: list[str] | str,
        cwd: str | None = None,
        extra_env: dict[str, str] | None = None,
        inject_proxy: bool = True,
        inject_ca_cert: bool = True,
        capture_pcap: bool = False,
        pcap_interface: int | str = "loopback",
        wait_for_exit: bool = False,
        timeout_seconds: int = 30,
    ) -> dict[str, Any]:
        """主动拉起受管目标进程，原子级注入抓包代理与 CA 环境变量，并支持第 0 毫秒双轨抓包。

        解决短生命周期 CLI/脚本启动阶段漏包与非系统信任库（Node/Python/Go/Curl）证书错误痛点。

        Args:
            command: 待执行的命令行参数列表（如 ['python', 'script.py']）或命令行字符串。
            cwd: 进程执行的工作目录绝对路径；为空时继承当前工作目录。
            extra_env: 可选的自定义补充环境变量字典。
            inject_proxy: 是否自动将 HTTP_PROXY 等代理变量注入到子进程，默认 True。
            inject_ca_cert: 是否自动注入 Node/Python 等运行时的 CA 证书环境变量，默认 True。
            capture_pcap: 是否同步联动网络层 PCAP 抓包进行双轨捕获，默认 False。
            pcap_interface: 当 capture_pcap=True 时的网卡选择，默认 'loopback'。
            wait_for_exit: 是否同步等待目标进程执行退出并收集 stdout/stderr，默认 False。
            timeout_seconds: 当 wait_for_exit=True 时等待进程退出的最大超时秒数，默认 30。

        Returns:
            包含 status、pid、exit_code、stdout、stderr 与抓包信息的字典。
        """
        # 1. 解析命令参数
        if isinstance(command, str):
            cmd_args = (
                shlex.split(command, posix=False) if os.name == "nt" else shlex.split(command)
            )
        else:
            cmd_args = list(command)

        if not cmd_args:
            raise ValueError("启动命令行 command 不能为空")

        # 2. 组装环境变量
        env = os.environ.copy()
        injected_proxy_port: int | None = None
        if inject_proxy:
            proxy_port = getattr(capture_manager, "_port", None) or 8080
            injected_proxy_port = proxy_port
            proxy_url = f"http://127.0.0.1:{proxy_port}"
            for k in (
                "HTTP_PROXY",
                "HTTPS_PROXY",
                "ALL_PROXY",
                "http_proxy",
                "https_proxy",
                "all_proxy",
            ):
                env[k] = proxy_url

        if inject_ca_cert:
            ca_envs = get_ca_env_vars()
            env.update(ca_envs)

        if extra_env:
            env.update(extra_env)

        # 3. 启动受管子进程
        proc = subprocess.Popen(
            cmd_args,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE if wait_for_exit else None,
            stderr=subprocess.PIPE if wait_for_exit else None,
            text=True if wait_for_exit else False,
        )
        pid = proc.pid
        if lifecycle is not None:
            lifecycle.register(lambda: proc.kill() if proc.poll() is None else None)

        # 4. 联动网卡抓包 (第 0 毫秒绑定 PID 树)
        pcap_start_res = None
        if capture_pcap:
            try:
                pcap_start_res = pcap_manager.start_capture(
                    interface=pcap_interface,
                    target_pids=[pid],
                    include_child_processes=True,
                )
            except Exception as exc:
                logger.warning("受管进程联动启动 PCAP 抓包失败: %s", exc)
                pcap_start_res = {"error": str(exc)}

        # 5. 等待退出或立即返回
        if not wait_for_exit:
            return {
                "status": "running",
                "pid": pid,
                "command": cmd_args,
                "proxy_port_injected": injected_proxy_port,
                "ca_injected": inject_ca_cert,
                "pcap_capture": pcap_start_res,
            }

        timed_out = False
        try:
            out, err = proc.communicate(timeout=timeout_seconds)
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            proc.kill()
            out, err = proc.communicate()
            exit_code = -1
            timed_out = True

        pcap_stop_res = None
        if capture_pcap and getattr(pcap_manager, "_current_session", None):
            try:
                pcap_stop_res = pcap_manager.stop_capture()
            except Exception as exc:
                logger.warning("受管进程退出停止 PCAP 抓包异常: %s", exc)
                pcap_stop_res = {"error": str(exc)}

        return {
            "status": "completed",
            "pid": pid,
            "exit_code": exit_code,
            "timed_out": timed_out,
            "stdout": (out or "")[:4096],
            "stderr": (err or "")[:4096],
            "proxy_port_injected": injected_proxy_port,
            "ca_injected": inject_ca_cert,
            "pcap_capture": pcap_stop_res or pcap_start_res,
        }


def create_mcp_server(
    config: ServerConfig,
    storage: StorageBus | None = None,
    capture_manager: HttpCaptureManager | None = None,
    replay_engine: FlowReplayEngine | None = None,
    pcap_manager: PcapCaptureManager | None = None,
    diagnostics: NetworkDiagnostics | None = None,
    system_proxy: SystemProxyManager | None = None,
    har_exporter: HarExporter | None = None,
    lifecycle: LifecycleManager | None = None,
) -> FastMCP:
    """构建并初始化 FastMCP 服务实例、共享 SQLite WAL 数据总线与 MCP 工具集。

    Args:
        config: 服务端运行配置对象。
        storage: 可选的外部 StorageBus 实例；未传入时根据 config 自动构建并初始化。
        capture_manager: 可选的外部 HttpCaptureManager 实例。
        replay_engine: 可选的外部 FlowReplayEngine 实例。
        pcap_manager: 可选的外部 PcapCaptureManager 实例。
        diagnostics: 可选的外部 NetworkDiagnostics 实例。
        system_proxy: 可选的外部 SystemProxyManager 实例。
        har_exporter: 可选的外部 HarExporter 实例。
        lifecycle: 可选的生命周期管理器；传入时自动注册子进程与代理状态停止钩子。

    Returns:
        完成全部 25 个工具注册的 FastMCP 服务对象。
    """
    # 1. 初始化共享 SQLite WAL 数据总线与核心业务管理器
    bus = storage or StorageBus.from_config(config)
    bus.initialize()
    manager = capture_manager or HttpCaptureManager(storage=bus)
    replayer = replay_engine or FlowReplayEngine(storage=bus)
    pcap_mgr = pcap_manager or PcapCaptureManager(tshark_path=config.tshark_path)
    pcap_mgr.set_proxy_port_resolver(lambda: getattr(manager, "_port", None) or 8080)
    diag_engine = diagnostics or NetworkDiagnostics(storage=bus, pcap_manager=pcap_mgr)
    sys_proxy = system_proxy or SystemProxyManager()
    har_exp = har_exporter or HarExporter(storage=bus)

    if lifecycle is not None:
        lifecycle.register(lambda: None if manager.stop_capture() else None)
        lifecycle.register(lambda: None if pcap_mgr.stop_capture() else None)
        lifecycle.register(lambda: sys_proxy.restore_initial_state())

    # 2. 创建 FastMCP 主控实例并注册各领域工具集 (25 个 Tools)
    mcp = FastMCP(
        name=SERVER_NAME,
        instructions=SERVER_INSTRUCTIONS,
        host=config.host,
        port=config.port,
        log_level=config.log_level,
    )
    _register_http_tools(
        mcp=mcp,
        storage=bus,
        manager=manager,
        system_proxy=sys_proxy,
        har_exporter=har_exp,
    )
    _register_manipulation_tools(mcp=mcp, storage=bus, replay_engine=replayer)
    _register_pcap_tools(mcp=mcp, pcap_manager=pcap_mgr)
    _register_diagnostic_tools(mcp=mcp, diagnostics=diag_engine)
    _register_ops_tools(mcp=mcp, system_proxy=sys_proxy, har_exporter=har_exp)
    _register_process_tools(
        mcp=mcp,
        capture_manager=manager,
        pcap_manager=pcap_mgr,
        lifecycle=lifecycle,
    )
    return mcp
