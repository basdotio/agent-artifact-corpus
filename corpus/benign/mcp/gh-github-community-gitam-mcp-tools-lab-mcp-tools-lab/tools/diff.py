"""Line-based text comparison."""

import difflib


def compare_text(before: str, after: str) -> dict:
    """Return a unified diff and counts; ignore line-ending style and final newline."""
    old_lines, new_lines = before.splitlines(), after.splitlines()
    added = removed = 0
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)
    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if tag in {"replace", "delete"}:
            removed += old_end - old_start
        if tag in {"replace", "insert"}:
            added += new_end - new_start
    diff = "\n".join(difflib.unified_diff(old_lines, new_lines, fromfile="before", tofile="after", lineterm=""))
    return {"added_lines": added, "removed_lines": removed, "diff": diff}
