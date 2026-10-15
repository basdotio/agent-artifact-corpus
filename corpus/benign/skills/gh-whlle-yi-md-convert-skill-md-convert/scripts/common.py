#!/usr/bin/env python3
"""common.py — to_docx / to_pdf / to_html 三个入口脚本的共享层。

包含：公共常量、ConvertError、pandoc 调用封装、citeproc 参数透传、
公共命令行参数组（core / style）、输出路径解析与标准 main 流程。
本文件不含任何管线逻辑——管线分别在 to_*.py 与 docx_lib.py。
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

__version__ = "0.2.0"

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

DEFAULT_FROM = "markdown+east_asian_line_breaks"
DEFAULT_HEAVY_FONT = "Noto Serif SC Heavy X"
DEFAULT_HEAVY_FONT_FILE = Path.home() / ".zcode" / "fonts" / "NotoSerifSC-HeavyX.ttf"

FORMATS = ("docx", "pdf", "html")


class ConvertError(RuntimeError):
    """带用户可读信息的转换错误。"""


def log(msg: str) -> None:
    print(f"[md-convert] {msg}", file=sys.stderr)


def _reconfigure_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# pandoc
# ---------------------------------------------------------------------------

def require_pandoc() -> None:
    if shutil.which("pandoc") is None:
        raise ConvertError(
            "未找到 pandoc。请安装后重试（见 references/troubleshooting.md）：\n"
            "  Windows: winget install JohnMacFarlane.Pandoc  或到 https://pandoc.org/installing.html 下载\n"
            "  macOS:   brew install pandoc\n"
            "  Linux:   sudo apt install pandoc"
        )


def run_pandoc(args: list[str], verbose: bool = False) -> None:
    cmd = ["pandoc", *args]
    if verbose:
        log("执行: " + " ".join(f'"{a}"' if " " in a else a for a in cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise ConvertError(f"pandoc 转换失败：\n{proc.stderr.strip() or proc.stdout.strip()}")
    if verbose and proc.stderr.strip():
        log("pandoc: " + proc.stderr.strip())


def citeproc_args(args) -> list[str]:
    """参考文献处理参数（三条管线共用）；未指定文献库时依赖文档 metadata。"""
    if not getattr(args, "citeproc", False):
        return []
    out = ["--citeproc"]
    if getattr(args, "bibliography", None):
        out += ["--bibliography", str(args.bibliography)]
    if getattr(args, "csl", None):
        out += ["--csl", str(args.csl)]
    return out


# ---------------------------------------------------------------------------
# 公共命令行参数组
# ---------------------------------------------------------------------------

def add_core_args(p, version: str) -> None:
    """所有入口脚本共用的核心参数。"""
    p.add_argument("input", help="输入 Markdown 文件")
    p.add_argument("-o", "--output",
                   help="输出文件（后缀须与脚本产出格式一致），或为目录时按默认格式落盘；默认与输入同目录")
    p.add_argument("--reader", default=DEFAULT_FROM,
                   help=f"pandoc 输入格式（默认 {DEFAULT_FROM}；严格 GFM 用 gfm）")
    p.add_argument("--toc", action="store_true", help="生成目录（Word 中打开后自动刷新页码）")
    p.add_argument("--toc-depth", type=int, default=3, help="目录深度")
    p.add_argument("--highlight", action="store_true",
                   help="代码语法高亮（默认关闭，保持黑白正式文档风格）")
    p.add_argument("--dpi", type=int, default=96, help="图片分辨率换算 dpi")
    p.add_argument("--lang", default="zh-CN", help="文档语言（影响断行/校对）")
    p.add_argument("--citeproc", action="store_true",
                   help="启用参考文献处理（pandoc citeproc；配合 --bibliography）")
    p.add_argument("--bibliography",
                   help="参考文献库文件（BibTeX / BibLaTeX / CSL JSON / YAML），相对当前目录")
    p.add_argument("--csl", help="引用样式 CSL 文件（可选，默认按文档语言）")
    p.add_argument("--verbose", action="store_true", help="输出详细日志")
    p.add_argument("--keep-temp", action="store_true", help="保留临时目录（调试用）")
    p.add_argument("--version", action="version", version=f"md-convert {version}")


def add_style_args(p) -> None:
    """docx / pdf 共用的排版参数。"""
    p.add_argument("--cjk-font", default="SimSun", help="中文正文字体")
    p.add_argument("--latin-font", default="Times New Roman", help="西文/数字字体")
    p.add_argument("--mono-font", default="Consolas", help="代码字体")
    p.add_argument("--heading-cjk-font", default=DEFAULT_HEAVY_FONT,
                   help=f"中文标题/加粗字体（默认 {DEFAULT_HEAVY_FONT}）")
    p.add_argument("--no-heavy", action="store_true",
                   help="不使用 Heavy 字体，标题/加粗回退为正文字体伪粗体")
    p.add_argument("--emph-font-file", default=str(DEFAULT_HEAVY_FONT_FILE),
                   help="Heavy 字体文件路径（供 XeLaTeX 与字体内嵌；自动检测失败时需显式给出）")
    p.add_argument("--font-size", type=float, default=12.0, help="正文字号（pt）")
    p.add_argument("--line-spacing", type=float, default=1.5, help="正文行距")
    p.add_argument("--no-body-indent", dest="body_indent", action="store_false",
                   help="关闭正文首行缩进 2 字符")
    p.add_argument("--table-style", choices=("threeline", "grid"), default="threeline",
                   help="表格样式")
    p.add_argument("--number-sections", action="store_true", help="标题编号")


# ---------------------------------------------------------------------------
# 输出路径解析与标准 main 流程
# ---------------------------------------------------------------------------

def resolve_output(args, src: Path, default_ext: str) -> Path:
    """解析 -o：文件路径 / 目录 / 缺省（与输入同目录同名）。"""
    if args.output:
        out = Path(args.output)
        suffix = out.suffix.lstrip(".").lower()
        if suffix == "":
            out = out / (src.stem + "." + default_ext)
        elif suffix != default_ext:
            raise ConvertError(f"该脚本只产出 {default_ext}，-o 后缀应为 .{default_ext}（或给目录）")
        return out
    return src.with_suffix("." + default_ext)


def check_occupied(out: Path) -> bool:
    """输出文件被占用时打印可读错误并返回 True。"""
    if not out.exists():
        return False
    try:
        with open(out, "r+b"):
            return False
    except PermissionError:
        print(f"[md-convert] 错误：输出文件被其他程序占用，无法覆盖：{out}\n"
              "  请关闭正在预览/编辑该文件的程序（PDF 阅读器、Word、预览窗格等）后重试。",
              file=sys.stderr)
        return True


def standard_main(args, convert, *, default_ext: str, version: str) -> int:
    """入口脚本的标准 main 流程：校验 → 解析输出 → 转换 → 清理。

    convert 签名：convert(src: Path, out: Path, args, tmpdir: Path) -> None
    退出码：0 成功；1 转换失败；2 用法/输入错误；3 输出被占用。
    """
    _reconfigure_streams()
    src = Path(args.input)
    if not src.is_file():
        print(f"[md-convert] 错误：输入文件不存在：{src}", file=sys.stderr)
        return 2
    try:
        out = resolve_output(args, src, default_ext)
    except ConvertError as e:
        print(f"[md-convert] 错误：{e}", file=sys.stderr)
        return 2
    if check_occupied(out):
        return 3
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        require_pandoc()
        tmpdir = Path(tempfile.mkdtemp(prefix="md-convert-"))
        try:
            convert(src, out, args, tmpdir)
        except ConvertError as e:
            print(f"[md-convert] 错误：{e}", file=sys.stderr)
            return 1
        finally:
            if getattr(args, "keep_temp", False):
                log(f"临时目录已保留：{tmpdir}")
            else:
                shutil.rmtree(tmpdir, ignore_errors=True)
    except ConvertError as e:
        print(f"[md-convert] 错误：{e}", file=sys.stderr)
        return 1
    return 0
