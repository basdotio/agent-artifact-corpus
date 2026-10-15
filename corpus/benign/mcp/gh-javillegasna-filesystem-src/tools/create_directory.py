import os
from typing import Annotated

from mcp.types import TextContent
from pydantic import AfterValidator, BaseModel

from core.enums import FileSystemTools
from core.types import BaseTool
from core.validations import validate_path


class CreateDirectoryInput(BaseModel):
    path: Annotated[
        str, 
        AfterValidator(
            lambda path: validate_path(path=path, validate_parent=True)
        ),
    ]


TOOL_DESCRIPTION = f"""
    Create a new directory or ensure a directory exists. Can create multiple
    directories at once. If the directory already exists, this operation will succeed 
    silently. Perfect for setting up directory structures for projects or ensuring
    that required directories are present before performing other operations.
    @Input:
        input: The path to the file to read.
    @Output:
        text: Success or error message .
    @Schema: {CreateDirectoryInput.model_json_schema()}
"""


class CreateDirectoryTool(BaseTool):
    def __init__(self):
        super().__init__(
            inputSchema=CreateDirectoryInput.model_json_schema(),
            name=FileSystemTools.CREATE_DIRECTORY.value,
            description=TOOL_DESCRIPTION,
        )

    def _entrypoint(self, input: CreateDirectoryInput) -> TextContent:
        os.makedirs(input.path, exist_ok=True)
        return TextContent(
            type="text",
            text=f"Directory created successfully at {input.path}",
        )
