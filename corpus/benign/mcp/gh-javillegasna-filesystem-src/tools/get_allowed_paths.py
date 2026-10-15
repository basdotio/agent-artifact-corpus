from mcp.types import TextContent
from pydantic import BaseModel

from core.config import ServerConfig
from core.enums import FileSystemTools
from core.types import BaseTool


class GetAllowedPathsInput(BaseModel): ...


TOOL_DESCRIPTION = f"""
    Get a detailed listing of all files and directories in a specified path.
    Results clearly distinguish between files and directories with [FILE] and [DIR]
    prefixes. This tool is essential for understanding directory structure and 
    finding specific files within a directory. Only works within allowed directories.
    @Input:
        path: The path to the file to read.
    @Output:
        text: text with list of files/dir names.
    @Schema: {GetAllowedPathsInput.model_json_schema()}
"""


class GetAllowedPathsTool(BaseTool):
    def __init__(self):
        super().__init__(
            inputSchema=GetAllowedPathsInput.model_json_schema(),
            name=FileSystemTools.GET_ALLOWED_PATHS.value,
            description=TOOL_DESCRIPTION,
        )

    def _entrypoint(self, input: GetAllowedPathsInput) -> TextContent:
        config = ServerConfig()

        formatted = "\n".join(config.get_allowed_paths())

        return TextContent(
            type="text",
            text=formatted,
        )
