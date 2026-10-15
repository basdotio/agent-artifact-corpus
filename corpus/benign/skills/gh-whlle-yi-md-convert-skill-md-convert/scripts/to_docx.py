#!/usr/bin/env python3
"""to_docx.py — Markdown → Word(.docx)。

管线（生成模板 → pandoc → 后处理 → 字体内嵌）在 docx_lib.py；
命令形态与参数见 references/params.md。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common
import docx_lib


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="to_docx.py",
        description="高质量 Markdown → Word(.docx)（md-convert）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    common.add_core_args(p, common.__version__)
    common.add_style_args(p)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return common.standard_main(args, docx_lib.convert_docx,
                                default_ext="docx", version=common.__version__)


if __name__ == "__main__":
    sys.exit(main())
