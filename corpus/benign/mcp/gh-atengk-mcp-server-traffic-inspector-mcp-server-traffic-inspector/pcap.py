"""网络层 (L3/L4) 网卡枚举、安全熔断实时抓包 (PcapCapture) 与离线协议深度分析模块。

@author Ateng
@since 2026-10-13
"""

from __future__ import annotations

import gzip
import ipaddress
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
import zlib
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from mcp_server_traffic_inspector.capture_manager import WorkerProcessProtocol
from mcp_server_traffic_inspector.config import LOGGER_NAME
from mcp_server_traffic_inspector.doctor import resolve_tshark_path
from mcp_server_traffic_inspector.pcap_slicer import (
    CaptureSidecar,
    build_slice_display_filter,
    slice_pcap_file,
)
from mcp_server_traffic_inspector.process_tracker import (
    ProcessFamilyTracker,
    ProcessInfo,
    SocketEntry,
)
from mcp_server_traffic_inspector.storage import (
    DEFAULT_PREVIEW_CHARS,
    _decode_preview,
    _is_binary_payload,
)

logger = logging.getLogger(LOGGER_NAME)

KNOWN_PROTOCOLS = (
    "TCP",
    "UDP",
    "DNS",
    "TLS",
    "HTTP",
    "HTTPS",
    "ICMP",
    "ARP",
    "DHCP",
    "SSH",
    "QUIC",
    "FTP",
    "SMTP",
)


def parse_interface_list(tshark_output: str) -> list[dict[str, Any]]:
    """解析 tshark -D 标准输出为结构化网卡列表。

    Args:
        tshark_output: tshark -D 命令输出的纯文本内容。

    Returns:
        网卡字典列表；无匹配时返回空列表 []。
    """
    if not tshark_output or not tshark_output.strip():
        return []

    interfaces: list[dict[str, Any]] = []
    line_pattern = re.compile(r"^(\d+)\.\s+([^\s(]+(?:\s+[^\s(]+)*)(?:\s+\((.*)\))?$")

    for raw_line in tshark_output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = line_pattern.match(line)
        if match:
            idx_str, name, desc = match.groups()
            friendly = desc.strip() if desc else name.strip()
            interfaces.append(
                {
                    "index": int(idx_str),
                    "name": name.strip(),
                    "description": desc.strip() if desc else name.strip(),
                    "friendly_name": friendly,
                }
            )

    return interfaces


def parse_tshark_fields_output(
    tsv_lines: Sequence[str],
    file_path: str,
    total_packets: int | None = None,
) -> dict[str, Any]:
    """解析 tshark -T fields 报文提取字段为聚合网络指标。

    提取协议分布、TCP 重传率、RTT 往返时延（极值与均值）及 DNS 解析指标。

    Args:
        tsv_lines: 制表符分隔的 tshark 提取字段文本行序列。
        file_path: 目标 PCAP 文件路径。
        total_packets: 可选的文件内总数据包数；为 None 时以 tsv_lines 行数计量。

    Returns:
        包含协议占比、TCP 质量与 DNS 统计的结构化字典。
    """
    proto_counts: dict[str, int] = {}
    total_tcp = 0
    retrans_tcp = 0
    rtt_list_ms: list[float] = []

    dns_queries = 0
    dns_responses = 0
    dns_failures = 0
    dns_durations_ms: list[float] = []

    analyzed_count = 0

    for raw_line in tsv_lines:
        line = raw_line.strip()
        if not line:
            continue
        analyzed_count += 1
        cols = line.split("\t")
        while len(cols) < 7:
            cols.append("")

        _frame_num, proto_str, retrans_str, rtt_str, dns_resp_str, dns_rcode_str, dns_time_str = (
            cols[:7]
        )

        # 1. 统计协议分布
        proto_tokens = [t.upper() for t in proto_str.split(":") if t]
        matched_protos = set()
        for token in proto_tokens:
            for known in KNOWN_PROTOCOLS:
                if known in token:
                    matched_protos.add(known)
        for p in matched_protos:
            proto_counts[p] = proto_counts.get(p, 0) + 1

        # 2. 统计 TCP 重传与 ACK RTT 时延
        if "TCP" in matched_protos or "tcp" in proto_str.lower():
            total_tcp += 1
            if retrans_str and retrans_str.strip() == "1":
                retrans_tcp += 1
            if rtt_str and rtt_str.strip():
                try:
                    rtt_sec = float(rtt_str.strip().split(",")[0])
                    if rtt_sec >= 0.0:
                        rtt_list_ms.append(round(rtt_sec * 1000.0, 2))
                except ValueError:
                    pass

        # 3. 统计 DNS 请求、响应、异常状态码及响应耗时
        if "DNS" in matched_protos or "dns" in proto_str.lower():
            if dns_resp_str and dns_resp_str.strip() == "1":
                dns_responses += 1
                if dns_rcode_str and dns_rcode_str.strip():
                    try:
                        rcode = int(dns_rcode_str.strip().split(",")[0])
                        if rcode != 0:
                            dns_failures += 1
                    except ValueError:
                        pass
                if dns_time_str and dns_time_str.strip():
                    try:
                        d_time = float(dns_time_str.strip().split(",")[0])
                        if d_time >= 0.0:
                            dns_durations_ms.append(round(d_time * 1000.0, 2))
                    except ValueError:
                        pass
            elif dns_resp_str and dns_resp_str.strip() == "0":
                dns_queries += 1

    packet_total = total_packets if total_packets is not None else analyzed_count
    retrans_rate = round((retrans_tcp / total_tcp) * 100.0, 2) if total_tcp > 0 else 0.0

    rtt_stats: dict[str, float | None] = {
        "min": min(rtt_list_ms) if rtt_list_ms else None,
        "max": max(rtt_list_ms) if rtt_list_ms else None,
        "avg": round(sum(rtt_list_ms) / len(rtt_list_ms), 2) if rtt_list_ms else None,
    }

    avg_dns_ms = (
        round(sum(dns_durations_ms) / len(dns_durations_ms), 2) if dns_durations_ms else None
    )

    return {
        "file_path": file_path,
        "total_packets": packet_total,
        "analyzed_packets": analyzed_count,
        "protocol_distribution": dict(
            sorted(proto_counts.items(), key=lambda x: x[1], reverse=True)
        ),
        "tcp_analysis": {
            "total_tcp_packets": total_tcp,
            "retransmission_packets": retrans_tcp,
            "retransmission_rate_pct": retrans_rate,
            "rtt_ms": rtt_stats,
        },
        "dns_analysis": {
            "query_count": dns_queries,
            "response_count": dns_responses,
            "failed_count": dns_failures,
            "avg_duration_ms": avg_dns_ms,
        },
    }


def parse_tcp_streams_output(
    tsv_lines: Sequence[str],
    limit: int = 50,
) -> list[dict[str, Any]]:
    """解析 tshark 导出的 TCP 流报文行，聚合为 TCP 会话流摘要列表。

    Args:
        tsv_lines: 制表符分隔的 tshark 提取字段文本行。
        limit: 最大返回流条数，默认 50。

    Returns:
        按 stream_id 聚合的 TCP 流列表；无匹配时返回空列表 []。
    """
    streams: dict[int, dict[str, Any]] = {}

    for raw_line in tsv_lines:
        line = raw_line.strip()
        if not line:
            continue
        cols = line.split("\t")
        while len(cols) < 11:
            cols.append("")

        (
            stream_str,
            ip_src,
            ip_dst,
            ipv6_src,
            ipv6_dst,
            tcp_srcport,
            tcp_dstport,
            proto_col,
            tcp_len_str,
            tls_sni,
            http_host,
        ) = cols[:11]

        if not stream_str.strip():
            continue
        try:
            stream_id = int(stream_str.strip())
        except ValueError:
            continue

        src_ip = ip_src.strip() or ipv6_src.strip()
        dst_ip = ip_dst.strip() or ipv6_dst.strip()
        src_port = int(tcp_srcport.strip()) if tcp_srcport.strip().isdigit() else 0
        dst_port = int(tcp_dstport.strip()) if tcp_dstport.strip().isdigit() else 0
        tcp_len = int(tcp_len_str.strip()) if tcp_len_str.strip().isdigit() else 0

        sni = tls_sni.strip() or http_host.strip() or None

        if stream_id not in streams:
            streams[stream_id] = {
                "stream_id": stream_id,
                "client": f"{src_ip}:{src_port}",
                "server": f"{dst_ip}:{dst_port}",
                "client_ip": src_ip,
                "client_port": src_port,
                "server_ip": dst_ip,
                "server_port": dst_port,
                "packet_count": 0,
                "payload_bytes": 0,
                "protocol": proto_col.strip() or "TCP",
                "sni_or_host": sni,
            }

        curr = streams[stream_id]
        curr["packet_count"] += 1
        curr["payload_bytes"] += tcp_len
        if sni and not curr["sni_or_host"]:
            curr["sni_or_host"] = sni
        p = proto_col.strip()
        if p and p.upper() not in ("TCP", "IP", "IPV6") and curr["protocol"] == "TCP":
            curr["protocol"] = p

    sorted_streams = sorted(streams.values(), key=lambda s: s["stream_id"])
    return sorted_streams[: max(1, int(limit))]


def _extract_tls_sni(data: bytes) -> str | None:
    """从 TLS Client Hello 握手数据中提取 SNI (Server Name Indication) 域名。"""
    try:
        if len(data) < 44 or data[0] != 0x16 or data[5] != 0x01:
            return None
        pos = 43
        session_id_len = data[pos]
        pos += 1 + session_id_len
        if pos + 2 > len(data):
            return None
        cipher_len = int.from_bytes(data[pos : pos + 2], "big")
        pos += 2 + cipher_len
        if pos + 1 > len(data):
            return None
        comp_len = data[pos]
        pos += 1 + comp_len
        if pos + 2 > len(data):
            return None
        ext_total_len = int.from_bytes(data[pos : pos + 2], "big")
        pos += 2
        ext_end = min(pos + ext_total_len, len(data))
        while pos + 4 <= ext_end:
            ext_type = int.from_bytes(data[pos : pos + 2], "big")
            ext_len = int.from_bytes(data[pos + 2 : pos + 4], "big")
            pos += 4
            if ext_type == 0:  # server_name
                sub_pos = pos
                if sub_pos + 2 <= ext_end:
                    sub_pos += 2  # skip server_name_list_len
                    while sub_pos + 3 <= pos + ext_len and sub_pos + 3 <= ext_end:
                        name_type = data[sub_pos]
                        name_len = int.from_bytes(data[sub_pos + 1 : sub_pos + 3], "big")
                        sub_pos += 3
                        if name_type == 0 and sub_pos + name_len <= ext_end:
                            return data[sub_pos : sub_pos + name_len].decode(
                                "utf-8", errors="replace"
                            )
                        sub_pos += name_len
            pos += ext_len
    except Exception:
        return None
    return None


def _heuristic_dissect_payload(data: bytes) -> dict[str, Any]:
    """对原始二进制 payload 执行启发式协议推断与轻量解构。"""
    res: dict[str, Any] = {}
    if not data:
        return res

    # 1. 协议特征识别 (TLS / HTTP / WebSocket)
    if data.startswith(b"\x16\x03"):
        res["protocol_hint"] = "TLS"
        sni = _extract_tls_sni(data)
        if sni:
            res["tls_sni"] = sni
    elif any(
        data.startswith(m)
        for m in (
            b"GET ",
            b"POST ",
            b"PUT ",
            b"DELETE ",
            b"PATCH ",
            b"HEAD ",
            b"OPTIONS ",
            b"CONNECT ",
            b"HTTP/1.",
            b"HTTP/2.",
        )
    ):
        res["protocol_hint"] = "HTTP"
        if b"Upgrade: websocket" in data or b"upgrade: websocket" in data:
            res["protocol_hint"] = "WebSocket Handshake"
    elif data[0] in (0x81, 0x82, 0x88, 0x89, 0x8A) and len(data) >= 2:
        # WebSocket 常见帧头特征 (FIN + Text/Binary/Close/Ping/Pong)
        res["protocol_hint"] = "WebSocket Frame"

    # 2. 压缩流解构尝试 (Gzip / Zlib)
    try:
        decomp = None
        if data.startswith(b"\x1f\x8b"):
            decomp = gzip.decompress(data[:65536])
        elif len(data) >= 2 and data[:2] in (b"\x78\x9c", b"\x78\x01", b"\x78\xda"):
            decomp = zlib.decompress(data[:65536])
        if decomp:
            res["decompressed_preview"] = decomp[:300].decode("utf-8", errors="replace")
    except Exception:
        pass

    # 3. 提取可打印 ASCII 字符串片段 (类似 strings 命令)
    ascii_strings = [
        s.decode("ascii", errors="ignore") for s in re.findall(rb"[\x20-\x7e]{4,}", data[:2048])
    ]
    if ascii_strings:
        res["heuristic_strings"] = ascii_strings[:10]

    return res


def parse_tcp_stream_turns_output(
    tsv_lines: Sequence[str],
    stream_id: int,
    format: str = "turns",
) -> dict[str, Any]:
    """解析指定 TCP 流的 payload 字段行，按方向聚合为交互回合 (Turns) 或原始报文流。

    Args:
        tsv_lines: 制表符分隔的 tshark 提取字段文本行。
        stream_id: 目标 TCP 流 ID。
        format: 格式化方式（'turns'、'raw'、'hex'），默认 'turns'。

    Returns:
        包含流端点、回合统计与按交互时序聚合数据的字典。
    """
    client_endpoint: tuple[str, int] | None = None
    server_endpoint: tuple[str, int] | None = None
    raw_packets: list[dict[str, Any]] = []

    for raw_line in tsv_lines:
        line = raw_line.strip()
        if not line:
            continue
        cols = line.split("\t")
        while len(cols) < 9:
            cols.append("")

        (
            frame_num_str,
            time_epoch_str,
            ip_src,
            ip_dst,
            ipv6_src,
            ipv6_dst,
            tcp_srcport,
            tcp_dstport,
            payload_hex_raw,
        ) = cols[:9]

        payload_clean = payload_hex_raw.replace(":", "").replace(" ", "").strip()
        if not payload_clean:
            continue
        try:
            payload_bytes = bytes.fromhex(payload_clean)
        except ValueError:
            continue

        src_ip = ip_src.strip() or ipv6_src.strip()
        dst_ip = ip_dst.strip() or ipv6_dst.strip()
        src_port = int(tcp_srcport.strip()) if tcp_srcport.strip().isdigit() else 0
        dst_port = int(tcp_dstport.strip()) if tcp_dstport.strip().isdigit() else 0
        epoch_time = float(time_epoch_str.strip()) if time_epoch_str.strip() else 0.0
        frame_num = int(frame_num_str.strip()) if frame_num_str.strip().isdigit() else 0

        if client_endpoint is None:
            client_endpoint = (src_ip, src_port)
            server_endpoint = (dst_ip, dst_port)

        direction = (
            "client_to_server" if (src_ip, src_port) == client_endpoint else "server_to_client"
        )

        raw_packets.append(
            {
                "frame_number": frame_num,
                "timestamp": epoch_time,
                "direction": direction,
                "payload_bytes": payload_bytes,
            }
        )

    client_str = f"{client_endpoint[0]}:{client_endpoint[1]}" if client_endpoint else "unknown"
    server_str = f"{server_endpoint[0]}:{server_endpoint[1]}" if server_endpoint else "unknown"

    if not raw_packets:
        return {
            "stream_id": stream_id,
            "client": client_str,
            "server": server_str,
            "total_turns": 0,
            "total_bytes": 0,
            "format": format,
            "turns": [],
        }

    turns: list[dict[str, Any]] = []
    current_direction = raw_packets[0]["direction"]
    current_bytes = bytearray()
    turn_packet_count = 0
    turn_start_time = raw_packets[0]["timestamp"]
    turn_end_time = raw_packets[0]["timestamp"]
    turn_index = 1
    total_stream_bytes = 0

    def _flush_turn(
        idx: int,
        direction: str,
        b_data: bytes,
        pkt_cnt: int,
        t_start: float,
        t_end: float,
    ) -> dict[str, Any]:
        is_binary = _is_binary_payload(b_data, None)
        text_payload, truncated = _decode_preview(b_data, is_binary, DEFAULT_PREVIEW_CHARS)
        turn_obj: dict[str, Any] = {
            "turn_index": idx,
            "direction": direction,
            "packet_count": pkt_cnt,
            "byte_count": len(b_data),
            "start_time": t_start,
            "end_time": t_end,
            "is_binary": is_binary,
            "payload_preview": text_payload,
            "truncated": truncated,
        }
        heuristic = _heuristic_dissect_payload(b_data)
        if heuristic:
            turn_obj["heuristic"] = heuristic
        if format == "hex":
            turn_obj["payload_hex"] = b_data.hex()
        elif format == "raw" and not is_binary:
            turn_obj["payload_raw"] = b_data.decode("utf-8", errors="replace")
        return turn_obj

    for pkt in raw_packets:
        p_dir = pkt["direction"]
        p_bytes = pkt["payload_bytes"]
        p_time = pkt["timestamp"]
        total_stream_bytes += len(p_bytes)

        if p_dir == current_direction:
            current_bytes.extend(p_bytes)
            turn_packet_count += 1
            turn_end_time = p_time
        else:
            turns.append(
                _flush_turn(
                    turn_index,
                    current_direction,
                    bytes(current_bytes),
                    turn_packet_count,
                    turn_start_time,
                    turn_end_time,
                )
            )
            turn_index += 1
            current_direction = p_dir
            current_bytes = bytearray(p_bytes)
            turn_packet_count = 1
            turn_start_time = p_time
            turn_end_time = p_time

    if current_bytes:
        turns.append(
            _flush_turn(
                turn_index,
                current_direction,
                bytes(current_bytes),
                turn_packet_count,
                turn_start_time,
                turn_end_time,
            )
        )

    return {
        "stream_id": stream_id,
        "client": client_str,
        "server": server_str,
        "total_turns": len(turns),
        "total_bytes": total_stream_bytes,
        "format": format,
        "turns": turns,
    }


def _default_spawner(cmd: list[str], env: dict[str, str]) -> WorkerProcessProtocol:
    return subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )


class PcapCaptureManager:
    """管理原始网络层报文捕获 (PcapCapture) 与离线 PCAP 协议分析。"""

    def __init__(
        self,
        tshark_path: str | None = None,
        command_runner: Callable[[list[str]], str] | None = None,
        process_spawner: Callable[[list[str], dict[str, str]], WorkerProcessProtocol] | None = None,
        default_output_dir: Path | None = None,
        snapshot_fetcher: Callable[[], list[ProcessInfo]] | None = None,
        socket_fetcher: Callable[[], list[SocketEntry]] | None = None,
    ) -> None:
        """初始化 PCAP 捕获与分析管理器。

        Args:
            tshark_path: 显式指定的 tshark 可执行文件路径。
            command_runner: 可选的同步命令执行器（供测试注入），默认调用 subprocess.run。
            process_spawner: 可选的子进程启动器函数（供测试注入），默认调用 subprocess.Popen。
            default_output_dir: 默认抓包产出文件保存目录，为 None 时使用系统临时目录。
            snapshot_fetcher: 可选的进程快照获取器函数（供测试注入）。
            socket_fetcher: 可选的活跃套接字获取器函数（供测试注入）。
        """
        self._explicit_path = tshark_path
        self._runner = command_runner or self._run_command_sync
        self._spawner = process_spawner or _default_spawner
        self._default_dir = (default_output_dir or Path(tempfile.gettempdir())).resolve()
        self._snapshot_fetcher = snapshot_fetcher
        self._socket_fetcher = socket_fetcher

        self._process: WorkerProcessProtocol | None = None
        self._active_output_file: str | None = None
        self._active_interface: int | str | None = None
        self._started_at: float | None = None

        # 进程感知抓包状态
        self._active_tracker: ProcessFamilyTracker | None = None
        self._is_process_capture: bool = False
        self._active_final_target: Path | None = None
        self._active_keep_raw: bool = False

        # 受管 HTTP 代理端口动态解析器
        self._proxy_port_resolver: Callable[[], int | None] | None = None

    def set_proxy_port_resolver(self, resolver: Callable[[], int | None]) -> None:
        """注册活跃 HTTP 抓包代理端口解析回调函数。"""
        self._proxy_port_resolver = resolver

    def _run_command_sync(self, cmd: list[str]) -> str:
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30.0,
                check=False,
            )
            return completed.stdout or ""
        except (OSError, subprocess.SubprocessError, UnicodeDecodeError) as exc:
            logger.warning("执行 tshark 命令失败 (%s): %s", cmd, exc)
            return ""

    def _resolve_binary(self) -> Path:
        resolved = resolve_tshark_path(self._explicit_path)
        if resolved is None:
            if self._runner != self._run_command_sync or self._spawner != _default_spawner:
                return Path(self._explicit_path or "tshark")
            raise RuntimeError(
                "未检测到 tshark 可执行文件，无法执行 PCAP 相关操作。"
                "请安装 Wireshark/tshark 或配置 --tshark-path。"
            )
        return resolved

    def list_interfaces(self) -> list[dict[str, Any]]:
        """枚举当前主机可用的网络抓包接口列表。

        Returns:
            包含接口索引、名称与描述的列表；未检测到 tshark 或无网卡时返回空列表 []。
        """
        try:
            tshark_bin = self._resolve_binary()
        except RuntimeError:
            return []

        cmd = [str(tshark_bin), "-D"]
        output = self._runner(cmd)
        return parse_interface_list(output)

    @staticmethod
    def _is_loopback_interface(item: dict[str, Any]) -> bool:
        name = str(item.get("name", "")).lower()
        desc = str(item.get("description", "")).lower()
        friendly = str(item.get("friendly_name", "")).lower()
        return (
            "loopback" in name
            or "loopback" in desc
            or "loopback" in friendly
            or name in ("lo", "lo0")
            or "npf_loopback" in name
        )

    def _normalize_interface(self, iface: int | str) -> str:
        """归一化单网卡标识符为 tshark 能够识别的接口名或索引。

        支持传入友好名称（如 'WLAN'）、数字索引（如 1）、'loopback' 别名或直接设备名。

        Args:
            iface: 网卡索引、名称或友好别名。

        Returns:
            可直接用于 tshark -i 的参数字符串。
        """
        if isinstance(iface, int):
            return str(iface)
        target = str(iface).strip()
        if not target or target.isdigit():
            return target or "1"

        try:
            available = self.list_interfaces()
            target_lower = target.lower()

            # 1. 语义别名支持：loopback / lo / 127.0.0.1
            if target_lower in ("loopback", "lo", "lo0", "npf_loopback", "127.0.0.1"):
                for item in available:
                    if self._is_loopback_interface(item):
                        return str(item.get("name") or item.get("index"))
                return r"\Device\NPF_Loopback" if sys.platform == "win32" else "lo"

            # 2. 普通名称/描述/friendly_name 模糊比对
            for item in available:
                name = str(item.get("name", "")).strip()
                desc = str(item.get("description", "")).strip()
                friendly = str(item.get("friendly_name", "")).strip()
                if target_lower in (name.lower(), desc.lower(), friendly.lower()):
                    return name or str(item.get("index", target))
        except Exception as exc:
            logger.debug("归一化网卡名称失败，回退至原始参数: %s", exc)

        return target

    def _resolve_interfaces(self, iface: int | str | Sequence[int | str]) -> list[str]:
        """解析并扩展网卡标识符为供 tshark -i 消费的网卡参数列表。

        支持单网卡、网卡列表、逗号分隔字符串、'loopback' 以及 'auto' 双轨自适应。
        """
        if isinstance(iface, (list, tuple)):
            res: list[str] = []
            for sub in iface:
                res.extend(self._resolve_interfaces(sub))
            return res or ["1"]

        if isinstance(iface, str) and "," in iface:
            parts = [p.strip() for p in iface.split(",") if p.strip()]
            return self._resolve_interfaces(parts)

        target_str = str(iface).strip().lower()
        if target_str == "auto":
            try:
                available = self.list_interfaces()
                if not available:
                    return ["1"]

                loopback_item: dict[str, Any] | None = None
                primary_physical: dict[str, Any] | None = None

                for item in available:
                    if self._is_loopback_interface(item):
                        if loopback_item is None:
                            loopback_item = item
                    else:
                        name_lower = str(item.get("name", "")).lower()
                        if "etwdump" not in name_lower and primary_physical is None:
                            primary_physical = item

                chosen: list[str] = []
                if primary_physical is not None:
                    chosen.append(
                        str(primary_physical.get("name") or primary_physical.get("index"))
                    )
                elif available:
                    chosen.append(str(available[0].get("name") or available[0].get("index")))

                if loopback_item is not None:
                    chosen.append(str(loopback_item.get("name") or loopback_item.get("index")))

                return chosen or ["1"]
            except Exception as exc:
                logger.debug("自动推导 auto 双轨网卡失败: %s", exc)
                return ["1"]

        return [self._normalize_interface(iface)]

    def start_capture(
        self,
        *,
        interface: int | str | Sequence[int | str] = 1,
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
        """在指定网卡启动带双重安全熔断阈值的原始报文捕获 (PcapCapture)。

        支持基于进程路径、进程名称或显式 PID 家族树追踪与后处理时空切片。

        Args:
            interface: 网卡索引、名称、'loopback'、'auto' 或网卡标识符列表，默认 1。
            output_path: 保存目标 .pcap 绝对路径；为空时自动生成于系统临时目录。
            bpf_filter: 可选的 BPF 抓包过滤表达式（如 'tcp port 80'）。
            max_packets: 最大抓包数熔断上限，默认 2000 包。
            duration_seconds: 最大抓包时长熔断上限，默认 60 秒。
            process_path: 可选的目标可执行文件绝对路径。
            process_name: 可选的目标进程名称通配符（如 'Weixin*.exe'）。
            target_pids: 可选的显式指定目标 PID 列表。
            include_child_processes: 是否递归追踪目标进程的所有派生子进程，默认 True。
            keep_raw_pcap: 是否保留全量中间抓包文件，默认 False（自动清理）。

        Returns:
            包含状态、网卡、已解析网卡列表、输出路径及过滤元数据的字典。
        """
        # 1. 若已有运行中的实时抓包子进程，先执行安全停止
        if self._process is not None and self._process.poll() is None:
            self.stop_capture()

        # 2. 校验并组装输出文件绝对路径
        tshark_bin = self._resolve_binary()
        if output_path and output_path.strip():
            target_path = Path(output_path.strip()).expanduser().resolve()
        else:
            ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_path = (
                self._default_dir / f"pcap_capture_{ts_str}_{uuid4().hex[:6]}.pcap"
            ).resolve()

        target_path.parent.mkdir(parents=True, exist_ok=True)

        is_process_mode = bool(process_path or process_name or target_pids)
        self._is_process_capture = is_process_mode
        self._active_final_target = target_path
        self._active_keep_raw = keep_raw_pcap

        # 在进程抓包模式下，底层 tshark 捕获到中间原始文件
        capture_file = (
            target_path.parent / f"raw_{target_path.name}" if is_process_mode else target_path
        )

        if is_process_mode:
            self._active_tracker = ProcessFamilyTracker(
                process_path=process_path,
                process_name=process_name,
                target_pids=target_pids,
                include_child_processes=include_child_processes,
                poll_interval=0.1,
                snapshot_fetcher=self._snapshot_fetcher,
                socket_fetcher=self._socket_fetcher,
            )
            self._active_tracker.start()

        # 3. 构建并启动实施双重安全熔断的 tshark 子进程
        resolved_ifaces = self._resolve_interfaces(interface)
        cmd = [str(tshark_bin)]
        for single_iface in resolved_ifaces:
            cmd.extend(["-i", single_iface])
        cmd.extend(
            [
                "-w",
                str(capture_file),
                "-c",
                str(max(1, int(max_packets))),
                "-a",
                f"duration:{max(1, int(duration_seconds))}",
                "-q",
            ]
        )
        if bpf_filter and bpf_filter.strip():
            cmd.extend(["-f", bpf_filter.strip()])

        self._process = self._spawner(cmd, dict(os.environ))
        self._active_output_file = str(capture_file)
        self._active_interface = interface
        self._started_at = time.monotonic()

        result: dict[str, Any] = {
            "status": "capturing",
            "interface": interface,
            "resolved_interfaces": resolved_ifaces,
            "output_file": str(target_path),
            "limits": {
                "max_packets": int(max_packets),
                "duration_seconds": int(duration_seconds),
            },
        }
        if is_process_mode:
            result["process_filter"] = {
                "process_path": process_path,
                "process_name": process_name,
                "target_pids": target_pids,
                "include_child_processes": include_child_processes,
            }

        return result

    def stop_capture(self) -> dict[str, Any]:
        """优雅停止当前正在运行的实时 PCAP 抓包子进程，并执行切片与元数据落盘。

        Returns:
            包含 status ("stopped")、pcap_file 路径、packet_count 及拓扑元数据的字典。
        """
        # 1. 安全终止 tshark 子进程
        proc = self._process
        self._process = None
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=3.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
            except Exception as exc:
                logger.warning("终止 tshark 实时抓包子进程异常: %s", exc)

        raw_capture_file = self._active_output_file
        final_target = self._active_final_target
        is_process_mode = self._is_process_capture
        tracker = self._active_tracker
        keep_raw = self._active_keep_raw

        self._active_output_file = None
        self._active_interface = None
        self._started_at = None
        self._active_tracker = None
        self._is_process_capture = False
        self._active_final_target = None
        self._active_keep_raw = False

        process_summary: dict[str, Any] | None = None
        server_topology: list[dict[str, Any]] = []

        # 2. 若启用了进程感知模式，执行时空切片并保存 Sidecar
        if is_process_mode and tracker is not None and final_target is not None:
            family, timeline = tracker.stop()
            process_summary = family.to_dict()
            server_topology = timeline.export_server_topology(family.all_pids)

            ports = timeline.get_active_ports(family.all_pids)
            display_filter = build_slice_display_filter(ports)

            if raw_capture_file and Path(raw_capture_file).is_file():
                try:
                    tshark_bin = self._resolve_binary()
                    slice_pcap_file(
                        raw_pcap_path=raw_capture_file,
                        target_pcap_path=final_target,
                        display_filter=display_filter,
                        tshark_bin=tshark_bin,
                        runner=self._runner,
                        keep_raw_pcap=keep_raw,
                    )
                except Exception as exc:
                    logger.warning("执行 PCAP 时空切片异常: %s", exc)

            pcap_file = str(final_target)
        else:
            pcap_file = raw_capture_file

        # 3. 统计最终切片文件的报文数量
        packet_count = 0
        if pcap_file and Path(pcap_file).is_file():
            try:
                tshark_bin = self._resolve_binary()
                count_out = self._runner(
                    [str(tshark_bin), "-r", str(pcap_file), "-T", "fields", "-e", "frame.number"]
                )
                packet_count = len([line for line in count_out.splitlines() if line.strip()])
            except Exception as exc:
                logger.debug("统计 PCAP 文件包数失败: %s", exc)

        # 4. 双轨抓包模式感知：检测流量是否被重定向至本地回环接口并区分协议类型
        redirection_notice: dict[str, Any] | None = None
        if is_process_mode and packet_count == 0 and server_topology:
            active_proxy_port = (
                self._proxy_port_resolver() if self._proxy_port_resolver else None
            ) or 8080

            def _is_loopback_ip(ip: str | None) -> bool:
                if not ip:
                    return False
                target = ip.strip().lower()
                if target in ("127.0.0.1", "::1", "localhost"):
                    return True
                if target.startswith("127."):
                    return True
                try:
                    return ipaddress.ip_address(target).is_loopback
                except ValueError:
                    return False

            loopback_items = [
                item for item in server_topology if _is_loopback_ip(item.get("server_ip"))
            ]
            external_items = [
                item for item in server_topology if not _is_loopback_ip(item.get("server_ip"))
            ]
            loopback_hits = sum(item.get("hit_count", 0) for item in loopback_items)
            external_hits = sum(item.get("hit_count", 0) for item in external_items)

            if loopback_hits > 0 and external_hits == 0:
                all_loopback_ports = sorted(
                    {int(item["port"]) for item in loopback_items if item.get("port")}
                )
                proxy_ports = [p for p in all_loopback_ports if p == active_proxy_port]
                raw_socket_ports = [p for p in all_loopback_ports if p != active_proxy_port]
                has_raw_socket = len(raw_socket_ports) > 0
                is_redirected_to_proxy = len(proxy_ports) > 0 and not has_raw_socket

                if has_raw_socket:
                    msg = (
                        f"检测到目标进程存在非 HTTP 原生套接字连接 (端口: {raw_socket_ports})，"
                        f"未流经本地 HTTP 代理 (端口: {active_proxy_port})。原生 TCP 载荷未被捕获。"
                        "建议使用 interface='loopback' 或 interface='auto' 进行底层重组。"
                    )
                else:
                    msg = (
                        f"检测到目标进程活跃连接已被本地代理端口 ({proxy_ports}) 接管，"
                        "未流经物理网卡。全量明文数据已完整保存在 HTTP 抓包会话与 HAR 归档中。"
                    )

                redirection_notice = {
                    "is_redirected_to_proxy": is_redirected_to_proxy,
                    "has_raw_socket": has_raw_socket,
                    "proxy_ports": proxy_ports,
                    "raw_socket_ports": raw_socket_ports,
                    "loopback_proxy_ports": proxy_ports,
                    "loopback_hits": loopback_hits,
                    "message": msg,
                }

        # 5. 持久化伴随元数据 (CaptureSidecar)
        if is_process_mode and tracker is not None and final_target is not None:
            extra_meta: dict[str, Any] = {}
            if redirection_notice is not None:
                extra_meta["redirection_notice"] = redirection_notice
            CaptureSidecar.save(
                pcap_path=final_target,
                process_family=family,
                timeline=timeline,
                extra=extra_meta,
            )

        res: dict[str, Any] = {
            "status": "stopped",
            "pcap_file": pcap_file,
            "packet_count": packet_count,
        }
        if is_process_mode:
            res["process_summary"] = process_summary
            res["server_topology"] = server_topology
            if redirection_notice is not None:
                res["redirection_notice"] = redirection_notice

        return res

    def analyze_pcap(
        self,
        file_path: str,
        display_filter: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """对指定的离线 .pcap / .pcapng 文件执行深度协议、TCP 重传与 DNS 质量分析。

        Args:
            file_path: 目标 PCAP 本地文件路径。
            display_filter: 可选的 Wireshark Display Filter 过滤表达式（如 'tcp' 或 'dns'）。
            limit: 分析的最大报文上限数，默认 50。

        Returns:
            包含协议分布、TCP 质量指标与 DNS 统计的结构化字典。

        Raises:
            ValueError: 当指定文件不存在时抛出。
            RuntimeError: 当 tshark 引擎不可用时抛出。
        """
        # 1. 验证目标文件有效性与 tshark 可用性
        path_obj = Path(file_path.strip()).expanduser().resolve()
        if not path_obj.is_file():
            raise ValueError(f"PCAP 文件不存在: {file_path}")

        tshark_bin = self._resolve_binary()

        # 2. 执行 tshark -T fields 字段提取
        cmd = [
            str(tshark_bin),
            "-r",
            str(path_obj),
            "-c",
            str(max(1, int(limit))),
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "frame.protocols",
            "-e",
            "tcp.analysis.retransmission",
            "-e",
            "tcp.analysis.ack_rtt",
            "-e",
            "dns.flags.response",
            "-e",
            "dns.flags.rcode",
            "-e",
            "dns.time",
        ]
        if display_filter and display_filter.strip():
            cmd.extend(["-Y", display_filter.strip()])

        output = self._runner(cmd)
        tsv_lines = [line for line in output.splitlines() if line.strip()]

        # 3. 汇总聚合指标
        analysis = parse_tshark_fields_output(
            tsv_lines=tsv_lines,
            file_path=str(path_obj),
            total_packets=len(tsv_lines),
        )

        # 4. 若存在同名 .pcap.meta.json 伴随元数据，自动挂载多服务器拓扑与进程画像
        sidecar_meta = CaptureSidecar.load(path_obj)
        if sidecar_meta:
            analysis["process_summary"] = sidecar_meta.get("process_family")
            analysis["server_topology"] = sidecar_meta.get("server_topology", [])

        return analysis

    def list_tcp_streams(
        self,
        file_path: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """从指定的离线 PCAP 文件中提取并枚举所有 TCP 会话流及其端点、包数与载荷大小。

        Args:
            file_path: 目标 PCAP 本地文件绝对或相对路径。
            limit: 最大返回流条数，默认 50。

        Returns:
            按 stream_id 升序排列的 TCP 流列表；无匹配时返回空列表 []。

        Raises:
            ValueError: 当指定文件不存在时抛出。
            RuntimeError: 当 tshark 引擎不可用时抛出。
        """
        path_obj = Path(file_path.strip()).expanduser().resolve()
        if not path_obj.is_file():
            raise ValueError(f"PCAP 文件不存在: {file_path}")

        tshark_bin = self._resolve_binary()
        cmd = [
            str(tshark_bin),
            "-r",
            str(path_obj),
            "-Y",
            "tcp",
            "-T",
            "fields",
            "-e",
            "tcp.stream",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
            "-e",
            "ipv6.src",
            "-e",
            "ipv6.dst",
            "-e",
            "tcp.srcport",
            "-e",
            "tcp.dstport",
            "-e",
            "_ws.col.Protocol",
            "-e",
            "tcp.len",
            "-e",
            "tls.handshake.extensions_server_name",
            "-e",
            "http.host",
        ]
        output = self._runner(cmd)
        tsv_lines = [line for line in output.splitlines() if line.strip()]
        return parse_tcp_streams_output(tsv_lines, limit=limit)

    def follow_tcp_stream(
        self,
        file_path: str,
        stream_id: int,
        format: str = "turns",
    ) -> dict[str, Any]:
        """重组并跟踪指定 TCP 流的数据交互，按客户端与服务端方向聚合为回合 (Turns)。

        Args:
            file_path: 目标 PCAP 本地文件绝对或相对路径。
            stream_id: 待跟踪的 TCP 流 ID（如 0, 1）。
            format: 数据组织格式，支持 'turns'（默认回合制）、'raw' 与 'hex'。

        Returns:
            包含客户端/服务端端点、回合统计与时序报文数据的结构化字典。

        Raises:
            ValueError: 当指定文件不存在时抛出。
            RuntimeError: 当 tshark 引擎不可用时抛出。
        """
        path_obj = Path(file_path.strip()).expanduser().resolve()
        if not path_obj.is_file():
            raise ValueError(f"PCAP 文件不存在: {file_path}")

        tshark_bin = self._resolve_binary()
        cmd = [
            str(tshark_bin),
            "-r",
            str(path_obj),
            "-Y",
            f"tcp.stream eq {int(stream_id)} and tcp.len > 0",
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "frame.time_epoch",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
            "-e",
            "ipv6.src",
            "-e",
            "ipv6.dst",
            "-e",
            "tcp.srcport",
            "-e",
            "tcp.dstport",
            "-e",
            "tcp.payload",
        ]
        output = self._runner(cmd)
        tsv_lines = [line for line in output.splitlines() if line.strip()]
        return parse_tcp_stream_turns_output(
            tsv_lines=tsv_lines,
            stream_id=int(stream_id),
            format=format,
        )
