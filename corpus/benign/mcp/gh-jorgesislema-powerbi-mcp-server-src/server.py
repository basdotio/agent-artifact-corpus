#!/usr/bin/env python3
"""
Servidor MCP para Power BI
Permite a GitHub Copilot interactuar con modelos de Power BI
"""
import asyncio
import os
import sys
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Ensure the vendor directory containing AdomdClient.dll is on the DLL search path
vendor_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'vendor', 'adomd'))
if os.path.isdir(vendor_dir):
    os.add_dll_directory(vendor_dir)

from src.tools import TOOLS, handle_tool_call

# Crear servidor MCP
app = Server("powerbi-mcp-server")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """Lista todas las herramientas disponibles"""
    tools = []
    for tool_def in TOOLS:
        tools.append(Tool(
            name=tool_def["name"],
            description=tool_def["description"],
            inputSchema=tool_def["inputSchema"]
        ))
    return tools

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Ejecuta una herramienta específica"""
    result_json = await handle_tool_call(name, arguments)
    return [TextContent(type="text", text=result_json)]

async def _main_async():
    """Punto de entrada principal"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="powerbi-mcp-server",
                server_version="1.0.0",
                capabilities={}
            ),
            NotificationOptions()
        )

def main():
    """Wrapper sync para usar en console_scripts."""
    try:
        asyncio.run(_main_async())
    except KeyboardInterrupt:
        # Ctrl-C was pressed; exit cleanly
        print("Servidor MCP detenido por el usuario.")
        return
    except Exception as e:
        # Any other unexpected error
        print(f"Error inesperado al iniciar el servidor MCP: {e}")
        print("Asegúrate de que VS Code o el cliente MCP estén proporcionando entrada por stdin.")
        return

if __name__ == "__main__":
    main()