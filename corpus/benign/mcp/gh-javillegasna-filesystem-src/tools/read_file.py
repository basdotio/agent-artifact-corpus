from typing import Annotated

from mcp.types import TextContent
from pydantic import AfterValidator, BaseModel

from core.enums import FileSystemTools
from core.types import BaseTool
from core.validations import validate_path


class ReadFileInput(BaseModel):
    path: Annotated[str, AfterValidator(validate_path)]

TOOL_DESCRIPTION = f"""
    Reads a file from the filesystem and returns its content.
    @Input:
        input: The path to the file to read.
    @Output:
        text: The content of the file.
    @Schema: {ReadFileInput.model_json_schema()}
"""

class ReadFileTool(BaseTool):
    def __init__(self):
        super().__init__(
            inputSchema=ReadFileInput.model_json_schema(),
            name=FileSystemTools.READ_FILE.value,
            description=TOOL_DESCRIPTION,
        )

    def _entrypoint(self, input: ReadFileInput) -> TextContent:
        with open(input.path, encoding="utf-8") as file:
            content = file.read()
        return TextContent(type="text", text=f"{input.path}:\n{content}")
   