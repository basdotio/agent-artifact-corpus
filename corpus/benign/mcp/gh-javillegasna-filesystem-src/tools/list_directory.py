import os
from typing import Annotated

from mcp.types import TextContent
from pydantic import AfterValidator, BaseModel

from core.enums import FileSystemTools
from core.types import BaseTool
from core.validations import validate_path


class ListDirectoryInput(BaseModel):
    path: Annotated[str, AfterValidator(validate_path)]


TOOL_DESCRIPTION = f"""
    Get a detailed listing of all files and directories in a specified path.
    Results clearly distinguish between files and directories with [FILE] and [DIR]
    prefixes. This tool is essential for understanding directory structure and 
    finding specific files within a directory. Only works within allowed directories.
    @Input:
        path: The path to the file to read.
    @Output:
        text: text with list of files/dir names.
    @Schema: {ListDirectoryInput.model_json_schema()}
"""


class ListDirectoryTool(BaseTool):
    def __init__(self):
        super().__init__(
            inputSchema=ListDirectoryInput.model_json_schema(),
            name=FileSystemTools.LIST_DIRECTORY.value,
            description=TOOL_DESCRIPTION,
        )

    def _entrypoint(self, input: ListDirectoryInput) -> TextContent:
        entries = os.scandir(input.path)

        formatted = "\n".join(
            f"[DIR] {entry.name}" if entry.is_dir() else f"[FILE] {entry.name}"
            for entry in entries
        )

        return TextContent(
            type="text",
            text=formatted,
        )
