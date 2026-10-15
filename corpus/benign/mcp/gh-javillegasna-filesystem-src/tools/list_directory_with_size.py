import datetime
import os
from enum import Enum
from typing import Annotated

from mcp.types import TextContent
from pydantic import AfterValidator, BaseModel

from core.enums import FileSystemTools
from core.types import BaseTool
from core.validations import validate_path


class SortByEnum(str, Enum):
    file_name = "file_name"
    size = "size"


class ListDirectoryWithSizeInput(BaseModel):
    path: Annotated[str, AfterValidator(validate_path)]
    sort_by: SortByEnum = SortByEnum.file_name


TOOL_DESCRIPTION = f"""
    Get a detailed listing of all files and directories in a specified path, including 
    sizes. Results clearly distinguish between files and directories with [FILE] 
    and [DIR] prefixes. This tool is useful for understanding directory structure and
    finding specific files within a directory. Only works within allowed directories.
    @Input:
        path: The path to the file to read.
        sort_by: string literal to file_name or size
    @Output:
        text: with sorted dir/files names plus summary.
    @Schema: {ListDirectoryWithSizeInput.model_json_schema()}
"""


class ListDirectoryWithSizeTool(BaseTool):
    def __init__(self):
        super().__init__(
            inputSchema=ListDirectoryWithSizeInput.model_json_schema(),
            name=FileSystemTools.LIST_DIRECTORY_WITH_SIZE.value,
            description=TOOL_DESCRIPTION,
        )

    def _format_size(self, size_bytes: float):
        """Format size in bytes to human-readable form."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    def _sort_entries(self, detailed_entries: list[dict], sort_by: SortByEnum):
        if sort_by == SortByEnum.size:
            return sorted(detailed_entries, key=lambda e: e["size"], reverse=True)

        return sorted(detailed_entries, key=lambda e: e["name"].lower())

    def _format_entry(self, entry_path: str, entry: os.DirEntry[str]):
        try:
            stats = os.stat(entry_path)
            return {
                "name": entry.name,
                "isDirectory": entry.is_dir(),
                "size": stats.st_size,
                "mtime": datetime.datetime.fromtimestamp(stats.st_mtime),
            }
        except Exception:
            return {
                "name": entry.name,
                "isDirectory": entry.is_dir(),
                "size": 0,
                "mtime": datetime.datetime.fromtimestamp(0),
            }

    def _format_output(self, sorted_entries: list[dict]):
        formatted_entries = []
        for entry in sorted_entries:
            kind = "[DIR]" if entry["isDirectory"] else "[FILE]"
            name_padded = entry["name"].ljust(30)
            size_str = ""
            if not entry["isDirectory"]:
                size_str = self._format_size(entry["size"]).rjust(10)

            formatted_entries.append(f"{kind} {name_padded}{size_str}")
        return formatted_entries

    def _entrypoint(self, input: ListDirectoryWithSizeInput) -> TextContent:
        valid_path = input.path
        with os.scandir(valid_path) as entries:
            detailed_entries = [
                self._format_entry(
                    os.path.join(valid_path, entry.name),
                    entry,
                )
                for entry in entries
            ]

        sorted_entries = self._sort_entries(
            detailed_entries=detailed_entries, 
            sort_by=input.sort_by
        )
        # Format output
        formatted_entries = self._format_output(sorted_entries)

        # Summary
        total_files = sum(1 for e in detailed_entries if not e["isDirectory"])
        total_dirs = sum(1 for e in detailed_entries if e["isDirectory"])
        total_size = sum(e["size"] for e in detailed_entries if not e["isDirectory"])

        summary = [
            "",
            f"Total: {total_files} files, {total_dirs} directories",
            f"Combined size: {self._format_size(total_size)}",
        ]
        return TextContent(
            type="text",
            text="\n".join(formatted_entries + summary),
        )
