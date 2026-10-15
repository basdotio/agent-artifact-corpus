"""Gỡ các khối quảng cáo đã hết hạn khỏi README.md.

Khối có dạng:
    <!-- AD:START until=2026-10-05T23:55:00+07:00 -->
    ...
    <!-- AD:END -->
Quá thời điểm `until` thì xoá cả khối (kèm dòng trống ngay sau). In "changed" nếu có sửa.
"""
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "README.md")
text = path.read_text(encoding="utf-8")
now = datetime.now(timezone.utc)
pattern = re.compile(r"<!-- AD:START until=(\S+) -->.*?<!-- AD:END -->\n?\n?", re.S)


def drop(m: "re.Match[str]") -> str:
    try:
        until = datetime.fromisoformat(m.group(1))
    except ValueError:
        return m.group(0)              # ngày sai định dạng: giữ nguyên, không xoá nhầm
    return "" if now >= until else m.group(0)


new = pattern.sub(drop, text)
if new != text:
    path.write_text(new, encoding="utf-8")
    print("changed")
