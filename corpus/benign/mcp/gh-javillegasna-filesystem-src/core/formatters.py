import os
import re


def normalize_line_endings(text: str) -> str:
    """
    Normalize line endings in a string to Unix-style (\n).
    """
    return text.replace("\r\n", "\n").replace("\r", "\n")


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace while preserving overall structure."""
    # Collapse multiple spaces into one
    result = re.sub(r"[ \t]+", " ", text)
    # Trim whitespace at line beginnings and endings
    result = "\n".join(line.strip() for line in result.split("\n"))
    return result


def get_line_indentation(line: str) -> str:
    """Extract the indentation (leading whitespace) from a line."""
    match = re.match(r"^(\s*)", line)
    return match.group(1) if match else ""


def expand_home(path: str) -> str:
    """
    Expand the user's home directory in a given path.
    """
    if path.startswith("~"):
        return os.path.expanduser(path)
    return path


def normalize_path(path: str) -> str:
    """
    Normalize a file path by expanding the user's home directory
    and normalizing line endings.
    """
    return os.path.normpath(path)
