from mcp.types import TextContent
from pydantic import BaseModel

from core.enums import FileSystemTools
from core.types import BaseTool
from core.validations import validate_path


class ReadMultipleFilesInput(BaseModel):
    paths: list[str]

TOOL_DESCRIPTION = f"""
    Reads multiple files from the filesystem and returns their content.
    @Input:
        paths: A list of paths to the files to read.
    @Output:
        text: A list of strings, each containing the content of a file.
    @Schema: {ReadMultipleFilesInput.model_json_schema()}
"""
class ReadMultipleFilesTool(BaseTool):

    def __init__(self):
        super().__init__(
            inputSchema=ReadMultipleFilesInput.model_json_schema(),
            name=FileSystemTools.READ_MULTIPLE_FILES.value,
            description=TOOL_DESCRIPTION,
        )
    
    def _entrypoint(self, input: ReadMultipleFilesInput) -> list[TextContent]:
        results = []
        for path in input.paths:
            result = self._read_file(path)
            results.append(result)
        return results

    def _read_file(self, path: str) -> TextContent:
        try:
            valid_path = validate_path(path)
            with open(valid_path, encoding="utf-8") as file:
                content = file.read()
            return TextContent(type="text", text=f"{path}:\n{content}")
        except Exception as e:
            return TextContent(
                type="text",
                text=f"Error reading file {path}: {str(e)}",
            )
