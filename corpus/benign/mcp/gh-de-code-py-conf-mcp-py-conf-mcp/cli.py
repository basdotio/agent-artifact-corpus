import argparse
from typing import Literal
from fastmcp import FastMCP

from py_conf_mcp.config import LOGGER, AppConfig, load_app_config
from py_conf_mcp.tools.resolver import ConfigToolResolver


def create_mcp_for_app_config(app_config: AppConfig) -> FastMCP:
    LOGGER.info('app_config: %r', app_config)

    tool_resolver = ConfigToolResolver(
        tool_definitions_config=app_config.tool_definitions
    )

    tools = tool_resolver.get_tools_by_name(app_config.server.tools)
    LOGGER.info('Tools: %r', tools)

    mcp: FastMCP = FastMCP(app_config.server.name, stateless_http=True)

    for tool in tools:
        mcp.add_tool(
            tool.tool_fn,
            name=tool.name,
            description=tool.description
        )

    return mcp


def create_mcp() -> FastMCP:
    app_config = load_app_config()
    return create_mcp_for_app_config(app_config=app_config)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='MCP CLI')
    parser.add_argument(
        '--transport',
        type=str,
        default='stdio',
        choices=['sse', 'stdio', 'streamable-http']
    )
    parser.add_argument('--host', type=str, default='localhost')
    parser.add_argument('--port', type=int, default=8080)
    return parser.parse_args()


def run(
    transport: Literal['stdio', 'sse'],
    host: str,
    port: int
) -> None:
    mcp = create_mcp()
    mcp.run(transport=transport, host=host, port=port)


def main():
    args = parse_args()
    LOGGER.info('Arguments: %r', args)
    run(
        transport=args.transport,
        host=args.host,
        port=args.port
    )
