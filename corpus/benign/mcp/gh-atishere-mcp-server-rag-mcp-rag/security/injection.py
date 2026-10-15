"""Prompt injection detection."""

import re
from typing import Final

# ============================================================
# INJECTION PATTERNS
# ============================================================
# Danh sách các pattern thường gặp trong prompt injection.
# Mỗi pattern là regex — dùng re.search để tìm trong text.

INJECTION_PATTERNS: Final[list[re.Pattern[str]]] = [
    # ----- Instruction override -----
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)", re.IGNORECASE),
    re.compile(r"forget\s+(everything|all|previous)", re.IGNORECASE),
    re.compile(r"override\s+(your\s+)?(instructions?|rules?|prompt)", re.IGNORECASE),

    # ----- Role change -----
    re.compile(r"you\s+are\s+now\s+(a\s+)?(hacker|admin|root|developer)", re.IGNORECASE),
    re.compile(r"act\s+as\s+(a\s+)?(hacker|admin|root)", re.IGNORECASE),
    re.compile(r"pretend\s+(to\s+be|you\s+are)", re.IGNORECASE),

    # ----- System prompt leak -----
    re.compile(r"(print|show|reveal|repeat)\s+(your\s+)?(system\s+)?(prompt|instructions?)", re.IGNORECASE),
    re.compile(r"what\s+(are|is)\s+your\s+(system\s+)?(prompt|instructions?)", re.IGNORECASE),

    # ----- Delimiter injection -----
    re.compile(r"\[\s*SYSTEM\s*\]", re.IGNORECASE),
    re.compile(r"\[\s*INST\s*\]", re.IGNORECASE),
    re.compile(r"<\|im_start\|>", re.IGNORECASE),
    re.compile(r"<\|im_end\|>", re.IGNORECASE),
    re.compile(r"<\|system\|>", re.IGNORECASE),
    re.compile(r"###\s*(system|instruction)", re.IGNORECASE),

    # ----- Command injection -----
    re.compile(r"(execute|run|eval)\s+(this\s+)?(command|code|script)", re.IGNORECASE),
    re.compile(r"\brm\s+-rf\b"),
    re.compile(r"\bdrop\s+table\b", re.IGNORECASE),
    re.compile(r"\bdelete\s+from\b", re.IGNORECASE),
    re.compile(r"\btruncate\s+table\b", re.IGNORECASE),
]


def detect_injection(text: str) -> bool:
    """Phát hiện prompt injection trong text.

    Args:
        text: Text cần kiểm tra (query, chunk content, ...)

    Returns:
        True nếu phát hiện injection, False nếu an toàn
    """
    if not text:
        return False

    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            return True

    return False


def get_matched_patterns(text: str) -> list[str]:
    """Lấy danh sách patterns match (dùng để debug).

    Args:
        text: Text cần kiểm tra

    Returns:
        Danh sách regex patterns đã match
    """
    if not text:
        return []

    matched: list[str] = []
    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            matched.append(pattern.pattern)

    return matched


def sanitize_injection(text: str) -> str:
    """Loại bỏ các đoạn có injection (thay bằng [REDACTED]).

    Args:
        text: Text cần sanitize

    Returns:
        Text đã được làm sạch
    """
    if not text:
        return text

    result = text
    for pattern in INJECTION_PATTERNS:
        result = pattern.sub("[REDACTED]", result)

    return result
