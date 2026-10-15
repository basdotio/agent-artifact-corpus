# -*- coding: utf-8 -*-
"""
builder.py
大学通用实验报告排版主引擎 (Universal College Lab Report Engine)
支持从 JSON 配置文件或代码调用生成标准 B4 6页双面折页 Word (.docx) 和 PDF。
具备实体大框全高容器、中缝折页独立页脚、微段落阻断与防溢出算法。
"""

import os
import sys
import json
import argparse

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import docx
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

# ----------------------------------------------------------------------
# 默认配置常量（通用安全占位符，不包含任何个人隐私信息）
# ----------------------------------------------------------------------
DEFAULT_STUDENT_INFO = {
    "university": "四川轻化工大学",
    "department": "计算机科学与工程学院",
    "major": "计算机专业",
    "class_num": "2024级",
    "name": "同学姓名",
    "student_id": "学号未填写",
    "group_num": "01",
    "lab_name": "专业教学实验室",
    "date": "2026年秋季"
}

LOCAL_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".labreport_config.json")

def load_local_student_config():
    if os.path.exists(LOCAL_CONFIG_PATH):
        try:
            with open(LOCAL_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

# ----------------------------------------------------------------------
# 排版基础辅助函数
# ----------------------------------------------------------------------
def format_run(run, font_cn="宋体", font_en="Times New Roman", size_pt=8.2, bold=False, italic=False, color_rgb=None):
    run.bold = bold
    run.italic = italic
    run.font.name = font_en
    run.font.size = Pt(size_pt)
    if color_rgb:
        run.font.color.rgb = RGBColor(*color_rgb)
    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.xpath('./w:rFonts')
    if not rFonts:
        rFonts_elem = OxmlElement('w:rFonts')
        rPr.append(rFonts_elem)
    else:
        rFonts_elem = rFonts[0]
    rFonts_elem.set(qn('w:ascii'), font_en)
    rFonts_elem.set(qn('w:hAnsi'), font_en)
    rFonts_elem.set(qn('w:eastAsia'), font_cn)

def set_para_format(para, align=WD_ALIGN_PARAGRAPH.LEFT, line_spacing=1.08, space_before=0.5, space_after=0.5):
    para.alignment = align
    para.paragraph_format.line_spacing = line_spacing
    para.paragraph_format.space_before = Pt(space_before)
    para.paragraph_format.space_after = Pt(space_after)

def add_col_break(doc):
    p = doc.add_paragraph()
    set_para_format(p, space_before=0, space_after=0, line_spacing=1.0)
    pPr = p._p.get_or_add_pPr()
    pPr.append(parse_xml(f'<w:spacing {nsdecls("w")} w:before="0" w:after="0" w:line="20" w:lineRule="exact"/>'))
    r = p.add_run()
    r._r.append(parse_xml(f'<w:br {nsdecls("w")} w:type="column"/>'))

def configure_b4_section(section, left_page_num, right_page_num):
    section.page_width = Pt(1105.65)
    section.page_height = Pt(765.45)
    section.left_margin = Pt(42.55)
    section.right_margin = Pt(42.55)
    section.top_margin = Pt(42.55)
    section.bottom_margin = Pt(42.55)
    
    sectPr = section._sectPr
    cols = sectPr.find(qn('w:cols'))
    if cols is None:
        cols = OxmlElement('w:cols')
        sectPr.append(cols)
    cols.set(qn('w:num'), '2')
    cols.set(qn('w:space'), '1131')
    
    footer = section.footer
    footer.is_linked_to_previous = False
    p_f = footer.paragraphs[0]
    p_f.text = ""
    set_para_format(p_f, space_before=0, space_after=0, line_spacing=1.0)
    
    tbl_f = footer.add_table(rows=1, cols=2, width=Pt(1020))
    tbl_f.autofit = False
    tbl_fPr = tbl_f._tbl.tblPr
    tbl_fPr.append(parse_xml(f'<w:tblW {nsdecls("w")} w:w="9640" w:type="dxa"/>'))
    tbl_fPr.append(parse_xml(f'<w:tblInd {nsdecls("w")} w:w="0" w:type="dxa"/>'))
    
    c0 = tbl_f.cell(0, 0)
    c0._tc.get_or_add_tcPr().append(parse_xml(f'<w:tcW {nsdecls("w")} w:w="4820" w:type="dxa"/>'))
    p0 = c0.paragraphs[0]
    p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r0 = p0.add_run(f"第 {left_page_num} 页")
    format_run(r0, font_cn="宋体", font_en="Times New Roman", size_pt=9.0)
    
    c1 = tbl_f.cell(0, 1)
    c1._tc.get_or_add_tcPr().append(parse_xml(f'<w:tcW {nsdecls("w")} w:w="4820" w:type="dxa"/>'))
    p1 = c1.paragraphs[0]
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = p1.add_run(f"第 {right_page_num} 页")
    format_run(r1, font_cn="宋体", font_en="Times New Roman", size_pt=9.0)

def create_container_table(doc, title_text, min_height_dxa=11200):
    tbl = doc.add_table(rows=1, cols=2)
    tbl.autofit = False
    tblPr = tbl._tbl.tblPr
    tblPr.append(parse_xml(f'<w:tblW {nsdecls("w")} w:w="9464" w:type="dxa"/>'))
    tblPr.append(parse_xml(f'<w:tblInd {nsdecls("w")} w:w="0" w:type="dxa"/>'))
    tblPr.append(parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
        f'  <w:left w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
        f'  <w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
        f'  <w:right w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
        f'  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        f'  <w:insideV w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        f'</w:tblBorders>'
    ))
    tblPr.append(parse_xml(
        f'<w:tblCellMar {nsdecls("w")}>'
        f'  <w:top w:w="40" w:type="dxa"/>'
        f'  <w:left w:w="80" w:type="dxa"/>'
        f'  <w:bottom w:w="40" w:type="dxa"/>'
        f'  <w:right w:w="80" w:type="dxa"/>'
        f'</w:tblCellMar>'
    ))
    
    row = tbl.rows[0]
    trPr = row._tr.get_or_add_trPr()
    trPr.append(parse_xml(f'<w:trHeight {nsdecls("w")} w:val="{min_height_dxa}" w:hRule="atLeast"/>'))
    
    c0 = row.cells[0]
    c0._tc.get_or_add_tcPr().append(parse_xml(f'<w:tcW {nsdecls("w")} w:w="959" w:type="dxa"/>'))
    c0._tc.get_or_add_tcPr().append(parse_xml(f'<w:vAlign {nsdecls("w")} w:val="center"/>'))
    p0 = c0.paragraphs[0]
    p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r0 = p0.add_run(title_text)
    format_run(r0, font_cn="黑体", font_en="Arial", size_pt=10.0, bold=True)
    
    c1 = row.cells[1]
    c1._tc.get_or_add_tcPr().append(parse_xml(f'<w:tcW {nsdecls("w")} w:w="8505" w:type="dxa"/>'))
    c1._tc.get_or_add_tcPr().append(parse_xml(f'<w:vAlign {nsdecls("w")} w:val="top"/>'))
    c1.paragraphs[0].text = ""
    return c1

def add_heading(cell, text, level=1):
    p = cell.add_paragraph() if cell.paragraphs[0].text else cell.paragraphs[0]
    if level == 1:
        set_para_format(p, space_before=2.5, space_after=1.0)
        run = p.add_run(text)
        format_run(run, font_cn="黑体", font_en="Arial", size_pt=9.2, bold=True, color_rgb=(15, 35, 75))
    elif level == 2:
        set_para_format(p, space_before=2.0, space_after=0.8)
        run = p.add_run(text)
        format_run(run, font_cn="黑体", font_en="Arial", size_pt=8.6, bold=True, color_rgb=(25, 50, 100))
    elif level == 3:
        set_para_format(p, space_before=1.2, space_after=0.6)
        run = p.add_run(text)
        format_run(run, font_cn="黑体", font_en="Arial", size_pt=8.2, bold=True, color_rgb=(40, 40, 40))
    return p

def add_p(cell, text, bold_prefix=None, indent=0):
    p = cell.add_paragraph() if cell.paragraphs[0].text else cell.paragraphs[0]
    set_para_format(p, line_spacing=1.08, space_before=0.5, space_after=0.5)
    if indent > 0:
        p.paragraph_format.left_indent = Pt(indent * 8)
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        format_run(r_pre, font_cn="黑体", font_en="Arial", size_pt=8.2, bold=True, color_rgb=(20, 20, 20))
    r_body = p.add_run(text)
    format_run(r_body, font_cn="宋体", font_en="Times New Roman", size_pt=8.2, color_rgb=(25, 25, 25))
    return p

def add_img(cell, img_path, width_in=4.0, caption=None):
    if not os.path.exists(img_path):
        print(f"[Warning] Image not found: {img_path}")
        return
    p = cell.add_paragraph()
    set_para_format(p, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=1.5, space_after=0.5)
    r = p.add_run()
    r.add_picture(img_path, width=Inches(width_in))
    
    if caption:
        p_cap = cell.add_paragraph()
        set_para_format(p_cap, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=0.5, space_after=1.5)
        r_cap = p_cap.add_run(caption)
        format_run(r_cap, font_cn="楷体", font_en="Times New Roman", size_pt=7.6, bold=True, color_rgb=(60, 60, 60))

def add_code(cell, code_lines):
    p = cell.add_paragraph()
    set_para_format(p, line_spacing=1.02, space_before=1.0, space_after=1.0)
    p.paragraph_format.left_indent = Pt(5)
    pPr = p._p.get_or_add_pPr()
    pPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="F6F8FA"/>'))
    pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:left w:val="single" w:sz="12" w:space="4" w:color="0969DA"/></w:pBdr>')
    pPr.append(pBdr)
    
    for i, line in enumerate(code_lines):
        r = p.add_run(line + ("\n" if i < len(code_lines) - 1 else ""))
        format_run(r, font_cn="Consolas", font_en="Consolas", size_pt=7.0, color_rgb=(30, 30, 30))


# ----------------------------------------------------------------------
# 通用大学实验报告页面构建引擎
# ----------------------------------------------------------------------
class UniversalLabReportBuilder:
    """
    通用大学实验报告排版引擎
    可适配各理工科专业、各大高校官方标准的 B4 6页实体大框双面折页格式。
    """
    def __init__(self, data):
        self.data = data
        local_cfg = load_local_student_config()
        self.student = {**DEFAULT_STUDENT_INFO, **local_cfg, **data.get("student_info", {})}
        self.doc = docx.Document()
        
    def build_page1(self):
        # 表头与基本信息
        p_title = self.doc.add_paragraph()
        set_para_format(p_title, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=0, space_after=1)
        
        # 动态根据高校名称生成庄重开阔的表头标题
        univ_name = self.student.get("university", "通用高等院校").strip()
        if "实验报告" in univ_name:
            title_text = "  ".join(list(univ_name.replace(" ", "")))
        else:
            title_text = "  ".join(list(univ_name.replace(" ", ""))) + "  实  验  报  告"
            
        r_t = p_title.add_run(title_text)
        format_run(r_t, font_cn="黑体", font_en="Arial", size_pt=14.0, bold=True)

        p_sub = self.doc.add_paragraph()
        set_para_format(p_sub, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=0, space_after=2)
        r_sub = p_sub.add_run(
            f"学院/系：{self.student.get('department')}    "
            f"课程名称：{self.data.get('course_name', '专业实验课程')}    "
            f"实验日期：{self.student.get('date')}"
        )
        format_run(r_sub, font_cn="宋体", font_en="Times New Roman", size_pt=8.8)

        # Page 1 Table 0 (学生信息 + 仪器 + 目的)
        t0 = self.doc.add_table(rows=5, cols=8)
        t0.autofit = False
        t0Pr = t0._tbl.tblPr
        t0Pr.append(parse_xml(f'<w:tblW {nsdecls("w")} w:w="9464" w:type="dxa"/>'))
        t0Pr.append(parse_xml(f'<w:tblInd {nsdecls("w")} w:w="0" w:type="dxa"/>'))
        t0Pr.append(parse_xml(
            f'<w:tblBorders {nsdecls("w")}>'
            f'  <w:top w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
            f'  <w:left w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
            f'  <w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
            f'  <w:right w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
            f'  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
            f'  <w:insideV w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
            f'</w:tblBorders>'
        ))
        t0Pr.append(parse_xml(
            f'<w:tblCellMar {nsdecls("w")}>'
            f'  <w:top w:w="30" w:type="dxa"/>'
            f'  <w:left w:w="60" w:type="dxa"/>'
            f'  <w:bottom w:w="30" w:type="dxa"/>'
            f'  <w:right w:w="60" w:type="dxa"/>'
            f'</w:tblCellMar>'
        ))

        widths_r0 = [959, 992, 851, 850, 1134, 1843, 1276, 1559]
        texts_r0 = [
            "姓 名", self.student.get("name"), 
            "组 号", self.student.get("group_num"), 
            "学 号", self.student.get("student_id"), 
            "实验室", self.student.get("lab_name")
        ]
        for i in range(8):
            c = t0.cell(0, i)
            c._tc.get_or_add_tcPr().append(parse_xml(f'<w:tcW {nsdecls("w")} w:w="{widths_r0[i]}" w:type="dxa"/>'))
            c._tc.get_or_add_tcPr().append(parse_xml(f'<w:vAlign {nsdecls("w")} w:val="center"/>'))
            p = c.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(texts_r0[i])
            format_run(r, font_cn="黑体" if i % 2 == 0 else "楷体", font_en="Times New Roman", size_pt=8.5, bold=(i % 2 == 0))

        texts_r1 = [
            "专 业", self.student.get("major"), 
            "组 号", self.student.get("group_num"), 
            "班 号", self.student.get("class_num"), 
            "老师签名", ""
        ]
        for i in range(8):
            c = t0.cell(1, i)
            c._tc.get_or_add_tcPr().append(parse_xml(f'<w:tcW {nsdecls("w")} w:w="{widths_r0[i]}" w:type="dxa"/>'))
            c._tc.get_or_add_tcPr().append(parse_xml(f'<w:vAlign {nsdecls("w")} w:val="center"/>'))
            p = c.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(texts_r1[i])
            format_run(r, font_cn="黑体" if i % 2 == 0 else "楷体", font_en="Times New Roman", size_pt=8.5, bold=(i % 2 == 0))

        # Row 2: 实验名称
        t0.cell(2, 1).merge(t0.cell(2, 5))
        c2_0 = t0.cell(2, 0)
        c2_0._tc.get_or_add_tcPr().append(parse_xml(f'<w:tcW {nsdecls("w")} w:w="959" w:type="dxa"/>'))
        c2_0._tc.get_or_add_tcPr().append(parse_xml(f'<w:vAlign {nsdecls("w")} w:val="center"/>'))
        p = c2_0.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        format_run(p.add_run("实验\n名称"), font_cn="黑体", size_pt=8.5, bold=True)

        c2_1 = t0.cell(2, 1)
        c2_1._tc.get_or_add_tcPr().append(parse_xml(f'<w:tcW {nsdecls("w")} w:w="5670" w:type="dxa"/>'))
        c2_1._tc.get_or_add_tcPr().append(parse_xml(f'<w:vAlign {nsdecls("w")} w:val="center"/>'))
        p = c2_1.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        format_run(p.add_run(self.data.get("lab_name", "计算机专业综合实验")), font_cn="黑体", font_en="Arial", size_pt=8.5, bold=True)

        c2_6 = t0.cell(2, 2)
        c2_6._tc.get_or_add_tcPr().append(parse_xml(f'<w:tcW {nsdecls("w")} w:w="1276" w:type="dxa"/>'))
        c2_6._tc.get_or_add_tcPr().append(parse_xml(f'<w:vAlign {nsdecls("w")} w:val="center"/>'))
        p = c2_6.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        format_run(p.add_run("成绩评定"), font_cn="黑体", size_pt=8.5, bold=True)

        c2_7 = t0.cell(2, 3)
        c2_7._tc.get_or_add_tcPr().append(parse_xml(f'<w:tcW {nsdecls("w")} w:w="1559" w:type="dxa"/>'))

        # Row 3: 所用仪器材料
        t0.cell(3, 1).merge(t0.cell(3, 7))
        c3_0 = t0.cell(3, 0)
        c3_0._tc.get_or_add_tcPr().append(parse_xml(f'<w:tcW {nsdecls("w")} w:w="959" w:type="dxa"/>'))
        c3_0._tc.get_or_add_tcPr().append(parse_xml(f'<w:vAlign {nsdecls("w")} w:val="center"/>'))
        p = c3_0.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        format_run(p.add_run("所\n用\n仪\n器\n材\n料"), font_cn="黑体", size_pt=8.5, bold=True)

        c3_1 = t0.cell(3, 1)
        c3_1._tc.get_or_add_tcPr().append(parse_xml(f'<w:tcW {nsdecls("w")} w:w="8505" w:type="dxa"/>'))
        c3_1._tc.get_or_add_tcPr().append(parse_xml(f'<w:vAlign {nsdecls("w")} w:val="center"/>'))
        p = c3_1.paragraphs[0]
        set_para_format(p, line_spacing=1.1, space_before=1.0, space_after=1.0)
        format_run(p.add_run(self.data.get("instruments", "微型计算机、相关专业仿真软件与开发调试环境。")), font_cn="宋体", font_en="Times New Roman", size_pt=8.2)

        # Row 4: 实验目的或要求
        t0.cell(4, 1).merge(t0.cell(4, 7))
        r4 = t0.rows[4]
        r4._tr.get_or_add_trPr().append(parse_xml(f'<w:trHeight {nsdecls("w")} w:val="7200" w:hRule="atLeast"/>'))

        c4_0 = t0.cell(4, 0)
        c4_0._tc.get_or_add_tcPr().append(parse_xml(f'<w:tcW {nsdecls("w")} w:w="959" w:type="dxa"/>'))
        c4_0._tc.get_or_add_tcPr().append(parse_xml(f'<w:vAlign {nsdecls("w")} w:val="center"/>'))
        p = c4_0.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        format_run(p.add_run("实\n验\n目\n的\n或\n要\n求"), font_cn="黑体", size_pt=9.5, bold=True)

        c4_1 = t0.cell(4, 1)
        c4_1._tc.get_or_add_tcPr().append(parse_xml(f'<w:tcW {nsdecls("w")} w:w="8505" w:type="dxa"/>'))
        c4_1._tc.get_or_add_tcPr().append(parse_xml(f'<w:vAlign {nsdecls("w")} w:val="top"/>'))
        c4_1.paragraphs[0].text = ""

        purposes = self.data.get("purposes", [])
        for idx, item in enumerate(purposes):
            add_heading(c4_1, f"{idx+1}. {item.get('title', '')}", level=2)
            add_p(c4_1, item.get("desc", ""))

    def build_page2(self):
        add_col_break(self.doc)
        c_p2 = create_container_table(self.doc, "实\n\n验\n\n原\n\n理", min_height_dxa=11200)
        principles = self.data.get("principles", [])
        for idx, p_item in enumerate(principles):
            add_heading(c_p2, f"{idx+1}. {p_item.get('title', '')}", level=2)
            add_p(c_p2, p_item.get("summary", ""))
            for sub in p_item.get("items", []):
                add_p(c_p2, sub.get("text", ""), bold_prefix=sub.get("prefix", "• "), indent=1)

    def build_page3(self):
        s2 = self.doc.add_section(docx.enum.section.WD_SECTION.NEW_PAGE)
        configure_b4_section(s2, 3, 4)
        c_p3 = create_container_table(self.doc, "实\n验\n过\n程\n或\n内\n容\n、\n结\n果\n、\n分\n析\n、\n讨\n论\n、\n结\n论", min_height_dxa=11200)
        
        proc_part1 = self.data.get("process_part1", {})
        if proc_part1.get("main_title"):
            add_heading(c_p3, proc_part1["main_title"], level=1)
        
        for sec in proc_part1.get("sections", []):
            add_heading(c_p3, sec.get("title", ""), level=2)
            for p in sec.get("paragraphs", []):
                add_p(c_p3, p)
            if sec.get("image"):
                add_img(c_p3, sec["image"]["path"], width_in=sec["image"].get("width", 4.0), caption=sec["image"].get("caption"))
            for ana in sec.get("analyses", []):
                add_p(c_p3, ana.get("text", ""), bold_prefix=ana.get("prefix"))

    def build_page4(self):
        add_col_break(self.doc)
        c_p4 = create_container_table(self.doc, "实\n验\n过\n程\n或\n内\n容\n、\n结\n果\n、\n分\n析\n、\n讨\n论\n、\n结\n论\n（\n续\n）", min_height_dxa=11200)
        
        proc_part2 = self.data.get("process_part2", {})
        if proc_part2.get("main_title"):
            add_heading(c_p4, proc_part2["main_title"], level=1)
            
        for sec in proc_part2.get("sections", []):
            add_heading(c_p4, sec.get("title", ""), level=2)
            for p in sec.get("paragraphs", []):
                add_p(c_p4, p)
            if sec.get("image"):
                add_img(c_p4, sec["image"]["path"], width_in=sec["image"].get("width", 4.0), caption=sec["image"].get("caption"))
            for item in sec.get("items", []):
                add_p(c_p4, item.get("text", ""), bold_prefix=item.get("prefix"), indent=1)
                
            if sec.get("table"):
                t_data = sec["table"]
                rows = len(t_data["rows"])
                cols = len(t_data["rows"][0])
                tbl = c_p4.add_table(rows=rows, cols=cols)
                tbl.autofit = False
                tblPr = tbl._tbl.tblPr
                tblPr.append(parse_xml(f'<w:tblW {nsdecls("w")} w:w="{t_data.get("width_dxa", "8300")}" w:type="dxa"/>'))
                tblPr.append(parse_xml(f'<w:tblInd {nsdecls("w")} w:w="80" w:type="dxa"/>'))
                tblPr.append(parse_xml(
                    f'<w:tblBorders {nsdecls("w")}>'
                    f'  <w:top w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
                    f'  <w:left w:val="none"/>'
                    f'  <w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
                    f'  <w:right w:val="none"/>'
                    f'  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/>'
                    f'  <w:insideV w:val="none"/>'
                    f'</w:tblBorders>'
                ))
                col_widths = t_data.get("col_widths_dxa", ["1600"] + ["3350"]*(cols-1))
                for r_i, row in enumerate(t_data["rows"]):
                    for c_i, val in enumerate(row):
                        cell_c = tbl.cell(r_i, c_i)
                        cell_c._tc.get_or_add_tcPr().append(parse_xml(f'<w:tcW {nsdecls("w")} w:w="{col_widths[c_i]}" w:type="dxa"/>'))
                        p_t = cell_c.paragraphs[0]
                        set_para_format(p_t, align=WD_ALIGN_PARAGRAPH.CENTER if (r_i == 0 or c_i == 0) else WD_ALIGN_PARAGRAPH.LEFT, line_spacing=1.02, space_before=0.5, space_after=0.5)
                        format_run(p_t.add_run(val), font_cn="黑体" if r_i == 0 else "宋体", font_en="Arial", size_pt=7.2, bold=(r_i == 0))

    def build_page5(self):
        s3 = self.doc.add_section(docx.enum.section.WD_SECTION.NEW_PAGE)
        configure_b4_section(s3, 5, 6)
        c_p5 = create_container_table(self.doc, "附\n\n原\n\n始\n\n实\n\n验\n\n记\n\n录", min_height_dxa=11200)
        
        records = self.data.get("raw_records", [])
        for rec in records:
            add_heading(c_p5, rec.get("title", ""), level=2)
            if rec.get("type") == "table":
                t_data = rec["table"]
                rows = len(t_data["rows"])
                cols = len(t_data["rows"][0])
                tbl = c_p5.add_table(rows=rows, cols=cols)
                tbl.autofit = False
                tblPr = tbl._tbl.tblPr
                tblPr.append(parse_xml(f'<w:tblW {nsdecls("w")} w:w="{t_data.get("width_dxa", "8400")}" w:type="dxa"/>'))
                tblPr.append(parse_xml(f'<w:tblInd {nsdecls("w")} w:w="50" w:type="dxa"/>'))
                tblPr.append(parse_xml(
                    f'<w:tblBorders {nsdecls("w")}>'
                    f'  <w:top w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
                    f'  <w:left w:val="none"/>'
                    f'  <w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
                    f'  <w:right w:val="none"/>'
                    f'  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="E0E0E0"/>'
                    f'  <w:insideV w:val="none"/>'
                    f'</w:tblBorders>'
                ))
                col_widths = t_data.get("col_widths_dxa", ["1200", "1600", "2000", "2400", "1200"])
                for r_i, r_data in enumerate(t_data["rows"]):
                    for c_i, val in enumerate(r_data):
                        cell = tbl.cell(r_i, c_i)
                        cell._tc.get_or_add_tcPr().append(parse_xml(f'<w:tcW {nsdecls("w")} w:w="{col_widths[c_i]}" w:type="dxa"/>'))
                        p_cell = cell.paragraphs[0]
                        set_para_format(p_cell, align=WD_ALIGN_PARAGRAPH.CENTER if (r_i == 0 or c_i in [0, 4]) else WD_ALIGN_PARAGRAPH.LEFT, line_spacing=1.02, space_before=0.5, space_after=0.5)
                        lines = val.replace('\\n', '\n').split('\n')
                        for l_i, line in enumerate(lines):
                            if l_i > 0:
                                p_cell.add_run()._r.append(parse_xml(f'<w:br {nsdecls("w")}/>'))
                            r_val = p_cell.add_run(line)
                            format_run(r_val, font_cn="黑体" if r_i == 0 else "宋体", font_en="Consolas" if ("." in line or "Fa" in line or "Se" in line or "10." in line or "20." in line) else "Times New Roman", size_pt=7.2, bold=(r_i == 0))
            elif rec.get("type") == "code":
                add_code(c_p5, rec.get("code_lines", []))
            elif rec.get("type") == "images":
                for img in rec.get("images", []):
                    add_img(c_p5, img["path"], width_in=img.get("width", 4.0), caption=img.get("caption"))

    def build_page6(self):
        add_col_break(self.doc)
        c_p6 = create_container_table(self.doc, "附\n\n原\n\n始\n\n实\n\n验\n\n记\n\n录\n（\n续\n）", min_height_dxa=11200)
        
        add_heading(c_p6, "【课后思考题全套深度题解】", level=1)
        questions = self.data.get("questions", [])
        for idx, q in enumerate(questions):
            add_heading(c_p6, f"{idx+1}. {q.get('question', '')}", level=2)
            if q.get("intro"):
                add_p(c_p6, q["intro"])
            for ans_item in q.get("answers", []):
                add_p(c_p6, ans_item.get("text", ""), bold_prefix=ans_item.get("prefix"), indent=1)
            if q.get("steps"):
                for step in q["steps"]:
                    add_p(c_p6, step.get("text", ""), bold_prefix=step.get("prefix"), indent=1)
                    
        add_heading(c_p6, "【实验总结与反思】", level=1)
        summary_text = self.data.get("summary", "本次实验综合将理论与工程实践深度融合，建立了严谨的系统性工程思维。")
        add_p(c_p6, summary_text)

    def generate(self, docx_path, pdf_path=None):
        # Sheet 1
        s1 = self.doc.sections[0]
        configure_b4_section(s1, 1, 2)
        self.build_page1()
        self.build_page2()
        
        # Sheet 2
        self.build_page3()
        self.build_page4()
        
        # Sheet 3
        self.build_page5()
        self.build_page6()
        
        # 保存 Docx
        os.makedirs(os.path.dirname(os.path.abspath(docx_path)), exist_ok=True)
        self.doc.save(docx_path)
        print(f"[Success] DOCX generated: {docx_path}")
        
        if pdf_path:
            self.export_pdf(docx_path, pdf_path)
            
    def export_pdf(self, docx_path, pdf_path):
        os.makedirs(os.path.dirname(os.path.abspath(pdf_path)), exist_ok=True)
        try:
            import win32com.client
            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            word.DisplayAlerts = False
            try:
                wdoc = word.Documents.Open(os.path.abspath(docx_path))
                wdoc.SaveAs(os.path.abspath(pdf_path), FileFormat=17)
                wdoc.Close()
                print(f"[Success] PDF exported via Word COM: {pdf_path}")
            except Exception as e:
                print(f"[Error] Failed to export PDF via Word COM: {e}")
                raise e
            finally:
                word.Quit()
        except ImportError:
            print("[Warning] win32com not available. To export PDF directly on Windows, install pywin32.")


# 向下兼容别名
SUSELabReportBuilder = UniversalLabReportBuilder


def main():
    parser = argparse.ArgumentParser(description="Universal College Lab Report Engine (大学通用实验报告生成引擎)")
    parser.add_argument("--config", required=True, help="Path to lab report JSON definition")
    parser.add_argument("--out-docx", required=True, help="Output .docx file path")
    parser.add_argument("--out-pdf", help="Output .pdf file path")
    parser.add_argument("--university", help="Override university name (e.g. 清华大学)")
    parser.add_argument("--department", help="Override department/college name")
    parser.add_argument("--major", help="Override student major")
    parser.add_argument("--class-num", help="Override student class number")
    parser.add_argument("--name", help="Override student name")
    parser.add_argument("--student-id", help="Override student ID")
    parser.add_argument("--date", help="Override report date")
    args = parser.parse_args()
    
    with open(args.config, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    student_info = data.get("student_info", {})
    if args.university:
        student_info["university"] = args.university
    if args.department:
        student_info["department"] = args.department
    if args.major:
        student_info["major"] = args.major
    if args.class_num:
        student_info["class_num"] = args.class_num
    if args.name:
        student_info["name"] = args.name
    if args.student_id:
        student_info["student_id"] = args.student_id
    if args.date:
        student_info["date"] = args.date
    data["student_info"] = student_info
        
    builder = UniversalLabReportBuilder(data)
    builder.generate(args.out_docx, args.out_pdf)

if __name__ == "__main__":
    main()
