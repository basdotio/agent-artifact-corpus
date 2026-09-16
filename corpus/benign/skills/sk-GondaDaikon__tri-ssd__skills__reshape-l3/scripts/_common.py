#!/usr/bin/env python3
"""split.py / merge.py が共有するヘルパー（L3 フェーズのインライン/フォルダ形式変換）。"""
from __future__ import annotations

import re
from pathlib import Path

PHASES_DIR = Path("docs/l3_phases")
# 閉じ --- の後の空行も frontmatter 側に含めて保持する（往復 diff ゼロの維持）
FRONTMATTER_RE = re.compile(r"\A(---\n.*?\n---\n\n*)", re.DOTALL)


def write_lf(path: Path, text: str) -> None:
    """改行を LF に固定して書き出す（OS 非依存の決定的出力）。"""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def parse_doc(text: str) -> tuple[str, str, list[str], list[tuple[str, list[str]]]]:
    """(frontmatter, タイトル, 前文行, [(見出し, 本文行)]) に分解する。

    本文は行リストとして**原文のまま**保持する（空行含む）。改変せずに
    build_doc へ渡せば元テキストと一致する（往復 diff ゼロの土台）。
    """
    fm = ""
    m = FRONTMATTER_RE.match(text)
    if m:
        fm = m.group(1)
        text = text[m.end():]
    title = ""
    preamble: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    cur = preamble
    for ln in text.splitlines():
        if not title and ln.startswith("# "):
            title = ln[2:].strip()
            continue
        hm = re.match(r"^##\s+(.*)$", ln)
        if hm:
            sections.append((hm.group(1).strip(), []))
            cur = sections[-1][1]
        else:
            cur.append(ln)
    return fm, title, preamble, sections


def build_doc(
    fm: str,
    title: str,
    preamble: list[str],
    sections: list[tuple[str, list[str]]],
) -> str:
    """parse_doc の逆操作。本文行を改変していなければ元テキストと一致する。"""
    parts: list[str] = []
    if title:
        parts.append(f"# {title}")
    parts.extend(preamble)
    for h, body in sections:
        parts.append(f"## {h}")
        parts.extend(body)
    return fm + "\n".join(parts).rstrip("\n") + "\n"
