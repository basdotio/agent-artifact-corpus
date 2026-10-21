"""mcp-server-traffic-inspector 命令行启动入口模块。

@author Ateng
@since 2026-10-13
"""

from __future__ import annotations

import atexit
import signal
import sys
from collections.abc import Callable, Mapping, Sequence
from types import FrameType
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_server_traffic_inspector.config import (
    TransportMode,
    configure_logging,
    parse_config,
)
from mcp_server_traffic_inspector.doctor import run_doctor
from mcp_server_traffic_inspector.server import LifecycleManager, create_mcp_server
from mcp_server_traffic_inspector.storage import StorageBus


def _default_runner(mcp: FastMCP, transport: TransportMode) -> None:
    mcp.run(transport=transport)


def main(
    argv: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
    runner: Callable[[Any, TransportMode], None] | None = None,
) -> int:
    """CLI 主入口函数，解析配置并执行环境自检或启动 FastMCP 服务。

    Args:
        argv: 命令行参数序列，为 None 时默认读取 sys.argv[1:]。
        env: 环境变量映射表，为 None 时默认读取 os.environ。
        runner: 可选的服务启动执行器（便于测试注入），默认调用 FastMCP.run。

    Returns:
        进程退出状态码（0 表示正常完成，非 0 表示自检或运行异常）。
    """
    # 1. 解析配置并初始化强制绑定至 stderr 的受管日志器
    config = parse_config(argv=argv, env=env)
    logger = configure_logging(log_level=config.log_level)

    # 2. 若指定 --check / --doctor，执行环境健康自检探针后直接返回退出码
    if config.check:
        report = run_doctor(config)
        sys.stdout.write(report.to_json() + "\n")
        sys.stdout.flush()
        return report.exit_code

    # 3. 初始化 SQLite WAL 共享数据总线与退出清理钩子
    storage = StorageBus.from_config(config)
    lifecycle = LifecycleManager()
    lifecycle.register(storage.cleanup)
    atexit.register(lifecycle.run_cleanup)

    def _handle_termination(signum: int, _frame: FrameType | None) -> None:
        logger.info("接收到终止信号 (%s)，正在执行资源清理...", signum)
        lifecycle.run_cleanup()
        raise SystemExit(0)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handle_termination)
        except (ValueError, OSError) as exc:
            logger.debug("当前线程或平台不支持注册信号处理器 (%s): %s", sig, exc)

    # 4. 启动 FastMCP 服务并在退出时保障清理执行
    try:
        mcp = create_mcp_server(config=config, storage=storage, lifecycle=lifecycle)
        logger.info(
            "正在启动 %s (transport=%s, db=%s)",
            mcp.name,
            config.transport,
            config.db_path,
        )
        active_runner = runner if runner is not None else _default_runner
        active_runner(mcp, config.transport)
        return 0
    finally:
        lifecycle.run_cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
