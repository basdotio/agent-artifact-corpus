from __future__ import annotations
import logging
import os

from mcp.server.fastmcp import FastMCP
from services import process_service

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler("logs/mcp.log", encoding="utf-8"),
    ],
)

mcp = FastMCP("system-info-mcp-server")


@mcp.tool(
    description="This tool returns system information like CPU, RAM, Disk usage, etc."
)
def system_info_tool():
    return process_service.get_system_info().to_dict()


@mcp.tool(
    description="This tool checks for processes consuming excessive resources and suggests closing them."
)
def resource_usage_tool():
    return process_service.get_high_resource_usage()


@mcp.tool(
        description="Terminate a process after validation and user confirmation"
)
def terminate_process_tool(pid: int, confirmed: bool):

    if not confirmed:
        return {"success": False, "message": "User confirmation required", "pid": pid}
    return process_service.terminate_process_with_validation(pid)



@mcp.tool(
        description="Return all running processes in the system"
)
def list_processes_tool():
    return process_service.get_processes()


if __name__ == "__main__":
    print("Starting MCP server...")
    mcp.run()
