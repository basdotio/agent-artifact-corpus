"""MCP 服务端入口文件"""
import asyncio
from dotenv import load_dotenv

# 从 .env 文件加载环境变量（如 API 密钥）
load_dotenv()

from mcp.server import Server
from mcp.server.stdio import stdio_server

from src.mcp.tools import register_tools
from src.mcp.resources import register_resources
from src.mcp.prompts import register_prompts

# 初始化 MCP 服务端实例
server = Server("report-agent")

# 注册 MCP 的各项能力
register_tools(server)
register_resources(server)
register_prompts(server)

async def main():
    """使用 stdio 传输协议启动 MCP 服务端"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
