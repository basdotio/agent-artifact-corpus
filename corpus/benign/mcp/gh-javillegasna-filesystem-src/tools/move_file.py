import os
from typing import Annotated

from mcp.types import TextContent
from pydantic import AfterValidator, BaseModel

from core.enums import FileSystemTools
from core.types import BaseTool
from core.validations import validate_path


class MoveFileInput(BaseModel):
    source: Annotated[str, AfterValidator(validate_path)]
    destination: Annotated[
        str, 
        AfterValidator(
            lambda path: validate_path(path=path,validate_parent=True)
        ),
    ]


TOOL_DESCRIPTION = f"""
    Move or rename files and directories. Can move files between directories
    and rename them in a single operation. If the destination exists, the
    operation will fail. Works across different directories and can be used
    for simple renaming within the same directory. Both source and destination must be
    within allowed directories.
    @Input:
        source: origin path
        destination: destination path
    @Output:
        text: text with success message or error
    @Schema: {MoveFileInput.model_json_schema()}
"""


class MoveFileTool(BaseTool):
    def __init__(self):
        super().__init__(
            inputSchema=MoveFileInput.model_json_schema(),
            name=FileSystemTools.MOVE_FILE.value,
            description=TOOL_DESCRIPTION,
        )

    def _validate_path(self, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Path not found: {path}")
        return os.path.abspath(path)

    def _entrypoint(self, input: MoveFileInput) -> TextContent:
        source_path = self._validate_path(input.source)
        parent_path = os.path.dirname(input.destination)
        self._validate_path(parent_path)
        os.rename(source_path, input.destination)

        return TextContent(
            type="text",
            text=f"Successfully moved {input.source} to {input.destination}",
        )
