"""Markdown helpers shared by all tools. Output is fed to an LLM, so everything here is about token economy."""

from __future__ import annotations

from typing import Iterable, Sequence

LINE_CLIP = 160


def clip(text: str, limit: int = LINE_CLIP) -> str:
    text = text.replace("\t", "    ").rstrip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def code_span(text: str) -> str:
    """Inline code that survives backticks inside the content."""
    text = clip(text.strip())
    if "`" in text:
        return f"`` {text} ``"
    return f"`{text}`"


def error_card(title: str, message: str, hint: str | None = None) -> str:
    out = f"### ❌ {title}\n{message}"
    if hint:
        out += f"\n\n💡 {hint}"
    return out


def truncate_list(items: Sequence[str], limit: int, noun: str = "results", hint: str = "") -> list[str]:
    if len(items) <= limit:
        return list(items)
    extra = len(items) - limit
    note = f"_…and {extra} more {noun}"
    note += f". {hint}_" if hint else "._"
    return list(items[:limit]) + [note]


def numbered_code(lines: Sequence[str], start_line: int, mark: Iterable[int] = (), width: int | None = None) -> list[str]:
    marks = set(mark)
    last = start_line + len(lines) - 1
    width = width or len(str(max(last, 1)))
    out = []
    for i, text in enumerate(lines):
        n = start_line + i
        prefix = ">" if n in marks else " "
        out.append(f"{prefix}{str(n).rjust(width)} | {clip(text, 200)}")
    return out


def compress_ranges(numbers: Iterable[int], max_parts: int = 0) -> str:
    nums = sorted(set(numbers))
    if not nums:
        return ""
    parts: list[str] = []
    start = prev = nums[0]
    for n in nums[1:]:
        if n == prev + 1:
            prev = n
            continue
        parts.append(f"L{start}" if start == prev else f"L{start}-{prev}")
        start = prev = n
    parts.append(f"L{start}" if start == prev else f"L{start}-{prev}")
    if max_parts and len(parts) > max_parts:
        return ", ".join(parts[:max_parts]) + f", … (+{len(parts) - max_parts} more ranges)"
    return ", ".join(parts)


def enforce_budget(text: str, max_chars: int) -> str:
    """Cut at a line boundary under max_chars and keep code fences balanced."""
    if len(text) <= max_chars:
        return text
    cut = text.rfind("\n", 0, max_chars)
    if cut <= 0:
        cut = max_chars
    kept = text[:cut]
    if kept.count("```") % 2 == 1:
        kept += "\n```"
    return kept + f"\n\n_…output truncated at {max_chars} characters to protect the context budget. Narrow the query for more._"


def plural(n: int, word: str, suffix: str = "s") -> str:
    return f"{n} {word}{'' if n == 1 else suffix}"
