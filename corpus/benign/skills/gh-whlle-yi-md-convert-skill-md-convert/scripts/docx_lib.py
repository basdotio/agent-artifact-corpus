#!/usr/bin/env python3
"""docx_lib.py — docx 管线核心，供 to_docx.py 复用。

四步管线（convert_docx）：
  1. build_reference()        生成受控样式的 reference.docx（排版模板）
  2. pandoc 转换              挂模板，公式转 OMML，--toc/-N/citeproc
  3. python-docx 后处理       三线表、中西文拆分加粗、目录域标记
  4. 字体内嵌                 Heavy 字体子集 ODTTF，接收方无需安装

本文件的函数不解析命令行——参数对象由入口脚本经 common.py 构造。
"""

from __future__ import annotations

import copy
import re
from pathlib import Path

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# OOXML 子元素顺序（CT_* 序列的后继片段），插入元素必须遵守，
# 否则 Word 会判定文档无效并进入修复/只读模式。
_RPR_AFTER_RFONTS = (
    "w:b", "w:bCs", "w:i", "w:iCs", "w:caps", "w:smallCaps", "w:strike", "w:dstrike",
    "w:outline", "w:shadow", "w:emboss", "w:imprint", "w:noProof", "w:snapToGrid",
    "w:vanish", "w:webHidden", "w:color", "w:spacing", "w:w", "w:kern", "w:position",
    "w:sz", "w:szCs", "w:highlight", "w:u", "w:effect", "w:bdr", "w:shd", "w:fitText",
    "w:vertAlign", "w:rtl", "w:cs", "w:em", "w:lang", "w:eastAsianLayout",
)
_RPR_AFTER_B = _RPR_AFTER_RFONTS[2:]
_TBLPR_AFTER_TBLW = (
    "w:jc", "w:tblCellSpacing", "w:tblInd", "w:tblBorders", "w:shd", "w:tblLayout",
    "w:tblCellMar", "w:tblLook", "w:tblCaption", "w:tblDescription",
)
_TBLPR_AFTER_BORDERS = _TBLPR_AFTER_TBLW[4:]
_TRPR_AFTER_CANTSPLIT = ("w:trHeight", "w:tblHeader", "w:tblCellSpacing", "w:jc", "w:hidden")
_TRPR_AFTER_TBLHEADER = ("w:tblCellSpacing", "w:jc", "w:hidden")
_TCPR_AFTER_TCBORDERS = (
    "w:shd", "w:noWrap", "w:tcMar", "w:textDirection", "w:tcFitText", "w:vAlign", "w:hideMark",
)

# CJK 统一表意文字及扩展、兼容表意、部首、中文标点、全角字符
CJK_RE = re.compile(
    "[\u2e80-\u2eff\u3000-\u303f\u31c0-\u31ef\u3200-\u32ff\u3400-\u4dbf"
    "\u4e00-\u9fff\uf900-\ufaff\ufe30-\ufe4f\uff00-\uffef]"
)
SEG_RE = re.compile(
    "([\u2e80-\u2eff\u3000-\u303f\u31c0-\u31ef\u3200-\u32ff\u3400-\u4dbf"
    "\u4e00-\u9fff\uf900-\ufaff\ufe30-\ufe4f\uff00-\uffef]+"
    "|[^\u2e80-\u2eff\u3000-\u303f\u31c0-\u31ef\u3200-\u32ff\u3400-\u4dbf"
    "\u4e00-\u9fff\uf900-\ufaff\ufe30-\ufe4f\uff00-\uffef]+)"
)


def _get_or_add(parent, tag: str, successors: tuple[str, ...]):
    """取（或按 schema 顺序创建）parent 的直接子元素 tag。"""
    el = parent.find(f"{W_NS}{tag}")
    if el is None:
        el = parent.makeelement(f"{W_NS}{tag}", {})
        parent.insert_element_before(el, *successors)
    return el


# ---------------------------------------------------------------------------
# docx 后处理：拆分加粗
# ---------------------------------------------------------------------------

def _iter_body_paragraphs(doc):
    yield from doc.element.body.iter(f"{W_NS}p")


def _pstyle_of(p_el) -> str | None:
    ppr = p_el.find(f"{W_NS}pPr")
    if ppr is None:
        return None
    pstyle = ppr.find(f"{W_NS}pStyle")
    return pstyle.get(f"{W_NS}val") if pstyle is not None else None


def _effective_bold(pstyle: str | None, rpr) -> bool:
    """判断 run 是否“实际加粗”：直接 w:b > rStyle(Strong) > 段落样式(标题族)。"""
    if rpr is not None:
        b = rpr.find(f"{W_NS}b")
        if b is not None:
            return b.get(f"{W_NS}val") not in ("0", "false", "none")
        rstyle = rpr.find(f"{W_NS}rStyle")
        if rstyle is not None and (rstyle.get(f"{W_NS}val") or "") == "Strong":
            return True
    if pstyle and (pstyle.startswith("Heading") or pstyle in ("Title", "Subtitle")):
        return True
    return False


def _run_text(r_el) -> str | None:
    """返回 run 的纯文本；若包含 w:t 以外的内容（图、换行、域等）返回 None。"""
    parts: list[str] = []
    for child in r_el:
        tag = child.tag
        if tag == f"{W_NS}rPr":
            continue
        if tag == f"{W_NS}t":
            parts.append(child.text or "")
        else:
            return None
    return "".join(parts)


def _make_segment_run(r_el, text: str, *, heavy_font: str | None):
    """复制 run 并写入单段文本；heavy_font 不为 None 时按“中文强调”规则处理。"""
    new_r = copy.deepcopy(r_el)
    for t in new_r.findall(f"{W_NS}t"):
        new_r.remove(t)
    t = new_r.makeelement(f"{W_NS}t", {})
    t.text = text
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    rpr = new_r.find(f"{W_NS}rPr")
    if rpr is not None:
        rpr.addnext(t)
    else:
        new_r.insert(0, t)

    if heavy_font is not None:
        rpr = new_r.find(f"{W_NS}rPr")
        if rpr is None:
            rpr = new_r.makeelement(f"{W_NS}rPr", {})
            new_r.insert(0, rpr)
        # 显式关闭加粗（run 级 w:b=0 覆盖样式级 w:b，避免 Heavy 字体再被伪粗体）
        b = _get_or_add(rpr, "b", _RPR_AFTER_B)
        b.set(f"{W_NS}val", "0")
        rfonts = _get_or_add(rpr, "rFonts", _RPR_AFTER_RFONTS)
        rfonts.set(f"{W_NS}eastAsia", heavy_font)
    return new_r


def fix_cjk_bold(doc, heavy_font: str) -> int:
    """中文强调规范化：加粗文本按中西文拆分 run。

    中文段使用 Heavy 宋体并显式关闭 w:b（不产生伪粗体）；
    西文段保留原样式（Times New Roman Bold）。
    """
    changed = 0
    for p in _iter_body_paragraphs(doc):
        pstyle = _pstyle_of(p)
        for r in list(p.iter(f"{W_NS}r")):
            text = _run_text(r)
            if not text or not CJK_RE.search(text):
                continue
            rpr = r.find(f"{W_NS}rPr")
            if not _effective_bold(pstyle, rpr):
                continue
            segs = [m.group(0) for m in SEG_RE.finditer(text)]
            if len(segs) <= 1 and CJK_RE.fullmatch(text):
                segs = [text]  # 纯中文整段，也统一改写
            anchors = []
            for seg in segs:
                is_cjk = bool(CJK_RE.match(seg))
                anchors.append(_make_segment_run(r, seg, heavy_font=heavy_font if is_cjk else None))
            for el in anchors:
                r.addprevious(el)
            p.remove(r)
            changed += 1
    return changed


# ---------------------------------------------------------------------------
# docx 后处理：表格
# ---------------------------------------------------------------------------

def _table_autofit(tbl) -> None:
    """列宽按内容自适应。

    pandoc 依据 md 源中分隔行的横线长度分配列宽，窄数字列会被压出折行
    （如 1,024 断成 1,02/4）。清除显式列宽并切到 autofit，由 Word 按内容重排。
    """
    tblpr = tbl._tbl.tblPr
    tblw = _get_or_add(tblpr, "tblW", _TBLPR_AFTER_TBLW)
    tblw.set(f"{W_NS}w", "0")
    tblw.set(f"{W_NS}type", "auto")
    layout = _get_or_add(tblpr, "tblLayout", _TBLPR_AFTER_TBLW)
    layout.set(f"{W_NS}type", "autofit")
    for tcpr in tbl._tbl.iter(f"{W_NS}tcPr"):
        for tcw in tcpr.findall(f"{W_NS}tcW"):
            tcw.set(f"{W_NS}w", "0")
            tcw.set(f"{W_NS}type", "auto")


def _repeat_header_row(row) -> None:
    """表头行跨页重复，且行内不断页。"""
    trpr = row._tr.get_or_add_trPr()
    if trpr.find(f"{W_NS}cantSplit") is None:
        trpr.insert_element_before(trpr.makeelement(f"{W_NS}cantSplit", {}),
                                   *_TRPR_AFTER_CANTSPLIT)
    if trpr.find(f"{W_NS}tblHeader") is None:
        trpr.insert_element_before(trpr.makeelement(f"{W_NS}tblHeader", {}),
                                   *_TRPR_AFTER_TBLHEADER)


def style_tables(doc, mode: str = "threeline") -> int:
    """为所有表格设置边框：threeline（学术三线表）或 grid（全框线）。

    同时居中表格、列宽按内容自适应、表头行加粗并跨页重复。
    表头中文随后由 fix_cjk_bold 规范化字重。
    """
    from docx.enum.table import WD_TABLE_ALIGNMENT

    count = 0
    for tbl in doc.tables:
        tblpr = tbl._tbl.tblPr
        old = tblpr.find(f"{W_NS}tblBorders")
        if old is not None:
            tblpr.remove(old)
        if mode == "threeline":
            spec = {"top": ("single", 12), "bottom": ("single", 12),
                    "left": ("none", 0), "right": ("none", 0),
                    "insideH": ("none", 0), "insideV": ("none", 0)}
        else:
            spec = {s: ("single", 4) for s in ("top", "left", "bottom", "right", "insideH", "insideV")}
        borders = tblpr.makeelement(f"{W_NS}tblBorders", {})
        tblpr.insert_element_before(borders, *_TBLPR_AFTER_BORDERS)
        for side, (val, sz) in spec.items():
            side_el = borders.makeelement(f"{W_NS}{side}", {})
            side_el.set(f"{W_NS}val", val)
            if val == "single":
                side_el.set(f"{W_NS}sz", str(sz))
                side_el.set(f"{W_NS}space", "0")
                side_el.set(f"{W_NS}color", "000000")
            borders.append(side_el)

        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        _table_autofit(tbl)

        # 表头行：加粗 + 三线表中的 0.75pt 下边线 + 跨页重复
        if tbl.rows:
            _repeat_header_row(tbl.rows[0])
            for cell in tbl.rows[0].cells:
                tcpr = cell._tc.get_or_add_tcPr()
                old_tc = tcpr.find(f"{W_NS}tcBorders")
                if old_tc is not None:
                    tcpr.remove(old_tc)
                if mode == "threeline":
                    tcb = tcpr.makeelement(f"{W_NS}tcBorders", {})
                    bottom = tcb.makeelement(f"{W_NS}bottom", {})
                    bottom.set(f"{W_NS}val", "single")
                    bottom.set(f"{W_NS}sz", "6")
                    bottom.set(f"{W_NS}space", "0")
                    bottom.set(f"{W_NS}color", "000000")
                    tcb.append(bottom)
                    tcpr.insert_element_before(tcb, *_TCPR_AFTER_TCBORDERS)
                for p in cell.paragraphs:
                    for run in p.runs:
                        run.font.bold = True
        count += 1
    return count


def enable_update_fields(doc) -> None:
    """标记文档打开时更新域（目录页码在 Word 中自动刷新）。"""
    settings = doc.settings.element
    if settings.find(f"{W_NS}updateFields") is None:
        el = settings.makeelement(f"{W_NS}updateFields", {})
        el.set(f"{W_NS}val", "true")
        settings.append(el)


# ---------------------------------------------------------------------------
# 字体内嵌（ODTTF）
# ---------------------------------------------------------------------------

def _subset_font(font_path: Path, text: str) -> bytes:
    """按文档用字裁剪字体，控制体积（完整 CJK 字体 10MB+，子集通常 <2MB）。"""
    import io

    from fontTools import subset
    from fontTools.ttLib import TTFont

    opts = subset.Options()
    opts.name_IDs = ["*"]
    opts.name_legacy = True
    opts.name_languages = ["*"]
    opts.glyph_names = False
    opts.layout_features = ["*"]
    opts.notdef_outline = True
    font = TTFont(str(font_path))
    subsetter = subset.Subsetter(options=opts)
    subsetter.populate(text=text)
    subsetter.subset(font)
    buf = io.BytesIO()
    font.save(buf)
    return buf.getvalue()


def _obfuscate_odttf(data: bytes, guid_str: str) -> bytes:
    """ODTTF 混淆：前 32 字节与 GUID 十六进制字节顺序异或，循环两轮。"""
    hexstr = guid_str.strip("{}").replace("-", "")
    key = bytes.fromhex(hexstr)
    head = bytearray(data[:32])
    for i in range(32):
        head[i] ^= key[i % 16]
    return bytes(head) + data[32:]


def embed_heavy_font(docx_path: Path, family: str, font_file: Path) -> bool:
    """把 Heavy 字体以 ODTTF 子集嵌入 docx。

    Word 对按用户注册的字体解析不稳定、对 CJK 变量字体支持差，接收方也
    往往没有该字体——内嵌后渲染不依赖系统安装。成功返回 True。
    """
    import uuid
    import zipfile

    if not font_file.is_file():
        return False
    with zipfile.ZipFile(docx_path) as z:
        names = z.namelist()
        texts = []
        for part in ("word/document.xml", "word/footnotes.xml", "word/endnotes.xml",
                     "word/header1.xml", "word/footer1.xml"):
            if part in names:
                xml = z.read(part).decode("utf-8", errors="replace")
                texts.append("".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml)))
        chars = "".join(texts) + family
        subset = _subset_font(font_file, chars)

    guid_hex = uuid.uuid4().hex
    guid_str = (f"{{{guid_hex[:8].upper()}-{guid_hex[8:12].upper()}-"
                f"{guid_hex[12:16].upper()}-{guid_hex[16:20].upper()}-"
                f"{guid_hex[20:32].upper()}}}")
    odttf = _obfuscate_odttf(subset, guid_str)

    with zipfile.ZipFile(docx_path) as z:
        items = {n: z.read(n) for n in z.namelist()}

    # 1) [Content_Types].xml：注册 odttf 类型
    ct = items["[Content_Types].xml"].decode("utf-8")
    if 'Extension="odttf"' not in ct:
        ct = ct.replace(
            "</Types>",
            '<Default Extension="odttf" '
            'ContentType="application/vnd.openxmlformats-officedocument.obfuscatedFont"/></Types>')
    items["[Content_Types].xml"] = ct.encode("utf-8")

    # 2) fontTable.xml：补/改 w:font 条目，挂 embedRegular
    ft = items["word/fontTable.xml"].decode("utf-8")
    font_block = (f'<w:font w:name="{family}">'
                  f'<w:charset w:val="86"/><w:family w:val="roman"/>'
                  f'<w:pitch w:val="variable"/>'
                  f'<w:embedRegular r:id="rIdMdfont1" w:fontKey="{guid_str}"/>'
                  f'</w:font>')
    if f'w:name="{family}"' in ft:
        ft = re.sub(rf'<w:font w:name="{re.escape(family)}">.*?</w:font>',
                    font_block, ft, flags=re.S)
    else:
        ft = ft.replace("</w:fonts>", font_block + "</w:fonts>")
    items["word/fontTable.xml"] = ft.encode("utf-8")

    # 3) fontTable 的 rels
    rel_name = "word/_rels/fontTable.xml.rels"
    rel_entry = ('<Relationship Id="rIdMdfont1" Type="http://schemas.openxmlformats.org/'
                 'officeDocument/2006/relationships/font" Target="fonts/font1.odttf"/>')
    if rel_name in items:
        rels = items[rel_name].decode("utf-8").replace(
            "</Relationships>", rel_entry + "</Relationships>")
    else:
        rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                + rel_entry + "</Relationships>")
    items[rel_name] = rels.encode("utf-8")

    # 4) settings.xml：声明文档含内嵌字体（按 schema 序列插在靠前位置）
    st = items["word/settings.xml"].decode("utf-8")
    if "embedTrueTypeFonts" not in st:
        el = "<w:embedTrueTypeFonts/><w:saveSubsetFonts/>"
        m = re.search(r"<w:settings[^>]*>", st)
        open_end = m.end()
        succ = re.search(r"<w:(?:defaultTabStop|autoHyphenation|compatability|"
                         r"compat|rsids|themeFontLang|clrSchemeMapping|shapeDefaults)"
                         r"[ />]", st[open_end:])
        if succ:
            pos = open_end + succ.start()
            st = st[:pos] + el + st[pos:]
        else:
            st = st[:open_end] + el + st[open_end:]
    items["word/settings.xml"] = st.encode("utf-8")

    # 5) 字体数据
    items["word/fonts/font1.odttf"] = odttf

    tmp = docx_path.with_suffix(".tmp.docx")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in items.items():
            z.writestr(name, data)
    tmp.replace(docx_path)
    return True


# ---------------------------------------------------------------------------
# 四步管线
# ---------------------------------------------------------------------------

def convert_docx(src: Path, out: Path, args, tmpdir: Path) -> Path:
    """md → docx 四步管线。args 由入口脚本经 common.py 构造。"""
    from common import citeproc_args, log, run_pandoc
    from docx import Document
    from make_reference_docx import build_reference

    ref = build_reference(
        tmpdir / "reference.docx",
        cjk_font=args.cjk_font,
        latin_font=args.latin_font,
        heavy_cjk_font=None if args.no_heavy else args.heading_cjk_font,
        mono_font=args.mono_font,
        body_pt=args.font_size,
        line_spacing=args.line_spacing,
        body_indent=args.body_indent,
        lang=args.lang,
    )
    pandoc_args = [
        str(src), "-f", args.reader, "-t", "docx",
        "--reference-doc", str(ref),
        "--resource-path", str(src.parent),
        "--dpi", str(args.dpi),
        "-M", f"lang={args.lang}",
        "-o", str(out),
    ]
    if not args.highlight:
        pandoc_args.append("--no-highlight")
    pandoc_args += citeproc_args(args)
    if args.toc:
        pandoc_args += ["--toc", "--toc-depth", str(args.toc_depth),
                        "-M", "toc-title=目录"]
    if args.number_sections:
        pandoc_args += ["--number-sections"]
    run_pandoc(pandoc_args, args.verbose)

    # ---- 后处理 ----
    doc = Document(str(out))
    n_tables = style_tables(doc, args.table_style)
    n_runs = 0
    if not args.no_heavy:
        n_runs = fix_cjk_bold(doc, args.heading_cjk_font)
    if args.toc:
        enable_update_fields(doc)
    doc.save(str(out))

    # ---- Heavy 字体内嵌（不依赖收件人安装） ----
    embedded = False
    if not args.no_heavy:
        font_file = Path(args.emph_font_file) if args.emph_font_file else None
        if font_file and font_file.is_file():
            try:
                embedded = embed_heavy_font(out, args.heading_cjk_font, font_file)
            except Exception as e:  # 内嵌失败不阻断转换，回退为依赖本机字体
                log(f"字体内嵌失败（忽略，回退本机字体）：{e}")

    log(f"docx 完成：{out.name}（表格 {n_tables}，规范化的强调 run {n_runs}，"
        f"样式 {'三线表' if args.table_style == 'threeline' else '全框线'}"
        f"{'，字体内嵌' if embedded else ''}）")
    return out
