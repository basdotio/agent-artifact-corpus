import asyncio
from typing import Any
from dingtalk.contacts import DingtalkContactsServer
from dingtalk.im import DingtalkIMServer
from mcp.server import Server as MCPServer
from mcp import stdio_server
import mcp.types as types

async def serve():
    _mcp_server = MCPServer(name="DingtalkIMServer")
    dingtalkContactsServer = DingtalkContactsServer()
    dingtalkIMServer = DingtalkIMServer()

    tool_contacts = [f for f in dir(DingtalkContactsServer) if not f.startswith("__")]
    tool_im = [f for f in dir(DingtalkIMServer) if not f.startswith("__")]

    @_mcp_server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """
        List all available tools.
        """
        return dingtalkContactsServer.list_tools() + dingtalkIMServer.list_tools()
    
    @_mcp_server.call_tool()
    async def handle_tool_call(
        name: str, arguments: dict[str, Any] | None = None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        try:
            match name:
                case n if n in tool_im:
                    method = getattr(dingtalkIMServer, n)
                case n if n in tool_contacts:
                    method = getattr(dingtalkContactsServer, n)

            if callable(method):
                result = await method(**arguments)
                return [types.TextContent(type="text", text=str(result))]
            else:
                raise Exception(f"Tool {name} not found")

        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async with stdio_server() as (read_stream, write_stream):
        try:
            await _mcp_server.run(
                read_stream,
                write_stream,
                _mcp_server.create_initialization_options(),
            )
        except Exception as e:
            raise
        finally:
            await dingtalkContactsServer.cleanup()
            await dingtalkIMServer.cleanup()
    
class ServerWrapper():
    """A wrapper to compat with mcp[cli]"""
    def run(self):
        asyncio.run(serve())

server = ServerWrapper()

if __name__ == '__main__':
    server.run()