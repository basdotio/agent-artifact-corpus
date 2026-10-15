#!/usr/bin/env python3
"""to_html.py — Markdown → 独立单文件 HTML。

样式（按字符分层的中西文字体、三线表、打印对齐 A4）在 assets/html-style.css，
经 pandoc --embed-resources 内嵌；公式输出 MathML。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="to_html.py",
        description="高质量 Markdown → 独立单文件 HTML（md-convert）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    common.add_core_args(p, common.__version__)
    return p


def extract_title(src: Path) -> str:
    """取 YAML front matter 的 title，否则第一个一级标题，否则文件名。"""
    try:
        text = src.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = src.read_text(encoding="utf-16")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if m:
        tm = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', m.group(1), re.M)
        if tm:
            return tm.group(1)
    fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if not fence:
            hm = re.match(r"^#\s+(.+?)\s*#*\s*$", line)
            if hm:
                return hm.group(1)
    return src.stem


def convert_html(src: Path, out: Path, args, tmpdir: Path) -> Path:
    css = Path(__file__).resolve().parent.parent / "assets" / "html-style.css"
    pandoc_args = [
        str(src), "-f", args.reader, "-t", "html5",
        "--standalone", "--embed-resources", "--mathml",
        "-M", f"title={extract_title(src)}",
        "-M", f"lang={args.lang}",
        "--resource-path", str(src.parent),
        "--dpi", str(args.dpi),
        "-o", str(out),
    ]
    if css.is_file():
        pandoc_args += ["-c", str(css.resolve())]
    if not args.highlight:
        pandoc_args.append("--no-highlight")
    pandoc_args += common.citeproc_args(args)
    if args.toc:
        pandoc_args += ["--toc", "--toc-depth", str(args.toc_depth)]
    common.run_pandoc(pandoc_args, args.verbose)
    common.log(f"html 完成：{out.name}")
    return out


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return common.standard_main(args, convert_html,
                                default_ext="html", version=common.__version__)


if __name__ == "__main__":
    sys.exit(main())
