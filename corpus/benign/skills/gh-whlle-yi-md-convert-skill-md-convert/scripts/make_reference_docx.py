#!/usr/bin/env python3
"""make_reference_docx.py — 生成受控样式的 pandoc reference.docx。

pandoc 的 docx 写入器以 reference.docx 中的样式为准排版。本脚本以 pandoc
自带的默认 reference.docx 为种子，程序化改写关键样式，使导出的 Word 文档
符合项目排版规范：

- 正文：中文宋体、西文/数字 Times New Roman、12pt、1.5 倍行距、首行缩进 2 字符
- 标题：中文思源宋体 Heavy（无伪粗体）、西文 Times New Roman、黑色
- 强调（**加粗**）：同上，由后处理脚本对中西文分别设置字体
- 代码：Consolas，浅灰底纹
- 表格：默认三线表（由后处理脚本完成边框绘制）
- 页面：A4，上下 2.54cm，左右 3.17cm

样式名与 pandoc 写入器使用的样式一一对应（Normal / Body Text / First
Paragraph / Heading 1-9 / Strong / Source Code / Verbatim Char 等），
不可随意改名，否则 pandoc 找不到样式会静默回退到默认外观。

用法：
    python make_reference_docx.py -o reference.docx [--cjk-font 宋体 ...]

完整参数见 ``build_reference()`` 与 ``main()``。生成的文件也可手动在 Word
中进一步微调后复用（styles.md 有说明）。
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt, RGBColor

# ---------------------------------------------------------------------------
# 默认排版参数（与项目排版规范一致）
# ---------------------------------------------------------------------------

DEFAULT_CJK_FONT = "SimSun"                    # 中文正文：宋体
DEFAULT_LATIN_FONT = "Times New Roman"         # 西文/数字
DEFAULT_HEAVY_CJK_FONT = "Noto Serif SC Heavy X"  # 中文强调/标题：思源宋体 Heavy
DEFAULT_MONO_FONT = "Consolas"                 # 代码

_BLACK = RGBColor(0x00, 0x00, 0x00)
_CODE_SHADING = "F7F7F7"   # 代码块底纹
_INLINE_CODE_SHADING = "EFEFEF"  # 行内代码底纹


class ReferenceError_(RuntimeError):
    """生成 reference.docx 过程中的可读错误。"""


# ---------------------------------------------------------------------------
# 底层工具：直接操作 OOXML
# ---------------------------------------------------------------------------

# CT_PPr / CT_RPr 序列的后继片段：插入元素必须按 schema 顺序，否则 Word 判定文档无效
_PPR_AFTER_SHD = (
    "w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap", "w:overflowPunct",
    "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN", "w:bidi", "w:adjustRightInd",
    "w:snapToGrid", "w:spacing", "w:ind", "w:contextualSpacing", "w:mirrorIndents",
    "w:suppressOverlap", "w:jc", "w:textDirection", "w:textAlignment",
    "w:textboxTightWrap", "w:outlineLvl", "w:divId", "w:cnfStyle", "w:rPr", "w:sectPr",
)
_PPR_AFTER_IND = _PPR_AFTER_SHD[13:]
_RPR_AFTER_SHD = (
    "w:fitText", "w:vertAlign", "w:rtl", "w:cs", "w:em", "w:lang",
    "w:eastAsianLayout", "w:specVanish",
)


# rFonts 的主题属性：OOXML 中主题属性优先于显式字体，设置显式字体前必须删除，
# 否则标题编号等西文会被文档主题字体（如 Aptos）顶掉。
_THEME_FONT_ATTRS = ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme")


def _set_style_fonts(style, *, ascii_font: str, east_asia: str, size_pt: float | None = None,
                     bold: bool | None = None, color_black: bool = False) -> None:
    """同时设置样式的西文字体（ascii/hAnsi）与中文字体（eastAsia）。"""
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    for attr in _THEME_FONT_ATTRS:
        if rfonts.get(qn(attr)) is not None:
            del rfonts.attrib[qn(attr)]
    rfonts.set(qn("w:ascii"), ascii_font)
    rfonts.set(qn("w:hAnsi"), ascii_font)
    rfonts.set(qn("w:eastAsia"), east_asia)
    if size_pt is not None:
        style.font.size = Pt(size_pt)
    if bold is not None:
        style.font.bold = bold
    if color_black:
        style.font.color.rgb = _BLACK


def _patch_theme_fonts(doc: Document, latin: str, east_asia: str) -> None:
    """把 docx 主题字体（major/minor）改为规范字体。

    兜底措施：凡是我们未显式设置字体的样式或标记（如作者/日期、题注编号、
    列表序号），其主题引用最终都落在 theme1.xml 上——不改主题就会漏出
    Aptos/Calibri 等主题字体。
    """
    for part in doc.part.package.iter_parts():
        if str(part.partname) == "/word/theme/theme1.xml":
            xml = part.blob.decode("utf-8", errors="replace")

            def _sub(m: "re.Match[str]") -> str:
                block = m.group(0)
                block = re.sub(r'<a:latin typeface="[^"]*"[^>]*/>',
                               f'<a:latin typeface="{latin}"/>', block, count=1)
                block = re.sub(r'<a:ea typeface="[^"]*"[^>]*/>',
                               f'<a:ea typeface="{east_asia}"/>', block, count=1)
                return block

            xml = re.sub(r"<a:majorFont>.*?</a:majorFont>", _sub, xml, flags=re.S)
            xml = re.sub(r"<a:minorFont>.*?</a:minorFont>", _sub, xml, flags=re.S)
            part._blob = xml.encode("utf-8")
            return


def _set_first_line_chars(style, chars: int = 200) -> None:
    """按“字符”为单位设置首行缩进（中文排版标准做法，随字号自适应）。"""
    ppr = style.element.get_or_add_pPr()
    ind = ppr.find(qn("w:ind"))
    if ind is None:
        ind = ppr.makeelement(qn("w:ind"), {})
        ppr.insert_element_before(ind, *_PPR_AFTER_IND)
    ind.set(qn("w:firstLineChars"), str(chars))
    if ind.get(qn("w:firstLine")):
        del ind.attrib[qn("w:firstLine")]


def _set_paragraph_shading(style, fill: str) -> None:
    """给段落样式加底纹（用于代码块）。"""
    ppr = style.element.get_or_add_pPr()
    shd = ppr.find(qn("w:shd"))
    if shd is None:
        shd = ppr.makeelement(qn("w:shd"), {})
        ppr.insert_element_before(shd, *_PPR_AFTER_SHD)
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), fill)


def _set_char_shading(style, fill: str) -> None:
    """给字符样式加底纹（用于行内代码）。"""
    rpr = style.element.get_or_add_rPr()
    shd = rpr.find(qn("w:shd"))
    if shd is None:
        shd = rpr.makeelement(qn("w:shd"), {})
        rpr.insert_element_before(shd, *_RPR_AFTER_SHD)
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), fill)


def _set_lang_east_asia(style, lang: str = "zh-CN") -> None:
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    lang_el = rpr.find(qn("w:lang"))
    if lang_el is None:
        lang_el = rpr.makeelement(qn("w:lang"), {})
        rpr.append(lang_el)
    lang_el.set(qn("w:eastAsia"), lang)


def _style_or_none(doc: Document, name: str):
    try:
        return doc.styles[name]
    except KeyError:
        return None


def _ensure_style(doc: Document, name: str, wtype):
    """取样式，不存在则创建。

    pandoc 默认 reference.docx 不含 Strong / Emphasis / Source Code——
    这三个样式由 pandoc 在文档使用时动态创建；必须在此预建，样式才会生效。
    """
    st = _style_or_none(doc, name)
    if st is None:
        st = doc.styles.add_style(name, wtype)
    return st


# ---------------------------------------------------------------------------
# 种子文档：pandoc 默认 reference.docx
# ---------------------------------------------------------------------------

def _seed_reference_docx(pandoc: str) -> Path:
    """从 pandoc 导出默认 reference.docx 作为种子，保证所有 pandoc 样式存在。"""
    proc = subprocess.run(
        [pandoc, "--print-default-data-file", "reference.docx"],
        capture_output=True, timeout=60,
    )
    if proc.returncode != 0 or not proc.stdout:
        raise ReferenceError_(
            f"无法从 pandoc 获取默认 reference.docx：{proc.stderr.decode(errors='replace').strip()}"
        )
    tmp = Path(tempfile.gettempdir()) / "md-convert-pandoc-reference-seed.docx"
    tmp.write_bytes(proc.stdout)
    return tmp


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def build_reference(
    out_path: str | Path,
    *,
    cjk_font: str = DEFAULT_CJK_FONT,
    latin_font: str = DEFAULT_LATIN_FONT,
    heavy_cjk_font: str | None = DEFAULT_HEAVY_CJK_FONT,
    mono_font: str = DEFAULT_MONO_FONT,
    body_pt: float = 12.0,
    line_spacing: float = 1.5,
    body_indent: bool = True,
    lang: str = "zh-CN",
    pandoc: str = "pandoc",
) -> Path:
    """生成 reference.docx 并返回路径。

    heavy_cjk_font 为 None 时表示本机没有 Heavy 字体，标题/强调回退为
    “宋体 + 伪粗体”（Word 对无粗体字形的字体做算法加粗）。
    """
    if heavy_cjk_font is None:
        heavy_cjk_font = cjk_font

    seed = _seed_reference_docx(pandoc)
    doc = Document(str(seed))
    _patch_theme_fonts(doc, latin_font, cjk_font)

    # ---- 页面：A4，中文 Word 默认页边距 --------------------------------
    sec = doc.sections[0]
    sec.page_width = Mm(210)
    sec.page_height = Mm(297)
    sec.top_margin = Cm(2.54)
    sec.bottom_margin = Cm(2.54)
    sec.left_margin = Cm(3.17)
    sec.right_margin = Cm(3.17)

    # ---- 正文 -----------------------------------------------------------
    normal = doc.styles["Normal"]
    _set_style_fonts(normal, ascii_font=latin_font, east_asia=cjk_font,
                     size_pt=body_pt, color_black=True)
    normal.paragraph_format.line_spacing = line_spacing
    normal.paragraph_format.widow_control = True
    _set_lang_east_asia(normal, lang)

    # pandoc 正文段落用的两个样式（不是 Normal）
    for name in ("Body Text", "First Paragraph"):
        st = _style_or_none(doc, name)
        if st is None:
            continue
        _set_style_fonts(st, ascii_font=latin_font, east_asia=cjk_font, color_black=True)
        if body_indent:
            _set_first_line_chars(st, 200)

    # 紧凑段落（列表项、表格单元格）：行距单倍、字号小一级、清除首行缩进
    # （Compact 基于 Body Text，会把首行缩进带进表格单元格，必须显式清零）
    compact = _style_or_none(doc, "Compact")
    if compact is not None:
        _set_style_fonts(compact, ascii_font=latin_font, east_asia=cjk_font,
                         size_pt=body_pt - 1.5, color_black=True)
        compact.paragraph_format.line_spacing = 1.0
        _set_first_line_chars(compact, 0)

    # ---- 标题 -----------------------------------------------------------
    # 中文用 Heavy 字重（不加伪粗体）；西文 Times New Roman（由后处理保证
    # 中文部分关闭 w:b）。这里样式层面保留加粗，供西文标题使用。
    heading_sizes = {1: body_pt + 4, 2: body_pt + 2, 3: body_pt + 1, 4: body_pt}
    for level in range(1, 10):
        st = _style_or_none(doc, f"Heading {level}")
        if st is None:
            continue
        size = heading_sizes.get(level, body_pt)
        _set_style_fonts(st, ascii_font=latin_font, east_asia=heavy_cjk_font,
                         size_pt=size, color_black=True)
        st.paragraph_format.keep_with_next = True

    title = _style_or_none(doc, "Title")
    if title is not None:
        _set_style_fonts(title, ascii_font=latin_font, east_asia=heavy_cjk_font,
                         size_pt=body_pt + 10, color_black=True)
        title.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for name in ("Author", "Date", "Subtitle"):
        st = _style_or_none(doc, name)
        if st is not None:
            _set_style_fonts(st, ascii_font=latin_font, east_asia=cjk_font, color_black=True)
            st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # ---- 强调 -----------------------------------------------------------
    from docx.enum.style import WD_STYLE_TYPE

    strong = _ensure_style(doc, "Strong", WD_STYLE_TYPE.CHARACTER)
    # w:b 保留给西文；中文部分由后处理脚本在 run 级别拆分处理
    _set_style_fonts(strong, ascii_font=latin_font, east_asia=heavy_cjk_font, bold=True)

    emphasis = _ensure_style(doc, "Emphasis", WD_STYLE_TYPE.CHARACTER)
    _set_style_fonts(emphasis, ascii_font=latin_font, east_asia=cjk_font, bold=False)
    emphasis.font.italic = True

    # ---- 代码 -----------------------------------------------------------
    src = _ensure_style(doc, "Source Code", WD_STYLE_TYPE.PARAGRAPH)
    src.base_style = doc.styles["Normal"]
    _set_style_fonts(src, ascii_font=mono_font, east_asia=cjk_font, size_pt=body_pt - 2)
    src.paragraph_format.line_spacing = 1.0
    _set_paragraph_shading(src, _CODE_SHADING)

    verb = _style_or_none(doc, "Verbatim Char")
    if verb is not None:
        _set_style_fonts(verb, ascii_font=mono_font, east_asia=cjk_font, size_pt=body_pt - 2)
        _set_char_shading(verb, _INLINE_CODE_SHADING)

    # ---- 引用块 ---------------------------------------------------------
    block = _style_or_none(doc, "Block Text")
    if block is not None:
        _set_style_fonts(block, ascii_font=latin_font, east_asia=cjk_font, color_black=True)
        block.font.italic = False
        block.paragraph_format.left_indent = Cm(0.75)

    # ---- 题注 -----------------------------------------------------------
    for name in ("Table Caption", "Image Caption"):
        st = _style_or_none(doc, name)
        if st is not None:
            _set_style_fonts(st, ascii_font=latin_font, east_asia=heavy_cjk_font,
                             size_pt=body_pt - 1.5, color_black=True)
            st.font.italic = False  # pandoc 默认题注斜体，中文题注应为直立
            st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # ---- 目录标题：pandoc 默认为蓝色，规范要求黑色 ----------------------
    toc_heading = _style_or_none(doc, "TOC Heading")
    if toc_heading is not None:
        _set_style_fonts(toc_heading, ascii_font=latin_font, east_asia=heavy_cjk_font,
                         color_black=True)
        toc_heading.font.italic = False

    # ---- 脚注 -----------------------------------------------------------
    foot = _style_or_none(doc, "Footnote Text")
    if foot is not None:
        _set_style_fonts(foot, ascii_font=latin_font, east_asia=cjk_font,
                         size_pt=body_pt - 3, color_black=True)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="make_reference_docx.py",
        description="生成受控样式的 pandoc reference.docx（md-convert 样式体系）",
    )
    parser.add_argument("-o", "--output", required=True, help="输出 .docx 路径")
    parser.add_argument("--cjk-font", default=DEFAULT_CJK_FONT, help=f"中文正文字体（默认 {DEFAULT_CJK_FONT}）")
    parser.add_argument("--latin-font", default=DEFAULT_LATIN_FONT, help=f"西文字体（默认 {DEFAULT_LATIN_FONT}）")
    parser.add_argument("--heavy-cjk-font", default=DEFAULT_HEAVY_CJK_FONT,
                        help="中文标题/强调字体；传 none 回退宋体伪粗体")
    parser.add_argument("--mono-font", default=DEFAULT_MONO_FONT, help=f"代码字体（默认 {DEFAULT_MONO_FONT}）")
    parser.add_argument("--font-size", type=float, default=12.0, help="正文字号 pt（默认 12 = 小四）")
    parser.add_argument("--line-spacing", type=float, default=1.5, help="正文行距（默认 1.5）")
    parser.add_argument("--no-body-indent", action="store_true", help="关闭正文首行缩进")
    args = parser.parse_args(argv)

    heavy = None if args.heavy_cjk_font.lower() in ("none", "no") else args.heavy_cjk_font
    path = build_reference(
        args.output,
        cjk_font=args.cjk_font,
        latin_font=args.latin_font,
        heavy_cjk_font=heavy,
        mono_font=args.mono_font,
        body_pt=args.font_size,
        line_spacing=args.line_spacing,
        body_indent=not args.no_body_indent,
    )
    print(f"[md-convert] reference.docx 已生成：{path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
