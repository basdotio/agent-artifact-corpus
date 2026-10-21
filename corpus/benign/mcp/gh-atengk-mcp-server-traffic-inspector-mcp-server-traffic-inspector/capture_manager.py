"""受控 mitmdump 代理子进程与 CaptureSession 生命周期管理模块。

@author Ateng
@since 2026-10-13
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from mcp_server_traffic_inspector.config import LOGGER_NAME
from mcp_server_traffic_inspector.doctor import resolve_mitmdump_path
from mcp_server_traffic_inspector.storage import StorageBus

logger = logging.getLogger(LOGGER_NAME)


class WorkerProcessProtocol(Protocol):
    """受控后台工作进程协议接口。"""

    def poll(self) -> int | None:
        """检查子进程是否已退出，运行中返回 None。"""
        ...

    def terminate(self) -> None:
        """发送温和终止信号。"""
        ...

    def wait(self, timeout: float | None = None) -> int:
        """等待子进程退出。"""
        ...

    def kill(self) -> None:
        """强制杀死子进程。"""
        ...


def _default_spawner(cmd: list[str], env: dict[str, str]) -> WorkerProcessProtocol:
    return subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )


class HttpCaptureManager:
    """管理应用层 HTTP/HTTPS 抓包会话 (CaptureSession) 与 mitmdump 工作子进程。"""

    def __init__(
        self,
        storage: StorageBus,
        process_spawner: Callable[[list[str], dict[str, str]], WorkerProcessProtocol] | None = None,
    ) -> None:
        """初始化 HTTP 抓包会话管理器。

        Args:
            storage: 共享 SQLite WAL 数据总线实例。
            process_spawner: 可选的子进程启动器函数（用于测试替身注入），默认调用 subprocess.Popen。
        """
        self.storage = storage
        self._spawner = process_spawner or _default_spawner
        self._process: WorkerProcessProtocol | None = None
        self._active_session_id: str | None = None
        self._last_session_id: str | None = None
        self._listen_host: str | None = None
        self._port: int | None = None
        self._started_at: float | None = None

    def _is_process_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def _terminate_process(self) -> None:
        proc = self._process
        self._process = None
        if proc is None:
            return
        try:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
        except Exception as exc:
            logger.warning("停止 mitmdump 子进程时发生异常: %s", exc)

    def start_capture(
        self,
        port: int = 8080,
        listen_host: str = "0.0.0.0",
        filter_host: str | None = None,
        ssl_insecure: bool = True,
    ) -> dict[str, Any]:
        """启动新的 CaptureSession 与受控 mitmdump 后台代理进程。

        若已有正在运行的抓包会话，将先优雅终止旧会话再启动新会话。

        Args:
            port: 代理监听端口，默认 8080。
            listen_host: 代理绑定地址，默认 "0.0.0.0"。
            filter_host: 可选的目标采集域名（非目标域名正常代理透传，仅目标域名入库）。
            ssl_insecure: 是否跳过上游服务端 TLS 证书校验，默认 True。

        Returns:
            包含 status、listen_host、port、session_id、db_path 与 ca_cert_path 的字典。
        """
        # 1. 若存在运行中的旧抓包进程，先执行安全终止
        if self._is_process_running():
            self.stop_capture()

        # 2. 生成新会话标识并组装 mitmdump 启动命令与环境变量
        session_id = f"sess_{uuid4().hex[:12]}"
        mitmdump_bin = resolve_mitmdump_path()
        executable = str(mitmdump_bin) if mitmdump_bin is not None else "mitmdump"
        addon_script = Path(__file__).with_name("proxy_addon.py").resolve()

        cmd = [
            executable,
            "--listen-host",
            listen_host,
            "--listen-port",
            str(int(port)),
            "-s",
            str(addon_script),
            "-q",
        ]
        if ssl_insecure:
            cmd.append("--ssl-insecure")

        child_env = dict(os.environ)
        child_env["MCP_CAPTURE_DB_PATH"] = str(self.storage.db_path)
        child_env["MCP_CAPTURE_BODIES_DIR"] = str(self.storage.bodies_dir)
        child_env["MCP_CAPTURE_SESSION_ID"] = session_id
        child_env["MCP_CAPTURE_FILTER_HOST"] = (filter_host or "").strip()

        # 3. 启动受控后台子进程并记录会话状态
        self._process = self._spawner(cmd, child_env)
        self._active_session_id = session_id
        self._last_session_id = session_id
        self._listen_host = listen_host
        self._port = int(port)
        self._started_at = time.monotonic()

        ca_cert_path = (Path.home() / ".mitmproxy" / "mitmproxy-ca-cert.pem").resolve()
        return {
            "status": "running",
            "listen_host": listen_host,
            "port": int(port),
            "session_id": session_id,
            "db_path": str(self.storage.db_path),
            "ca_cert_path": str(ca_cert_path),
        }

    def stop_capture(self) -> dict[str, Any]:
        """优雅停止当前正在运行的 HTTP/HTTPS 抓包代理子进程。

        Returns:
            包含 status ("stopped")、session_id 与 total_captured_flows 的统计字典。
        """
        # 1. 终止受控 mitmdump 后台工作进程
        target_session = self._active_session_id or self._last_session_id
        self._terminate_process()
        self._active_session_id = None
        self._listen_host = None
        self._port = None
        self._started_at = None

        # 2. 统计该会话已落库的 HttpFlow 总数
        flow_count = self.storage.count_flows(session_id=target_session) if target_session else 0
        return {
            "status": "stopped",
            "session_id": target_session,
            "total_captured_flows": flow_count,
        }

    def get_status(self) -> dict[str, Any]:
        """查询当前 HTTP 抓包代理的运行状态、捕获流数量与运行时长。

        Returns:
            包含 is_capturing、listen_host、port、session_id、flow_count 与 uptime_seconds 的字典。
        """
        is_running = self._is_process_running()
        if not is_running and self._active_session_id is not None:
            self._active_session_id = None

        session_id = self._active_session_id or self._last_session_id
        flow_count = self.storage.count_flows(session_id=session_id) if session_id else 0
        uptime = (
            round(max(0.0, time.monotonic() - self._started_at), 2)
            if is_running and self._started_at is not None
            else 0.0
        )

        return {
            "is_capturing": is_running,
            "listen_host": self._listen_host if is_running else None,
            "port": self._port if is_running else None,
            "session_id": session_id,
            "flow_count": flow_count,
            "uptime_seconds": uptime,
        }
