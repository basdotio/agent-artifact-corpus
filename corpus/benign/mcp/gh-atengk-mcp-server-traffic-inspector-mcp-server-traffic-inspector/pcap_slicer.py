"""报文时空切片 (PcapSlicer) 与捕获伴随元数据 (CaptureSidecar) 持久化管理模块。

@author Ateng
@since 2026-10-13
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mcp_server_traffic_inspector.config import LOGGER_NAME
from mcp_server_traffic_inspector.process_tracker import ProcessFamily, SocketTimeline

logger = logging.getLogger(LOGGER_NAME)


def build_slice_display_filter(ports: set[int]) -> str:
    """基于目标端口集合构建 Wireshark Display Filter 表达式。

    Args:
        ports: 待筛选的端口号集合。

    Returns:
        Wireshark 过滤表达式字符串，例如 '(tcp.port in {80, 443} || udp.port in {80, 443})'；
        端口集合为空时返回空字符串 ""。
    """
    valid_ports = {p for p in ports if p > 0}
    if not valid_ports:
        return ""

    port_list_str = ", ".join(str(p) for p in sorted(valid_ports))
    return f"(tcp.port in {{{port_list_str}}} || udp.port in {{{port_list_str}}})"


class CaptureSidecar:
    """管理与 .pcap 文件同名伴随落盘的结构化元数据 (.pcap.meta.json)。"""

    @staticmethod
    def get_sidecar_path(pcap_path: Path | str) -> Path:
        """获取目标 PCAP 文件对应的伴随元数据文件绝对路径。"""
        resolved = Path(pcap_path).resolve()
        return resolved.parent / f"{resolved.name}.meta.json"

    @classmethod
    def save(
        cls,
        pcap_path: Path | str,
        process_family: ProcessFamily,
        timeline: SocketTimeline,
        extra: dict[str, Any] | None = None,
    ) -> Path:
        """将抓包会话的进程家族与拓扑元数据持久化落盘至 Sidecar 文件。

        Args:
            pcap_path: 目标 PCAP 报文文件路径。
            process_family: 目标进程家族对象。
            timeline: 捕获期间采样的套接字时序流。
            extra: 附加元数据字典（如会话配置、标签等）。

        Returns:
            落盘的 Sidecar Path 对象。
        """
        meta_path = cls.get_sidecar_path(pcap_path)
        meta_path.parent.mkdir(parents=True, exist_ok=True)

        meta_data: dict[str, Any] = {
            "created_at": datetime.now(UTC).isoformat(),
            "pcap_file": str(Path(pcap_path).resolve()),
            "process_family": process_family.to_dict(),
            "server_topology": timeline.export_server_topology(process_family.all_pids),
            "extra": extra or {},
        }

        meta_path.write_text(
            json.dumps(meta_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return meta_path

    @classmethod
    def load(cls, pcap_path: Path | str) -> dict[str, Any] | None:
        """从本地读取与 PCAP 关联的伴随元数据，若不存在则返回 None。

        Args:
            pcap_path: 目标 PCAP 报文文件路径。

        Returns:
            解析后的元数据字典；文件不存在或损坏时返回 None。
        """
        meta_path = cls.get_sidecar_path(pcap_path)
        if not meta_path.is_file():
            return None
        try:
            content = meta_path.read_text(encoding="utf-8")
            return json.loads(content)
        except Exception as exc:
            logger.warning("读取 CaptureSidecar 元数据文件失败 (%s): %s", meta_path, exc)
            return None


def slice_pcap_file(
    raw_pcap_path: Path | str,
    target_pcap_path: Path | str,
    display_filter: str,
    tshark_bin: Path | str,
    runner: Callable[[list[str]], str],
    keep_raw_pcap: bool = False,
) -> dict[str, Any]:
    """调用 tshark 对原始抓包文件执行时空切片，并在完成后按策略清理中间全量文件。

    Args:
        raw_pcap_path: 原始全量抓包文件路径。
        target_pcap_path: 目标切片后纯净报文路径。
        display_filter: 用于切片的 Wireshark Display Filter。
        tshark_bin: tshark 可执行文件路径。
        runner: 命令执行器函数。
        keep_raw_pcap: 是否保留全量中间文件，默认 False（自动清理）。

    Returns:
        切片结果摘要字典。
    """
    raw_path = Path(raw_pcap_path).resolve()
    target_path = Path(target_pcap_path).resolve()

    if not raw_path.is_file():
        raise FileNotFoundError(f"原始 PCAP 文件不存在: {raw_path}")

    target_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. 组装 tshark 切片命令: tshark -r raw.pcap -Y filter -w target.pcap
    cmd = [
        str(tshark_bin),
        "-r",
        str(raw_path),
        "-w",
        str(target_path),
    ]
    if display_filter and display_filter.strip():
        cmd.extend(["-Y", display_filter.strip()])

    runner(cmd)

    # 2. 中间全量文件生命周期管理
    raw_kept = True
    if not keep_raw_pcap and raw_path != target_path:
        try:
            raw_path.unlink(missing_ok=True)
            raw_kept = False
        except OSError as exc:
            logger.warning("清理中间全量 PCAP 文件失败 (%s): %s", raw_path, exc)

    return {
        "status": "sliced",
        "output_file": str(target_path),
        "raw_pcap": str(raw_path) if raw_kept else None,
        "raw_kept": raw_kept,
        "filter_applied": display_filter,
    }
