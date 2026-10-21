"""命令行参数、环境变量契约解析与服务端日志流配置模块。

@author Ateng
@since 2026-10-13
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TextIO, cast

from mcp_server_traffic_inspector import __version__

TransportMode = Literal["stdio", "sse", "streamable-http"]
LogLevelName = Literal["DEBUG", "INFO", "WARNING", "ERROR"]

VALID_TRANSPORTS: tuple[TransportMode, ...] = ("stdio", "sse", "streamable-http")
VALID_LOG_LEVELS: tuple[LogLevelName, ...] = ("DEBUG", "INFO", "WARNING", "ERROR")
LOGGER_NAME = "mcp_server_traffic_inspector"


@dataclass(frozen=True, slots=True)
class ServerConfig:
    """MCP 服务运行期全局不可变配置实体。

    Attributes:
        transport: MCP 通信传输协议模式（stdio、sse、streamable-http）。
        host: SSE 或 Streamable-HTTP 模式下绑定的监听地址。
        port: SSE 或 Streamable-HTTP 模式下绑定的监听端口。
        tshark_path: 显式指定的 tshark 可执行文件路径，未指定时为 None。
        db_path: SQLite WAL 共享数据库的本地文件绝对路径。
        bodies_dir: 超大报文载荷（>256KB）分流存储的本地临时目录路径。
        preserve_db: 进程退出时是否保留 SQLite 数据库文件（显式指定路径时为 True）。
        log_level: 服务端日志输出级别。
        check: 是否执行运行环境健康自检探针（--check / --doctor）并退出。
    """

    transport: TransportMode
    host: str
    port: int
    tshark_path: str | None
    db_path: Path
    bodies_dir: Path
    preserve_db: bool
    log_level: LogLevelName
    check: bool


def _build_arg_parser() -> argparse.ArgumentParser:
    epilog_text = (
        "环境变量对照 (优先级低于 CLI 参数，高于内置默认值):\n"
        "  MCP_TRAFFIC_INSPECTOR_TRANSPORT    传输模式 (stdio | sse | streamable-http)\n"
        "  MCP_TRAFFIC_INSPECTOR_HOST         监听地址 (默认: 127.0.0.1)\n"
        "  MCP_TRAFFIC_INSPECTOR_PORT         监听端口 (默认: 8000)\n"
        "  MCP_TRAFFIC_INSPECTOR_TSHARK_PATH  自定义 tshark 可执行文件绝对路径\n"
        "  MCP_TRAFFIC_INSPECTOR_DB_PATH      自定义 SQLite 数据库路径 (指定后退出不删除)\n"
        "  MCP_TRAFFIC_INSPECTOR_LOG_LEVEL    日志级别 (DEBUG | INFO | WARNING | ERROR)\n\n"
        "客户端接入示例:\n"
        "  本地 stdio: uv run mcp-server-traffic-inspector\n"
        "  远程 SSE:   "
        "uv run mcp-server-traffic-inspector --transport sse --host 0.0.0.0 --port 8000\n"
        "  环境自检:   uv run mcp-server-traffic-inspector --check\n"
    )
    parser = argparse.ArgumentParser(
        prog="mcp-server-traffic-inspector",
        description=(
            "面向 AI Agent 的全栈网络流量抓包、检索、协议诊断、请求重放与规则拦截 MCP Server"
        ),
        epilog=epilog_text,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"mcp-server-traffic-inspector {__version__}",
        help="输出当前版本号并退出",
    )
    parser.add_argument(
        "--check",
        "--doctor",
        dest="check",
        action="store_true",
        default=False,
        help="执行运行环境自检探针（检查 Python、mitmdump、tshark、CA 证书与 SQLite 权限）并退出",
    )
    parser.add_argument(
        "-t",
        "--transport",
        choices=VALID_TRANSPORTS,
        default=None,
        help="MCP 通信传输协议 (可选: stdio, sse, streamable-http；默认: stdio)",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="sse 或 streamable-http 模式下绑定的监听地址 (默认: 127.0.0.1)",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=None,
        help="sse 或 streamable-http 模式下绑定的监听端口 (默认: 8000)",
    )
    parser.add_argument(
        "--tshark-path",
        dest="tshark_path",
        default=None,
        help="显式指定 tshark 可执行文件绝对路径",
    )
    parser.add_argument(
        "--db-path",
        dest="db_path",
        default=None,
        help="显式指定 SQLite 数据库文件路径（显式指定时进程退出后保留文件）",
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        default=None,
        help="日志输出级别 (DEBUG, INFO, WARNING, ERROR；默认: INFO)",
    )
    return parser


def parse_config(
    argv: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> ServerConfig:
    """解析命令行参数与环境变量，生成不可变的服务端配置。

    遵循“CLI 命令行参数 > MCP_TRAFFIC_INSPECTOR_* 环境变量 > 内置默认值”的解析优先级。

    Args:
        argv: 命令行参数列表，为 None 时默认读取 sys.argv[1:]。
        env: 环境变量映射表，为 None 时默认读取 os.environ。

    Returns:
        解析并校验后的 ServerConfig 实例。

    Raises:
        ValueError: 当环境变量或参数中的传输协议、端口或日志级别非法时抛出。
    """
    # 1. 构建并解析 CLI 参数与环境变量源
    parser = _build_arg_parser()
    parsed = parser.parse_args(args=list(argv) if argv is not None else sys.argv[1:])
    env_map = env if env is not None else os.environ

    # 2. 按 CLI > 环境变量 > 默认值 顺序合并核心传输与网络配置
    raw_transport = (
        (parsed.transport or env_map.get("MCP_TRAFFIC_INSPECTOR_TRANSPORT") or "stdio")
        .strip()
        .lower()
    )
    if raw_transport not in VALID_TRANSPORTS:
        raise ValueError(f"不支持的传输协议模式: {raw_transport}")
    transport = cast(TransportMode, raw_transport)

    host = (parsed.host or env_map.get("MCP_TRAFFIC_INSPECTOR_HOST") or "127.0.0.1").strip()

    if parsed.port is not None:
        port = int(parsed.port)
    elif env_port := env_map.get("MCP_TRAFFIC_INSPECTOR_PORT"):
        port = int(env_port)
    else:
        port = 8000

    raw_tshark = parsed.tshark_path or env_map.get("MCP_TRAFFIC_INSPECTOR_TSHARK_PATH")
    tshark_path = raw_tshark.strip() if raw_tshark and raw_tshark.strip() else None

    # 3. 解析数据库路径与进程退出保留策略
    pid = os.getpid()
    temp_root = Path(tempfile.gettempdir())
    explicit_db = parsed.db_path or env_map.get("MCP_TRAFFIC_INSPECTOR_DB_PATH")
    if explicit_db and explicit_db.strip():
        db_path = Path(explicit_db.strip()).expanduser().resolve()
        preserve_db = True
    else:
        db_path = (temp_root / f"mcp_traffic_inspector_{pid}.db").resolve()
        preserve_db = False

    bodies_dir = (temp_root / f"mcp_traffic_inspector_bodies_{pid}").resolve()

    # 4. 校验并归一化日志级别
    raw_log_level = (
        (parsed.log_level or env_map.get("MCP_TRAFFIC_INSPECTOR_LOG_LEVEL") or "INFO")
        .strip()
        .upper()
    )
    if raw_log_level not in VALID_LOG_LEVELS:
        raise ValueError(f"不支持的日志级别: {raw_log_level}")
    log_level = cast(LogLevelName, raw_log_level)

    return ServerConfig(
        transport=transport,
        host=host,
        port=port,
        tshark_path=tshark_path,
        db_path=db_path,
        bodies_dir=bodies_dir,
        preserve_db=preserve_db,
        log_level=log_level,
        check=bool(parsed.check),
    )


def configure_logging(
    log_level: str = "INFO",
    stream: TextIO | None = None,
) -> logging.Logger:
    """配置工程受管日志器，强制将日志输出至 stderr 以保护 stdio JSON-RPC 管道。

    Args:
        log_level: 日志级别名称（DEBUG、INFO、WARNING、ERROR）。
        stream: 自定义输出流，为 None 时默认绑定至 sys.stderr。

    Returns:
        配置完成的工程根 Logger 实例。
    """
    target_stream = stream if stream is not None else sys.stderr
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(numeric_level)
    logger.propagate = False
    logger.handlers.clear()

    handler = logging.StreamHandler(target_stream)
    handler.setLevel(numeric_level)
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
