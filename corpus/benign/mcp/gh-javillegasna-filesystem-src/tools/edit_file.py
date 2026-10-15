import difflib
from typing import Annotated

from mcp.types import TextContent
from pydantic import AfterValidator, BaseModel, Field

from core.enums import FileSystemTools
from core.formatters import get_line_indentation, normalize_line_endings
from core.types import BaseTool
from core.validations import validate_path


class EditOperation(BaseModel):
    old_text: str = Field(
        description="The text to be replaced",
        min_length=1,
        max_length=1000,
    )
    new_text: str = Field(
        description="The text to replace with",
        min_length=1,
        max_length=1000,
    )


class EditOptions(BaseModel):
    preserve_indentation: bool = True
    normalize_whitespace: bool = True


class EditFileInput(BaseModel):
    path: Annotated[str, AfterValidator(validate_path)]
    edits: list[EditOperation]
    dry_run: bool = Field(
        description="Preview changes using git-style diff format",
        default=False,
    )
    options: EditOptions = EditOptions()


class MatchResult(BaseModel):
    edit_index: int = 0
    matched: bool
    line_index: int = -1
    line_count: int = 0
    details: str = ""
    match_type: str


class EditFileOutput(BaseModel):
    match_results: list[MatchResult]
    file_path: str
    dry_run: bool
    success: bool = False
    message: str = ""
    diff: str = ""


TOOL_DESCRIPTION = f"""
    Edits a file on the filesystem by replacing specified text with new text.
    @Input:
        old_text: The text to be replaced.
        new_text: The text to replace with.
        dry_run: If true, preview changes using git-style diff format.
    @Output:
        text: A string containing the diff of the changes made to the file.
    @Schema: {EditFileInput.model_json_schema()}
"""


class EditFileTool(BaseTool):
    def __init__(self):
        super().__init__(
            inputSchema=EditFileInput.model_json_schema(),
            name=FileSystemTools.EDIT_FILE.value,
            description=TOOL_DESCRIPTION,
        )

    def find_exact_match(
        self,
        content: str,
        pattern: str,
        edit_index: int,
    ) -> MatchResult:
        """Find an exact string match in the content."""
        if pattern in content:
            lines_before = content[: content.find(pattern)].count("\n")
            line_count = pattern.count("\n") + 1
            return MatchResult(
                matched=True,
                edit_index=edit_index,
                line_index=lines_before,
                line_count=line_count,
                match_type="success",
                details="Exact match found",
            )
        return MatchResult(
            matched=False,
            edit_index=edit_index,
            match_type="failed",
            details="No exact match found",
        )

    def create_unified_diff(self, original: str, modified: str, file_path: str) -> str:
        """Create a unified diff between original and modified content."""
        original_lines = original.splitlines(True)
        modified_lines = modified.splitlines(True)

        diff_lines = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm="",
        )

        return "".join(diff_lines)

    def preserve_indentation(self, old_text: str, new_text: str) -> str:
        """Preserve the indentation pattern from old_text in new_text.

        This function adapts the indentation in the new text to match the pattern
        established in the old text, maintaining relative indentation between lines.
        """
        # Special case for markdown lists: don't modify indentation
        # if the new text has list markers
        if ("- " in new_text or "* " in new_text) and (
            "- " in old_text or "* " in old_text
        ):
            return new_text

        old_lines = old_text.split("\n")
        new_lines = new_text.split("\n")

        # Handle empty content
        if not old_lines or not new_lines:
            return new_text

        # Extract the base indentation from the first line of old text
        base_indent = (
            get_line_indentation(old_lines[0])
            if old_lines and old_lines[0].strip()
            else ""
        )

        # Pre-calculate indentation maps for efficiency
        old_indents = {
            i: get_line_indentation(line)
            for i, line in enumerate(old_lines)
            if line.strip()
        }
        new_indents = {
            i: get_line_indentation(line)
            for i, line in enumerate(new_lines)
            if line.strip()
        }

        # Calculate first line indentation length for relative adjustments
        first_new_indent_len = len(new_indents.get(0, "")) if new_indents else 0

        # Process each line with the appropriate indentation
        result_lines = []
        for i, new_line in enumerate(new_lines):
            # Empty lines remain empty
            if not new_line.strip():
                result_lines.append("")
                continue

            # Get current indentation in new text
            new_indent = new_indents.get(i, "")

            # Determine target indentation based on context
            if i < len(old_lines) and i in old_indents:
                # Matching line in old text - use its indentation
                target_indent = old_indents[i]
            elif i == 0:
                # First line gets base indentation
                target_indent = base_indent
            elif first_new_indent_len > 0:
                # Calculate relative indentation for other lines
                curr_indent_len = len(new_indent)

                # Default to base indent but look for better match from previous lines
                target_indent = base_indent

                # Find the closest previous line with appropriate indentation
                # to use as template
                for prev_i in range(i - 1, -1, -1):
                    if prev_i in old_indents and prev_i in new_indents:
                        prev_old = old_indents[prev_i]
                        prev_new = new_indents[prev_i]
                        if len(prev_new) <= curr_indent_len:
                            # Add spaces to match the relative indentation
                            relative_spaces = curr_indent_len - len(prev_new)
                            target_indent = prev_old + " " * relative_spaces
                            break
            else:
                # When first line has no indentation, use the new text's indentation
                target_indent = new_indent

            # Apply the calculated indentation
            result_lines.append(target_indent + new_line.lstrip())

        return "\n".join(result_lines)

    def apply_edits(
        self,
        content: str,
        edits: list[EditOperation],
        options: EditOptions,
    ) -> tuple[str, list[MatchResult], bool]:
        """
        Apply a list of edit operations to the content.

        Args:
            content: The original file content
            edits: List of edit operations
            options: Formatting options

        Returns:
            Tuple of (modified content, list of match results, changes_made flag)
        """

        # Normalize line endings
        normalized_content = normalize_line_endings(content)

        # Store match results for reporting
        match_results = []
        changes_made = False

        # Process each edit
        for i, edit in enumerate(edits):
            normalized_old = normalize_line_endings(edit.old_text)
            normalized_new = normalize_line_endings(edit.new_text)

            # Skip if the replacement text is identical to the old text
            if normalized_old == normalized_new:
                match_results.append(
                    MatchResult(
                        matched=True,
                        edit_index=i,
                        match_type="skipped",
                        details=(
                            "No change needed - text already matches desired state"
                        ),
                    )
                )
                continue

            # Check if the new_text is already in the content
            if (
                normalized_new in normalized_content
                and normalized_old not in normalized_content
            ):
                match_results.append(
                    MatchResult(
                        matched=True,
                        edit_index=i,
                        match_type="skipped",
                        details=(
                            "Edit already applied - content already in desired state"
                        ),
                    )
                )
                continue

            # Try exact match
            exact_match = self.find_exact_match(
                normalized_content, normalized_old, edit_index=i
            )

            # Process exact match (if found)
            if exact_match.matched:
                # For exact matches, find position in content
                start_pos = normalized_content.find(normalized_old)
                end_pos = start_pos + len(normalized_old)

                # Apply indentation preservation if requested
                if options.preserve_indentation:
                    normalized_new = self.preserve_indentation(
                        normalized_old, normalized_new
                    )

                # Apply the edit
                normalized_content = (
                    normalized_content[:start_pos]
                    + normalized_new
                    + normalized_content[end_pos:]
                )
                changes_made = True

            match_results.append(exact_match)

        return normalized_content, match_results, changes_made

    def _entrypoint(self, input: EditFileInput) -> TextContent:
        file_path = input.path
        # Read file content
        try:
            with open(file_path, encoding="utf-8") as f:
                original_content = f.read()
        except UnicodeDecodeError as e:
            raise ValueError(
                f"Unicode decode error while reading {file_path}: {str(e)}"
                f"File '{file_path}' contains invalid characters. "
                "Ensure it's a valid text file."
            ) from e
        except Exception:
            raise

        edit_operations = input.edits
        edit_options = input.options
        match_results = []

        # Apply edits
        modified_content, match_results, changes_made = self.apply_edits(
            original_content, edit_operations, edit_options
        )

        # Check for actual failures and already applied edits
        failed_matches = [r for r in match_results if r.match_type == "failed"]
        already_applied = [
            r
            for r in match_results
            if r.match_type == "skipped" and "already applied" in r.details
        ]

        # Handle common result cases
        result = EditFileOutput(
            match_results=match_results,
            file_path=file_path,
            dry_run=input.dry_run,
        )

        # Case 1: Failed matches
        if failed_matches:
            result.success = False
            result.message = "Failed to find exact match for one or more edits"
            return TextContent(type="text", text=result.model_dump_json(indent=2))

        # Case 2: No changes needed (already applied or identical content)
        if not changes_made or (
            already_applied and len(already_applied) == len(input.edits)
        ):
            result.success = True
            result.diff = ""
            result.message = "No changes needed - content already in desired state"

            return TextContent(type="text", text=result.model_dump_json(indent=2))

        # Case 3: Changes needed - create diff
        diff = self.create_unified_diff(original_content, modified_content, file_path)
        result.diff = diff
        result.success = True
        if input.dry_run and changes_made:
            return TextContent(type="text", text=result.model_dump_json(indent=2))
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(modified_content)
        except UnicodeEncodeError as e:
            result.success = False
            result.message = (
                f"Unicode encode error while writing to {file_path}: {str(e)}"
                "Content contains characters that cannot be encoded."
                " Please check the encoding."
            )

        except Exception as e:
            result.message = f"Error writing to file {file_path}: {str(e)}"
            result.success = False

        return TextContent(type="text", text=result.model_dump_json(indent=2))
