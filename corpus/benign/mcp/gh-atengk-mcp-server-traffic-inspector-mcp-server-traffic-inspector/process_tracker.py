"""进程家族树 (ProcessFamily) 感知、同目录边界防护与套接字时序流 (SocketTimeline) 动态采样模块。

@author Ateng
@since 2026-10-13
"""

from __future__ import annotations

import fnmatch
import logging
import socket
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import PurePath, PureWindowsPath
from typing import Any

import psutil

from mcp_server_traffic_inspector.config import LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)


@dataclass(frozen=True, slots=True)
class ProcessInfo:
    """系统单个活跃进程的元数据。

    Attributes:
        pid: 进程唯一数字 ID。
        ppid: 父进程数字 ID。
        name: 可执行文件名称（如 'Weixin.exe'）。
        exe_path: 可执行文件绝对路径（若有权限获取）。
    """

    pid: int
    ppid: int | None
    name: str
    exe_path: str = ""


@dataclass(frozen=True, slots=True)
class ProcessFamily:
    """目标进程及其合法子进程构成的进程家族。

    Attributes:
        root_pid: 主进程数字 ID。
        all_pids: 包含主进程与全部合法子进程的 PID 集合。
        members: 成员进程元数据列表。
    """

    root_pid: int | None
    all_pids: set[int]
    members: list[ProcessInfo] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """将进程家族对象序列化为结构化字典。

        Returns:
            包含 root_pid、all_pids 与 members 列表的字典。
        """
        return {
            "root_pid": self.root_pid,
            "all_pids": sorted(self.all_pids),
            "members": [asdict(m) for m in self.members],
        }


@dataclass(frozen=True, slots=True)
class SocketEntry:
    """单个套接字连接/绑定端点记录。

    Attributes:
        proto: 传输层协议 ('TCP' 或 'UDP')。
        local_ip: 本地绑定 IP 地址。
        local_port: 本地端口号。
        remote_ip: 远端对端 IP 地址（若已建立连接）。
        remote_port: 远端对端端口号。
        pid: 拥有该套接字的所属进程 PID。
        state: 连接状态（如 'ESTABLISHED', 'LISTEN'）。
    """

    proto: str
    local_ip: str
    local_port: int
    remote_ip: str = ""
    remote_port: int = 0
    pid: int | None = None
    state: str = ""


class SocketTimeline:
    """在抓包生命周期内记录套接字端点与 PID 绑定关系的时序流集合。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # 记录结构: list[tuple[timestamp, list[SocketEntry]]]
        self._snapshots: list[tuple[float, list[SocketEntry]]] = []

    def record_snapshot(self, timestamp: float, entries: list[SocketEntry]) -> None:
        """记录一个时间戳切片下的套接字连接快照。"""
        with self._lock:
            self._snapshots.append((timestamp, list(entries)))

    def get_active_ports(self, target_pids: set[int]) -> set[int]:
        """获取整个捕获周期内，目标 PID 家族使用过的全部本地端口集合。"""
        if not target_pids:
            return set()
        ports: set[int] = set()
        with self._lock:
            for _ts, entries in self._snapshots:
                for entry in entries:
                    if entry.pid in target_pids and entry.local_port > 0:
                        ports.add(entry.local_port)
        return ports

    def export_server_topology(self, target_pids: set[int]) -> list[dict[str, Any]]:
        """聚合导出目标 PID 家族通信过的全部远端服务器端点画像。"""
        if not target_pids:
            return []

        topology_map: dict[tuple[str, int, str], dict[str, Any]] = {}
        with self._lock:
            for _ts, entries in self._snapshots:
                for entry in entries:
                    if (
                        entry.pid in target_pids
                        and entry.remote_ip
                        and entry.remote_ip != "0.0.0.0"
                    ):
                        key = (entry.remote_ip, entry.remote_port, entry.proto)
                        if key not in topology_map:
                            topology_map[key] = {
                                "server_ip": entry.remote_ip,
                                "port": entry.remote_port,
                                "protocol": entry.proto,
                                "associated_pids": set(),
                                "hit_count": 0,
                            }
                        topology_map[key]["associated_pids"].add(entry.pid)
                        topology_map[key]["hit_count"] += 1

        result: list[dict[str, Any]] = []
        for val in topology_map.values():
            result.append(
                {
                    "server_ip": val["server_ip"],
                    "port": val["port"],
                    "protocol": val["protocol"],
                    "associated_pids": sorted(val["associated_pids"]),
                    "hit_count": val["hit_count"],
                }
            )
        return sorted(result, key=lambda x: (x["server_ip"], x["port"]))

    def to_dict(self) -> dict[str, Any]:
        """序列化为可持久化字典。"""
        with self._lock:
            snapshots_data = []
            for ts, entries in self._snapshots:
                snapshots_data.append(
                    {
                        "timestamp": ts,
                        "entries": [asdict(e) for e in entries],
                    }
                )
            return {"snapshots": snapshots_data}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SocketTimeline:
        """从字典反序列化创建 SocketTimeline 实例。"""
        instance = cls()
        for snap in data.get("snapshots", []):
            ts = float(snap.get("timestamp", 0.0))
            entries = [
                SocketEntry(
                    proto=e.get("proto", "TCP"),
                    local_ip=e.get("local_ip", ""),
                    local_port=int(e.get("local_port", 0)),
                    remote_ip=e.get("remote_ip", ""),
                    remote_port=int(e.get("remote_port", 0)),
                    pid=e.get("pid"),
                    state=e.get("state", ""),
                )
                for e in snap.get("entries", [])
            ]
            instance.record_snapshot(ts, entries)
        return instance


class ProcessFamilyDetector:
    """负责解析目标主进程与其合法派生子进程家族 (ProcessFamily)。"""

    @staticmethod
    def _to_pure_path(path_str: str) -> PurePath:
        """根据路径特征将其转换为 PureWindowsPath 或通用 PurePath。

        若包含反斜杠或形如 C: 的驱动器前缀，优先转为 PureWindowsPath，
        以保障在非 Windows 系统（如 Linux CI）上也能准确按层级解析。
        """
        clean = path_str.strip()
        if "\\" in clean or (len(clean) >= 2 and clean[1] == ":"):
            return PureWindowsPath(clean)
        return PurePath(clean)

    @classmethod
    def is_path_allowed(cls, child_exe: str, root_dir: str) -> bool:
        """判定子进程的可执行文件路径是否位于主程序所在的根目录树内。

        避免微信点击外链拉起外部 Chrome/Edge 时被纳入流量统计。

        Args:
            child_exe: 子进程可执行文件绝对路径。
            root_dir: 主程序所在根目录路径。

        Returns:
            若子进程位于根目录树内返回 True，否则返回 False。
        """
        if not child_exe or not root_dir:
            return False
        try:
            child_p = cls._to_pure_path(child_exe)
            root_p = cls._to_pure_path(root_dir)
            # 在 Windows 路径语义下进行大小写无关的层级包含判定
            if isinstance(child_p, PureWindowsPath) and isinstance(root_p, PureWindowsPath):
                child_parts = [p.lower() for p in child_p.parts]
                root_parts = [p.lower() for p in root_p.parts]
                if len(child_parts) < len(root_parts):
                    return False
                return child_parts[: len(root_parts)] == root_parts
            return child_p.is_relative_to(root_p)
        except (ValueError, OSError):
            return False

    def resolve_family(
        self,
        snapshot: list[ProcessInfo],
        process_path: str | None = None,
        process_name: str | None = None,
        target_pids: list[int] | None = None,
        include_child_processes: bool = True,
    ) -> ProcessFamily:
        """基于进程快照解析目标 ProcessFamily。

        Args:
            snapshot: 系统进程快照列表。
            process_path: 可选的目标可执行文件绝对路径。
            process_name: 可选的目标进程名称通配符。
            target_pids: 可选的显式指定目标 PID 列表。
            include_child_processes: 是否递归发现并纳入合法子进程。

        Returns:
            解析出的 ProcessFamily 对象；无匹配时返回空的 ProcessFamily。
        """
        matched_roots: list[ProcessInfo] = []
        root_dir = ""

        # 1. 规范化并定位候选主进程
        if process_path and process_path.strip():
            raw_path = process_path.strip()
            pure_root = self._to_pure_path(raw_path)
            clean_path = str(pure_root).lower()
            root_dir = str(pure_root.parent)
            for p in snapshot:
                p_pure = self._to_pure_path(p.exe_path) if p.exe_path else None
                p_exe = str(p_pure).lower() if p_pure else ""
                if p_exe == clean_path:
                    matched_roots.append(p)
                    break
                # 若无权限获取 exe_path，兜底匹配名称
                if not p_exe and p.name.lower() == pure_root.name.lower():
                    matched_roots.append(p)

        elif process_name and process_name.strip():
            pat = process_name.strip().lower()
            for p in snapshot:
                if fnmatch.fnmatch(p.name.lower(), pat):
                    matched_roots.append(p)

        elif target_pids:
            target_set = set(target_pids)
            for p in snapshot:
                if p.pid in target_set:
                    matched_roots.append(p)

        if not matched_roots:
            # 未发现主进程时，返回空家族
            return ProcessFamily(root_pid=None, all_pids=set(), members=[])

        primary_root = matched_roots[0]
        root_pid = primary_root.pid
        if not root_dir and primary_root.exe_path:
            root_dir = str(self._to_pure_path(primary_root.exe_path).parent)
        family_pids = {root_pid}
        members_map: dict[int, ProcessInfo] = {root_pid: primary_root}

        # 2. 若不包含子进程，直接返回
        if not include_child_processes:
            return ProcessFamily(
                root_pid=root_pid,
                all_pids=family_pids,
                members=list(members_map.values()),
            )

        # 3. 递归发现合法子进程
        # 构建 ppid -> list[ProcessInfo] 映射
        children_map: dict[int, list[ProcessInfo]] = {}
        for p in snapshot:
            if p.ppid is not None:
                children_map.setdefault(p.ppid, []).append(p)

        queue = [root_pid]
        while queue:
            parent_pid = queue.pop(0)
            direct_children = children_map.get(parent_pid, [])
            for child in direct_children:
                if child.pid in family_pids:
                    continue

                # 校验同目录白名单防护
                allowed = True
                if root_dir and child.exe_path:
                    allowed = self.is_path_allowed(child.exe_path, root_dir)

                if allowed:
                    family_pids.add(child.pid)
                    members_map[child.pid] = child
                    queue.append(child.pid)

        return ProcessFamily(
            root_pid=root_pid,
            all_pids=family_pids,
            members=list(members_map.values()),
        )


def capture_system_process_snapshot() -> list[ProcessInfo]:
    """获取当前系统活跃进程快照。"""
    results: list[ProcessInfo] = []
    for proc in psutil.process_iter(["pid", "ppid", "name", "exe"]):
        try:
            info = proc.info
            pid = int(info["pid"])
            ppid = int(info["ppid"]) if info.get("ppid") is not None else None
            name = str(info.get("name") or "")
            exe = str(info.get("exe") or "")
            results.append(ProcessInfo(pid=pid, ppid=ppid, name=name, exe_path=exe))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return results


def capture_system_socket_entries() -> list[SocketEntry]:
    """获取当前系统活跃网络套接字连接列表。"""
    entries: list[SocketEntry] = []
    try:
        conns = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, OSError):
        return []

    for c in conns:
        proto = "TCP" if c.type == socket.SOCK_STREAM else "UDP"
        l_ip = c.laddr.ip if c.laddr else ""
        l_port = int(c.laddr.port) if c.laddr else 0
        r_ip = c.raddr.ip if c.raddr else ""
        r_port = int(c.raddr.port) if c.raddr else 0
        entries.append(
            SocketEntry(
                proto=proto,
                local_ip=l_ip,
                local_port=l_port,
                remote_ip=r_ip,
                remote_port=r_port,
                pid=c.pid,
                state=str(c.status or ""),
            )
        )
    return entries


class ProcessFamilyTracker:
    """负责在抓包期间以固定 100ms 轮询采集 ProcessFamily 与 SocketTimeline。

    支持目标进程尚未启动时的异步挂起等待。
    """

    def __init__(
        self,
        process_path: str | None = None,
        process_name: str | None = None,
        target_pids: list[int] | None = None,
        include_child_processes: bool = True,
        poll_interval: float = 0.1,  # 100ms
        snapshot_fetcher: Callable[[], list[ProcessInfo]] | None = None,
        socket_fetcher: Callable[[], list[SocketEntry]] | None = None,
    ) -> None:
        self.process_path = process_path
        self.process_name = process_name
        self.target_pids = target_pids
        self.include_child_processes = include_child_processes
        self.poll_interval = max(0.02, float(poll_interval))

        self._snapshot_fetcher = snapshot_fetcher or capture_system_process_snapshot
        self._socket_fetcher = socket_fetcher or capture_system_socket_entries

        self.timeline = SocketTimeline()
        self.detector = ProcessFamilyDetector()
        self.latest_family = ProcessFamily(root_pid=None, all_pids=set(), members=[])

        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """启动后台 100ms 轮询采样线程。"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self) -> tuple[ProcessFamily, SocketTimeline]:
        """停止轮询线程并返回捕获到的最终 ProcessFamily 与 SocketTimeline。"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        return self.latest_family, self.timeline

    def _poll_loop(self) -> None:
        while self._running:
            now = time.monotonic()
            try:
                # 1. 刷新进程快照并发现当前活跃的 ProcessFamily
                snapshot = self._snapshot_fetcher()
                family = self.detector.resolve_family(
                    snapshot=snapshot,
                    process_path=self.process_path,
                    process_name=self.process_name,
                    target_pids=self.target_pids,
                    include_child_processes=self.include_child_processes,
                )
                if family.all_pids:
                    # 动态合并历史已知 PID（防止短命子进程销毁后被移出目标池）
                    merged_pids = self.latest_family.all_pids | family.all_pids
                    root_pid = self.latest_family.root_pid or family.root_pid
                    members = {m.pid: m for m in self.latest_family.members}
                    for m in family.members:
                        members[m.pid] = m
                    self.latest_family = ProcessFamily(
                        root_pid=root_pid,
                        all_pids=merged_pids,
                        members=list(members.values()),
                    )

                # 2. 采集当前活跃的套接字连接
                conns = self._socket_fetcher()
                self.timeline.record_snapshot(now, conns)
            except Exception as exc:
                logger.debug("ProcessFamilyTracker 轮询异常: %s", exc)

            time.sleep(self.poll_interval)
