"""Shared text helpers for parsing local-model output."""


def strip_fences(raw: str) -> str:
    """Strip a leading/trailing triple-backtick code fence if present.

    Handles fences with or without a 'json' language tag. Returns the inner
    content stripped of surrounding whitespace. If no fence is present the
    input is returned stripped.
    """
    stripped = raw.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    # Drop the opening fence line (which may be "```" or "```json").
    lines = lines[1:]
    # Drop the closing fence line if present.
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()
