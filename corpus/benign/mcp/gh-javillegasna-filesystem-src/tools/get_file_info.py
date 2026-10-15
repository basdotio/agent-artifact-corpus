import os
from datetime import datetime
from typing import Annotated

from mcp.types import TextContent
from pydantic import AfterValidator, BaseModel

from core.enums import FileSystemTools
from core.types import BaseTool
from core.validations import validate_path


class GetFileInfoInput(BaseModel):
    path: Annotated[str, AfterValidator(validate_path)]


class FileStats(BaseModel):
    size:float
    created: datetime
    modified: datetime
    accessed: datetime
    is_directory: bool
    is_file: bool
    permissions: str

TOOL_DESCRIPTION = f"""
    Retrieve detailed metadata about a file or directory. Returns comprehensive
    information including size, creation time, last modified time, permissions,
    and type. This tool is perfect for understanding file characteristics
    without reading the actual content. Only works within allowed directories.
    @Input:
        path: file path to get stats.
    @Output:
        text: stats of file/dir including permissions.
    @Schema: {GetFileInfoInput.model_json_schema()}
"""


class GetFileInfoTool(BaseTool):
    def __init__(self):
        super().__init__(
            inputSchema=GetFileInfoInput.model_json_schema(),
            name=FileSystemTools.GET_FILE_INFO.value,
            description=TOOL_DESCRIPTION,
        )

    def _entrypoint(self, input: GetFileInfoInput) -> TextContent:
        raw_stats = os.stat(input.path)
        file_stats = FileStats(
            size=raw_stats.st_size,
            created=datetime.fromtimestamp(raw_stats.st_ctime),
            modified=datetime.fromtimestamp(raw_stats.st_mtime),
            accessed=datetime.fromtimestamp(raw_stats.st_atime),
            is_directory=os.path.isdir(input.path),
            is_file=os.path.isfile(input.path),
            permissions=oct(raw_stats.st_mode)[-3:]
        )

        return TextContent(
            type="text",
            text=file_stats.model_dump_json(indent=2),
        )
