"""RabbitMQ MCP 服务端 CLI 命令行套件与双模网关启动入口.

@author Ateng
@since 2026-10-04
"""

import argparse
import contextlib
import io
import logging
import os
import sys

from mcp_server_rabbitmq.core.config import (
    load_config,
    set_global_config,
)
from mcp_server_rabbitmq.server import create_mcp_server

logger = logging.getLogger("mcp_server_rabbitmq")

# Windows 终端 GBK 编码容错与安全防御
if sys.platform == "win32":
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        with contextlib.suppress(io.UnsupportedOperation, AttributeError):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        with contextlib.suppress(io.UnsupportedOperation, AttributeError):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def build_parser() -> argparse.ArgumentParser:
    """构建 CLI 命令行参数解析器.

    @return 配置完整的 ArgumentParser 解析器实例
    """
    parser = argparse.ArgumentParser(
        prog="atengk-mcp-server-rabbitmq",
        description="专为 LLM 打造的生产级 RabbitMQ Model Context Protocol (MCP) 服务端",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # 基础连接与配置参数
    conn_group = parser.add_argument_group("RabbitMQ 连接配置")
    conn_group.add_argument(
        "--url",
        dest="url",
        default=None,
        help="RabbitMQ AMQP 0-9-1 连接协议串（如: amqp://user:pass@localhost:5672/）",
    )
    conn_group.add_argument(
        "--broker-host",
        "--rmq-host",
        dest="broker_host",
        default=None,
        help="RabbitMQ Broker 主机名或 IP 地址（默认: localhost）",
    )
    conn_group.add_argument(
        "--broker-port",
        "--rmq-port",
        dest="broker_port",
        type=int,
        default=None,
        help="RabbitMQ Broker AMQP 端口号（普通默认 5672，SSL 默认 5671）",
    )
    conn_group.add_argument(
        "-u",
        "--username",
        "--user",
        dest="username",
        default=None,
        help="RabbitMQ 认证用户名（默认: guest）",
    )
    conn_group.add_argument(
        "-P",
        "--password",
        dest="password",
        default=None,
        help="RabbitMQ 认证密码（默认: guest）",
    )
    conn_group.add_argument(
        "--vhost",
        dest="vhost",
        default=None,
        help="RabbitMQ 虚拟主机名称（默认: /）",
    )
    conn_group.add_argument(
        "--ssl",
        action=argparse.BooleanOptionalAction,
        dest="ssl",
        default=None,
        help="是否启用 AMQP SSL/TLS 加密传输 (amqps://)",
    )
    conn_group.add_argument(
        "-c",
        "--config",
        dest="config",
        default=None,
        help="多环境实例连接配置文件路径（connections.yaml）",
    )

    # Management HTTP API 参数
    mgmt_group = parser.add_argument_group("RabbitMQ Management HTTP API 配置")
    mgmt_group.add_argument(
        "--management-url",
        dest="management_url",
        default=None,
        help="RabbitMQ Management HTTP API 地址（如: http://user:pass@localhost:15672）",
    )
    mgmt_group.add_argument(
        "--management-host",
        dest="management_host",
        default=None,
        help="Management HTTP 服务主机名（默认继承 Broker 主机）",
    )
    mgmt_group.add_argument(
        "--management-port",
        dest="management_port",
        type=int,
        default=None,
        help="Management HTTP 服务端口号（默认: 15672）",
    )
    mgmt_group.add_argument(
        "--management-ssl",
        action=argparse.BooleanOptionalAction,
        dest="management_ssl",
        default=None,
        help="是否启用 Management API HTTPS 协议 (https://)",
    )

    # 安全门禁控制
    sec_group = parser.add_argument_group("安全与写门禁防线")
    sec_group.add_argument(
        "--allow-write",
        dest="allow_write",
        action="store_true",
        default=False,
        help="解除只读保护，允许执行声明、清空、删除队列/交换机及消息发布等高危写操作",
    )

    # 双模传输网关配置
    trans_group = parser.add_argument_group("双模通信网关")
    default_transport = os.getenv("MCP_RABBITMQ_TRANSPORT", "stdio").lower()
    trans_group.add_argument(
        "-t",
        "--transport",
        dest="transport",
        choices=["stdio", "sse"],
        default=default_transport if default_transport in ("stdio", "sse") else "stdio",
        help="MCP 传输层通信协议：stdio（标准输入输出）或 sse（常驻 HTTP SSE）",
    )
    trans_group.add_argument(
        "--host",
        dest="host",
        default=os.getenv("MCP_RABBITMQ_SERVER_HOST", "0.0.0.0"),
        help="常驻 HTTP SSE 网关监听网络地址",
    )
    trans_group.add_argument(
        "-p",
        "--port",
        dest="port",
        type=int,
        default=int(os.getenv("MCP_RABBITMQ_SERVER_PORT", "8000")),
        help="常驻 HTTP SSE 网关监听端口",
    )

    # 调试与常规参数
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",
        default=False,
        help="开启详细 DEBUG 日志输出",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="atengk-mcp-server-rabbitmq 1.0.4",
        help="显示当前服务版本号并退出",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    """CLI 主执行入口.

    负责参数解析、配置分层覆盖（CLI > ENV > Config）、全局状态装配与双模网关启动。

    @param argv 可选的命令行参数切片，为 None 时默认读取 sys.argv[1:]
    """
    # 1. 解析命令行参数并初始化受管日志框架
    parser = build_parser()
    args = parser.parse_args(argv)

    log_level = logging.DEBUG if args.verbose else getattr(
        logging, os.getenv("MCP_RABBITMQ_LOG_LEVEL", "INFO").upper(), logging.INFO
    )
    # stdio 模式下日志必须输出到 stderr，绝不能污染 stdout 数据通道
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    logger.info("正在启动 RabbitMQ MCP 服务端 (模式: %s)...", args.transport)

    # 2. 组装多层配置并应用 CLI 最高优先级覆盖 (ADR-0001)
    config = load_config(config_path=args.config)
    config.apply_cli_overrides(
        url=args.url,
        management_url=args.management_url,
        allow_write=args.allow_write,
        broker_host=args.broker_host,
        broker_port=args.broker_port,
        username=args.username,
        password=args.password,
        vhost=args.vhost,
        ssl=args.ssl,
        management_host=args.management_host,
        management_port=args.management_port,
        management_ssl=args.management_ssl,
    )
    if args.allow_write:
        logger.info("已通过 --allow-write 解除写操作保护，当前处于读写完全放行状态")

    set_global_config(config)

    # 3. 创建 FastMCP 实例并依序挂载双模传输网关
    server = create_mcp_server()

    if args.transport == "sse":
        logger.info("启动常驻 HTTP SSE 服务，监听地址: http://%s:%d/sse", args.host, args.port)
        server.run(transport="sse", host=args.host, port=args.port)
    else:
        logger.info("启动 Stdio 管道通信网关，等待客户端 JSON-RPC 会话交互...")
        server.run(transport="stdio")


if __name__ == "__main__":
    main()
