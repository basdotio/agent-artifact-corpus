import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

import tools
from core import config, formatters, types, validations

_log = logging.getLogger()

# Define the MCP server
server = FastMCP(name="file-reader-server", version="1.0.0")

def config_server():
    path_args = sys.argv[1:]

    if not path_args:
        _log.warning("Not allowed paths provided mcp can access all system")
        path_args.append(os.path.abspath(os.sep))

    server_config = config.ServerConfig()
    for path in path_args:
        expanded_path = formatters.expand_home(path)
        validations.path_exists(expanded_path)
        validations.is_valid_dir(expanded_path)
        norm_path = formatters.normalize_path(expanded_path)
        server_config.allow_path(norm_path)

def register_tools():
    tools_list: list[types.BaseTool]   = [
        tools.ReadFileTool(),
        tools.ReadMultipleFilesTool(),
        tools.WriteFileTool(),
        tools.EditFileTool(),
        tools.CreateDirectoryTool(),
        tools.ListDirectoryTool(),
        tools.ListDirectoryWithSizeTool(),
        tools.DirectoryTreeTool(),
        tools.MoveFileTool(),
        tools.SearchFilesTool(),
        tools.GetFileInfoTool(),
        tools.GetAllowedPathsTool(),
    ]
    for tool in tools_list:
        server.add_tool(
            fn=tool.callback(),
            name=tool.name,
            description=tool.description,
        )

def main():
    # initialize server config
    config_server()
    # Register tools
    register_tools()
    server.run()


if __name__ == "__main__":
    main()