import json
import os
from typing import Annotated

from mcp.types import TextContent
from pydantic import AfterValidator, BaseModel

from core.enums import FileSystemTools
from core.types import BaseTool
from core.validations import validate_path


class DirectoryTreeInput(BaseModel):
    path: Annotated[str, AfterValidator(validate_path)]


class TreeEntry(BaseModel):
    file_name: str
    type: str
    children: list["TreeEntry"] = []


TOOL_DESCRIPTION = f"""
    Get a recursive tree view of files and directories as a JSON structure.
    Each entry includes 'name', 'type' (file/directory), and 'children' for directories.
    Files have no children array, while directories always have a children array 
    (which may be empty). The output is formatted with 2-space indentation for 
    readability. Only works within allowed directories.
    @Input:
        path: The path to the file to read.
    @Output:
        text: text with directory tree
    @Schema: {DirectoryTreeInput.model_json_schema()}
"""


class DirectoryTreeTool(BaseTool):
    def __init__(self):
        super().__init__(
            inputSchema=DirectoryTreeInput.model_json_schema(),
            name=FileSystemTools.DIRECTORY_TREE.value,
            description=TOOL_DESCRIPTION,
        )

    def _validate_path(self, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Path not found: {path}")
        return os.path.abspath(path)

    def _build_tree(self, current_path) -> list[TreeEntry]:
        valid_path = self._validate_path(current_path)

        result = []
        with os.scandir(valid_path) as entries:
            for entry in entries:
                entry_data = TreeEntry(
                    file_name=entry.name,
                    type="directory" if entry.is_dir() else "file",
                )

                if entry.is_dir():
                    sub_path = os.path.join(current_path, entry.name)
                    entry_data.children.extend(self._build_tree(sub_path))
                result.append(entry_data)

        return result

    def _entrypoint(self, input: DirectoryTreeInput) -> TextContent:
        tree_data = self._build_tree(input.path)
        return TextContent(
            type="text",
            text=json.dumps(
                [entry.model_dump(exclude_defaults=True) for entry in tree_data],
                indent=2,
            ),
        )
