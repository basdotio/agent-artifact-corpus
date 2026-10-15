#!/usr/bin/env python3
"""to_pdf.py — Markdown → PDF，唯一引擎为 XeLaTeX。

排版规范与 docx 一致（宋体 + Times New Roman、Heavy 强调、A4、首行缩进 2 字符），
由动态生成的 XeLaTeX 导言保证；公式与三线表（booktabs）质量最佳，
输出跨机器一致。命令形态与参数见 references/params.md；
学术论文场景见 references/scenario-academic.md。
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="to_pdf.py",
        description="高质量 Markdown → PDF（XeLaTeX 引擎，md-convert）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    common.add_core_args(p, common.__version__)
    common.add_style_args(p)
    return p


def build_latex_header(args) -> str:
    """动态生成 XeLaTeX 导言（与 docx 排版规范一致）。"""
    lines: list[str] = []
    lines.append(f"\\setmainfont{{{args.latin_font}}}")
    lines.append("\\usepackage{xeCJK}")
    lines.append("\\usepackage{xeCJKfntef}")
    # pandoc 用 soul 实现删除线（\st），soul 不支持中文；
    # 改用 ulem 的 \sout（xeCJKfntef 已使其支持中文）
    lines.append("\\usepackage[normalem]{ulem}")
    lines.append("\\providecommand{\\st}[1]{\\sout{#1}}")
    emph_file = Path(args.emph_font_file) if args.emph_font_file else None
    if args.no_heavy or emph_file is None or not emph_file.is_file():
        lines.append(f"\\setCJKmainfont{{{args.cjk_font}}}[AutoFakeBold=2.5]")
        lines.append(
            f"\\IfFontExistsTF{{{args.heading_cjk_font}}}"
            f"{{\\setCJKfamilyfont{{emphsong}}{{{args.heading_cjk_font}}}}}"
            f"{{\\setCJKfamilyfont{{emphsong}}{{{args.cjk_font}}}[AutoFakeBold=2.5]}}"
        )
    else:
        font_dir = emph_file.parent.as_posix()
        font_name = emph_file.name
        # 主字体走系统族名查找；Path= 一旦出现，fontspec 会把主字体当文件名找，
        # 因此 Heavy 文件只能挂在 emphsong 家族上（供 \key 强调），不混入主字体。
        lines.append(f"\\setCJKmainfont{{{args.cjk_font}}}[AutoFakeBold=2.5]")
        lines.append(
            f"\\setCJKfamilyfont{{emphsong}}{{{font_name}}}[Path={font_dir}/, BoldFont={font_name}]"
        )
    lines.append("\\newcommand{\\key}[1]{{\\CJKfamily{emphsong}\\bfseries #1}}")
    # 数学字体与正文同风格（Times 系）；pandoc 的 xelatex 模板已加载 unicode-math
    lines.append(
        "\\IfFontExistsTF{STIX Two Math}{\\setmathfont{STIX Two Math}}"
        "{\\IfFontExistsTF{TeX Gyre Termes Math}{\\setmathfont{TeX Gyre Termes Math}}{}}"
    )
    # 首行缩进 2 字符（2 个汉字宽度 = 2em，与 docx 的 firstLineChars=200 对应）
    lines.append("\\AtBeginDocument{\\setlength{\\parindent}{2em}}")
    return "\n".join(lines) + "\n"


LUA_STRIKEOUT = """\
-- soul 宏包已从 TeX Live 2023 移除且不支持中文；
-- 把删除线改写为 ulem 的 \\sout（配合 xeCJKfntef 支持中文），避免加载 soul。
function Strikeout(el)
  return pandoc.RawInline("tex", "\\\\sout{" .. pandoc.utils.stringify(el) .. "}")
end
"""


def convert_pdf(src: Path, out: Path, args, tmpdir: Path) -> Path:
    if not shutil.which("xelatex"):
        raise common.ConvertError(
            "未找到 xelatex。请安装 TeX Live / MiKTeX（建议含中文支持），"
            "见 references/troubleshooting.md。"
        )
    header = tmpdir / "header.tex"
    header.write_text(build_latex_header(args), encoding="utf-8")
    lua = tmpdir / "strikeout.lua"
    lua.write_text(LUA_STRIKEOUT, encoding="utf-8")
    pandoc_args = [
        str(src), "-f", args.reader,
        "--pdf-engine", "xelatex",
        "-H", str(header),
        "--lua-filter", str(lua),
        "-V", "geometry:top=2.54cm", "-V", "geometry:bottom=2.54cm",
        "-V", "geometry:left=3.17cm", "-V", "geometry:right=3.17cm",
        "-V", f"linestretch={args.line_spacing}",
        "-V", "colorlinks=true", "-V", "linkcolor=black",
        "-V", "urlcolor=black", "-V", "citecolor=black",
        "--resource-path", str(src.parent),
        "--dpi", str(args.dpi),
        "-M", f"lang={args.lang}",
        "-o", str(out),
    ]
    if args.font_size in (10.0, 11.0, 12.0):
        pandoc_args += ["-V", f"fontsize={int(args.font_size)}pt"]
    if not args.highlight:
        pandoc_args.append("--no-highlight")
    pandoc_args += common.citeproc_args(args)
    if args.toc:
        pandoc_args += ["--toc", "--toc-depth", str(args.toc_depth),
                        "-M", "toc-title=目录"]
    if args.number_sections:
        pandoc_args += ["--number-sections"]
    common.run_pandoc(pandoc_args, args.verbose)
    common.log(f"pdf 完成（XeLaTeX）：{out.name}")
    return out


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return common.standard_main(args, convert_pdf,
                                default_ext="pdf", version=common.__version__)


if __name__ == "__main__":
    sys.exit(main())
