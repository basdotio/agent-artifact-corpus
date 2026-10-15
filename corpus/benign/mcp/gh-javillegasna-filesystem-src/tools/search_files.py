import os
from fnmatch import fnmatch
from typing import Annotated

from mcp.types import TextContent
from pydantic import AfterValidator, BaseModel

from core.enums import FileSystemTools
from core.types import BaseTool
from core.validations import validate_path


class SearchFilesInput(BaseModel):
    path: Annotated[str, AfterValidator(validate_path)]
    pattern: str
    exclude_patterns: list[str] = []


TOOL_DESCRIPTION = f"""
    Recursively search for files and directories matching a pattern.
    Searches through all subdirectories from the starting path. The search
    is case-insensitive and matches partial names. Returns full paths to all
    matching items. Great for finding files when you don't know their exact location.
    Only searches within allowed directories."
    @Input:
        path: Root path to stat searching
        pattern: partial path to search
        exclude_patterns: paths to exclude searching
    @Output:
        text: text with success message or error
    @Schema: {SearchFilesInput.model_json_schema()}
"""


class SearchFilesTool(BaseTool):
    def __init__(self):
        super().__init__(
            inputSchema=SearchFilesInput.model_json_schema(),
            name=FileSystemTools.SEARCH_FILES.value,
            description=TOOL_DESCRIPTION,
        )

    def _validate_path(self, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Path not found: {path}")
        return os.path.abspath(path)

    def _search_files(
        self,
        root_path: str,
        pattern: str,
        exclude_patterns: list[str],
    ):
        results = []

        def search(current_path: str):
            try:
                entries = os.scandir(current_path)
            except Exception:
                return  # Skip unreadable directories

            with entries:
                for entry in entries:
                    full_path = os.path.join(current_path, entry.name)

                    try:
                        self._validate_path(full_path)
                        relative_path = os.path.relpath(full_path, root_path)

                        # Handle exclusion patterns (converted to glob-style)
                        should_exclude = any(
                            fnmatch(relative_path, p) or fnmatch(full_path, p)
                            for p in exclude_patterns
                        )
                        if should_exclude:
                            continue

                        if pattern.lower() in entry.name.lower():
                            results.append(full_path)

                        if entry.is_dir():
                            search(full_path)
                    except Exception:
                        continue  # Skip errors on individual entries

        search(root_path)
        return results
        

    def _entrypoint(self, input: SearchFilesInput) -> TextContent:
        root_path = self._validate_path(input.path)
        results = self._search_files(
            root_path=root_path,
            pattern=input.pattern,
            exclude_patterns=input.exclude_patterns,
        )


        return TextContent(
            type="text",
            text= "\n".join(results) if len(results) >0 else "No matches found",
        )