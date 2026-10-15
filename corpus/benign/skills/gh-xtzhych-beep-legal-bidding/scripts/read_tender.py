#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
招标文件读取器 —— 把一份招标/磋商文件拆成可用的四份材料

用法：
    python3 read_tender.py <招标文件> [--out 输出目录] [--ocr]

支持的输入：.pdf / .docx / .doc
    .pdf  —— pdfplumber 抽文本层；无文本层（扫描件）时报错并提示加 --ocr
    .docx —— python-docx，段落 + 表格都能抽
    .doc  —— 走 macOS 自带的 textutil（不依赖 Word）

产出（默认写在输入文件同目录下的「<文件名>_拆解/」）：
    01_原文.txt          全文，供人工检索
    02_项目基本信息.md   项目名称/编号/采购人/预算/时间节点/保证金
    03_评分标准.md       评分表（docx 直接读表；pdf 抽表 + 文本兜底）
    04_风险提示.md       ★条款、废标条款、报价上限、投标有效期

设计原则：**不做静默失败**。
每一项都明确报「找到 / 没找到」，抽不到就说不出口，绝不假装成功。
所有产出文件顶部都盖「须回原文核对」的章 —— 抽取结果只作导航，不作依据。

⚠️ 本脚本与 skill 内其它材料一样：输出是给人看的线索，不是可依赖的结论。
   评标办法、资格条件、报价上限这三项，必须回原文逐字核对后才可用于决策。
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# ── 章节标记（正则，命中即认为是该节的起点）──────────────────────────
SECTIONS = {
    '资格条件': [
        r'供应商[的]?资格要求', r'投标人[的]?资格要求', r'申请人[的]?资格要求',
        r'合格的?[供应投标申请]', r'资格条件', r'资格审查',
    ],
    '评分办法': [
        r'评分标准', r'评审办法', r'评审方法', r'评分办法', r'评标办法',
        r'综合评分法', r'综合评估法', r'磋商办法',
    ],
    '废标条款': [
        r'废标', r'无效投标', r'无效响应', r'否决其投标', r'作无效', r'投标无效',
    ],
    '报价要求': [
        r'最高[投响]标?限价', r'采购预算', r'预算金额', r'报价要求', r'价格分',
    ],
    '时间节点': [
        r'提交响应文件', r'递交投标文件', r'提交投标文件', r'响应文件递交',
        r'投标截止', r'递交截止', r'提交截止', r'开标时间', r'开标', r'磋商时间',
        r'报名', r'获取[招磋]商?文件', r'澄清.*截止', r'答疑', r'踏勘',
    ],
    '保证金': [r'保证金'],
    '投标有效期': [r'投标有效期', r'响应有效期'],
    '封装要求': [r'封装', r'密封', r'装订'],
}

# ── 关键字段（键 → 正则候选列表）────────────────────────────────────
FIELDS = {
    '项目名称': [r'项目名称[：:]\s*(.+)', r'采购项目名称[：:]\s*(.+)'],
    '项目编号': [r'项目编号[：:]\s*(.+)', r'采购编号[：:]\s*(.+)', r'招标编号[：:]\s*(.+)'],
    '采购人': [r'采购人[（(]?[^)）]*[)）]?[：:]\s*(.+)', r'招标人[：:]\s*(.+)'],
    '采购代理机构': [r'采购代理机构[：:]\s*(.+)', r'代理机构[：:]\s*(.+)'],
    '预算金额': [r'(?:预算金额|采购预算|预算|最高限价|最高投标限价)[^0-9]{0,20}([\d,，.]+\s*(?:万元|元))'],
    '保证金': [r'保证金[^0-9]{0,30}([\d,，.]+\s*(?:万元|元))'],
}

RISK_MARKERS = {
    '★条款': [r'★', r'▲'],
    '废标表述': [r'废标', r'无效投标', r'无效响应', r'否决其投标', r'投标无效'],
    '有效期': [r'投标有效期[^0-9]{0,15}(\d+)\s*[天日]', r'响应有效期[^0-9]{0,15}(\d+)\s*[天日]'],
}

MAX_SECTION_LINES = 40      # 每节默认最多摘多少行（全局，不是每命中一次）
MAX_SECTION_HITS = 4        # 同一节最多取前几处命中（计名额的是"有内容的"命中，见下）
MIN_CHUNK_LINES = 3         # 短于这个行数的命中不算数，也不占名额
# 评分办法要留够行数——评分表是整份文件里最该看全的一节。
# 实测（邮储银行标）：评分表从「第三章评标办法」到「报价部分」结束约 120 行，
# 给到 160 才有余量；给少了会正好切在报价分之前，把最容易翻车的一段漏掉。
SECTION_CAP = {'评分办法': 200, '资格条件': 60, '废标条款': 50, '报价要求': 40}

# 目录行：Word 域代码、点线引导、纯页码行。不清掉它们，章节检测会被目录带跑
TOC_RE = re.compile(
    r'HYPERLINK|PAGEREF|TOC\s*\\o|^\s*\.{4,}|[.·]{4,}\s*\d+\s*$|'
    r'^\s*\d{1,3}\s*$|^\s*第[一二三四五六七八九十]+[卷章节]\s*$'
)

DISCLAIMER = (
    '> ⚠️ **本文件由脚本自动抽取，只作导航线索，不作用途依据。**\n'
    '> 资格条件、评标办法、报价上限三项，必须回 `01_原文.txt` 或原件逐字核对。\n'
    '> 抽取时间：{ts}\n\n'
)


def log(msg):
    print(msg, flush=True)


# ══════════════ 文本抽取 ══════════════
def from_pdf(path, ocr=False):
    """返回 (文本, 表格列表, 备注)。"""
    import pdfplumber
    texts, tables, notes = [], [], []
    with pdfplumber.open(path) as pdf:
        n = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            t = page.extract_text() or ''
            texts.append(t)
            for tb in (page.extract_tables() or []):
                if tb and len(tb) > 1:
                    tables.append((i + 1, tb))
        chars = sum(len(t.strip()) for t in texts)
        if chars < n * 50:
            notes.append(f'可疑：{n} 页仅抽到 {chars} 个字符，疑似扫描件或纯图片 PDF。')
            if ocr:
                notes.append('已指定 --ocr，但本脚本不内置 OCR；'
                             '请先用 tesseract 或预览导出文本后再跑。')
    return '\n'.join(texts), tables, notes


def from_docx(path):
    """段落与表格都抽，且**保持原有先后顺序**。

    只抽段落是不够的：招标文件里最要紧的那几项——投标有效期、保证金金额、
    装订份数、评分表——几乎都写在表格里。表格不进文本流，等于最该看的部分
    根本没读，而脚本还会报「未抽到」，让人以为文件里没有。

    表格按行拼成 `甲 | 乙 | 丙`，一行就是原文的一行，
    这样章节标记、字段正则都能像读正文一样读到它。
    """
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    d = Document(path)
    parts, tables = [], []
    for child in d.element.body.iterchildren():
        if child.tag.endswith('}p'):
            parts.append(Paragraph(child, d).text)
        elif child.tag.endswith('}tbl'):
            tb = Table(child, d)
            rows = [[c.text.strip().replace('\n', ' ') for c in r.cells] for r in tb.rows]
            rows = [r for r in rows if any(r)]
            if len(rows) > 1:
                tables.append((f'表{len(tables) + 1}', rows))
                # 表格逐行并入正文，另起一段，行内用竖线分隔（与 03 的渲染一致）
                parts.append('\n'.join(' | '.join(r) for r in rows))
    return '\n'.join(parts), tables, []


def from_doc(path):
    r = subprocess.run(['textutil', '-convert', 'txt', '-stdout', str(path)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f'textutil 转换失败：{r.stderr.strip()[:200]}')
    return r.stdout, [], ['由 .doc 经 textutil 转换，表格结构已丢失，'
                          '如需评分表请另存为 .docx 后重跑。']


def extract(path, ocr=False):
    ext = path.suffix.lower()
    if ext == '.pdf':
        return from_pdf(path, ocr)
    if ext == '.docx':
        return from_docx(path)
    if ext == '.doc':
        return from_doc(path)
    raise SystemExit(f'❌ 不支持的格式：{ext}（只支持 .pdf / .docx / .doc）')


# ══════════════ 解析 ══════════════
def clean_lines(text):
    """去掉目录行与空行。目录不清，章节检测会被目录里的标题带跑。"""
    out = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s or TOC_RE.search(s):
            continue
        out.append(s)
    return out


def norm(s):
    """把标签内部的空格抹掉，好让「招 标 人：」也能匹配「招标人」。"""
    return re.sub(r'[ \t　]+', '', s)


def tidy(val):
    """去掉字段值两侧与尾部的标点、盖章说明。"""
    val = val.strip(' ：:　、，。；;（(【[')
    val = re.sub(r'[）)】\]]*\s*$', '', val)
    val = re.sub(r'（?(?:盖)?(?:单位)?公章）?$', '', val)
    val = re.sub(r'[（(][^)）]{0,10}(?:公章|盖章|签字)[^)）]{0,10}[)）]', '', val)
    # .doc 经 textutil 转换会把勾选框等符号转成乱码（如 "Ρ""□"），
    # 掐掉开头那串非中文非数字的字符，免得带进报告。
    val = re.sub(r'^[^一-鿿\dA-Za-z]{1,6}', '', val)
    # 前面那个乱码多半是勾选框（☑有／□无），转换后只剩个"有，"／"无，"
    val = re.sub(r'^[有无]\s*[，,、]\s*', '', val)
    return val.strip()


XREF_RE = re.compile(r'(详见?|参见|见)\s*(投标人须知|供应商须知|招标文件|磋商文件|'
                     r'前附表|附件|第[一二三四五六七八九十]+[章节条款])')


def find_fields(lines, src_name=''):
    hits = {}
    for key, pats in FIELDS.items():
        for pat in pats:
            for ln in lines[:400]:          # 关键字段通常在开头
                m = re.search(pat, norm(ln))
                if m:
                    val = tidy(m.group(1) if m.groups() else m.group(0))
                    # 抽到的是"见投标人须知前附表"这类交叉引用时不算数——
                    # 那是路标，不是答案，留着比空着更误导。
                    if XREF_RE.search(val):
                        continue
                    if 0 < len(val) <= 80:
                        hits[key] = val
                        break
            if key in hits:
                break
    # 兜底：项目名称常不写"项目名称："，而是封面第一行长标题
    if '项目名称' not in hits:
        for ln in lines[:20]:
            head = norm(ln)
            if (12 <= len(head) <= 60
                    and not re.search(r'[：:]', head)
                    and re.search(r'(项目|服务|采购)', head)):
                hits['项目名称'] = tidy(head)
                break
    if '项目名称' not in hits and src_name:
        hits['项目名称'] = f'（未抽到，见文件名）{src_name}'

    # 预算未必是"多少钱"。法律服务标常写成折扣率（如"不得高于收费标准的80%"）
    # 或"见前附表"。抽不到金额就说"未抽到"，等于把最关键的一个数说成不存在 ——
    # 所以退回按行找，把原话摘出来，并注明不是金额形式。
    if '预算金额' not in hits:
        for ln in lines:
            if XREF_RE.search(norm(ln)):
                continue
            if re.search(r'(最高[投响]标?限价|采购预算|预算金额|报价上限)', norm(ln)):
                body = tidy(ln)
                # 光是"最高投标限价"五个字（表头/目录残留）不算线索。
                # 要求行里得有数字、或有"不得高于/不超过"这类封顶表述，
                # 否则会抓到"本文件中的编号、预算金额、人员姓名均为编造"这种说明文字。
                if not (re.search(r'\d', body)
                        or re.search(r'(不得高于|不得超过|不超过|上限)', body)):
                    continue
                hits['预算金额'] = f'（非金额形式，原文照录）{body[:70]}'
                break
    return hits


TENDER_MARKS = ['投标人须知', '供应商须知', '评标办法', '评审办法',
                '招标公告', '磋商公告', '投标邀请', '采购公告']
SELF_MARKS = ['我方', '本单位', '我单位', '本公司']

# 招标文件最后一章是"投标文件格式"，里面会有投标函模板，因此也会出现"我方"。
# 实测：招标文件里的自称是个位数（邮储标 6 处），投标文件是十几二十处（湟源标 19 处）。
SELF_THRESHOLD = 10


def guess_nature(lines):
    """猜这份文件是招标文件还是投标文件。

    指错文件是很容易发生的事——投标资料夹里两样都有。指错了脚本会报一堆
    「未抽到」，使用者只会以为脚本坏了。所以先认一下，认错了心里有数。

    判据用"自称"：投标文件整篇都在说"我方""我单位"，招标文件是站在采购方立场
    写的，除了格式附件的模板，不会自称"我方"。这比数"投标函"之类的词可靠——
    那些词两边的文件里都有。
    """
    text = '\n'.join(lines[:600])
    self_n = sum(text.count(k) for k in SELF_MARKS)
    tender = [k for k in TENDER_MARKS if k in text]
    if self_n >= SELF_THRESHOLD:
        return '投标文件（我方编写的应答）', len(tender), self_n
    if tender:
        return '招标文件（采购方发出的）', len(tender), self_n
    if self_n > 0:
        return '投标文件（我方编写的应答）', len(tender), self_n
    return '无法判断', len(tender), self_n


def scatter_lines(lines, name, k=8):
    """没找到章节标题时，退一步把全文里含该节关键词的行摘出来。

    报「未抽到」和报「散见 2 行」是两回事：前者让人以为文件里没这回事，
    后者说的是「有，但没有成章的规定」。招标文件里密封装订这类要求
    经常就是夹在正文句子中间的，不该因为不成章就当成不存在。
    """
    pats = SECTIONS.get(name, [])
    out = []
    for ln in lines:
        if any(re.search(p, norm(ln)) for p in pats):
            out.append(ln)
            if len(out) >= k:
                break
    return out


def is_heading(s):
    """判断一行像不像章节起点。

    要挡的是两类假命中：
      「（3）评标办法；」     —— 目录式的列表项，不是章节
      「6.3.1评标委员会按照第三章"评标办法"规定的方法…」 —— 正文条款里的交叉引用，
                                靠长度自然挡掉（真标题不会写到 45 字以上）

    刻意**不**按"数字开头"一刀切：像「3.1.2 投标人有下列情形之一的…否决其投标：」
    这种编号条款本身就是要抓的内容，砍掉它反而漏材料。
    """
    if len(s) > 45 or len(s) < 3:
        return False
    if re.match(r'^[（(]\s*\d+\s*[)）]', s):     # （3）评标办法；  列表项
        return False
    if s.endswith(('；', ';', '。', '，', ',')):
        return False
    return True


def is_strong_heading(s):
    """更强的标题判据：短、且内部没有句读。

    正文里顺带提一句"……按评审方法和评审标准进行评审，负责审议所有响应文件……"
    也能命中关键词，但它是一句散文，不是章节。真正的章节标题短，且不会在
    中间出现逗号句号 —— 这一条把两者分得很干净。
    """
    return is_heading(s) and len(s) <= 25 and not re.search(r'[，。；]', s)


# 章标题：必定是截断点。一份招标文件的章节边界，比任何关键词都可靠。
CHAPTER_RE = re.compile(r'^第\s*[一二三四五六七八九十]+\s*[章卷]')


def slice_sections(lines):
    """按标记把全文切成若干节。只有'像标题'的行才算章节起点，
    每节合计不超过该节上限 —— 不设上限会把全文吞进去。

    同一节里若存在"强标题"，就只用强标题，丢掉那些只是顺带提到关键词的散文行。
    实测（城西司法局磋商文件）：不这么做的话，评分标准那一节的开头会是
    「18.2.1 实质性偏离……按无效文件处理」——那是废标条款，不是评分办法。

    截断点比起点更严格：**只有强标记和章标题才截断。**
    实测（邮储银行标）：评分办法从「第三章评标办法（综合评估法）」开始，
    本该一路走到「2.2.4 评分标准」的评分表；可中间散落着别的节的弱标记
    （保证金、时间节点），每一个都截一刀，结果这一节只取到「形式评审标准」
    就断了——最该看的评分表一个字没进输出。
    起点放宽是为了不漏，截断收紧是为了不碎，两者方向相反才对。
    """
    marks, strong = [], set()
    for i, ln in enumerate(lines):
        if not is_heading(ln):
            continue
        for name, pats in SECTIONS.items():
            if any(re.search(p, ln[:40]) for p in pats):
                marks.append((i, name))
                if is_strong_heading(ln):
                    strong.add(name)
                break
    if strong:
        marks = [m for m in marks if m[1] not in strong or is_strong_heading(lines[m[0]])]
    # 截断点：强标记 ∪ 章标题。弱标记（顺带提到关键词的散文行）不截断。
    cuts = sorted({i for i, _ in marks if is_strong_heading(lines[i])}
                  | {i for i, ln in enumerate(lines) if CHAPTER_RE.match(ln)})

    def next_cut(i):
        """i 之后第一个截断点，没有就到底。"""
        lo, hi = 0, len(cuts)
        while lo < hi:                      # bisect_right，不引 bisect 也行
            mid = (lo + hi) // 2
            if cuts[mid] <= i:
                lo = mid + 1
            else:
                hi = mid
        return cuts[lo] if lo < len(cuts) else len(lines)

    out, count = {}, {}
    for idx, (i, name) in enumerate(marks):
        if count.get(name, 0) >= MAX_SECTION_HITS:
            continue
        cap = SECTION_CAP.get(name, MAX_SECTION_LINES)
        end = next_cut(i)
        room = cap - len(out.get(name, []))
        if room <= 0:
            continue
        chunk = lines[i:min(end, i + room)]
        # 太短的命中不占名额。命中会被"下一个标记"立刻截断——正文里顺带提一句
        # "按本章评审办法"就能产生一个只有一两行的命中。若它照样占掉一个名额，
        # 真正的章节（往往在后面几千字处）就永远轮不上。
        # 实测：城西司法局那份，评分表在第 354 行，却被前面几处空命中挡在门外。
        if len(chunk) < MIN_CHUNK_LINES:
            continue
        out.setdefault(name, []).extend(chunk)
        count[name] = count.get(name, 0) + 1
    return out


DATE_RE = re.compile(r'\d{4}\s*年\s*\d{1,2}\s*月|\d{1,2}\s*月\s*\d{1,2}\s*日')


def find_dates(lines, k=25):
    """把所有带日期的行扫出来。

    时间节点是整份文件里最不能漏的东西——漏一个就是废标，而它偏偏散在各章
    （报名期、澄清截止、投标截止、开标时间分属三四个地方）。按章节抓不可靠，
    所以直接按"这行有日期"来捞，宁滥勿缺。
    """
    out = []
    for ln in lines:
        if DATE_RE.search(norm(ln)):
            out.append(ln)
            if len(out) >= k:
                break
    return out


def find_risks(lines):
    out = {}
    for name, pats in RISK_MARKERS.items():
        found = []
        for i, ln in enumerate(lines):
            for p in pats:
                if re.search(p, ln):
                    m = re.search(p, ln)
                    val = f'（{m.group(1)} 天）' if m.groups() else ''
                    found.append(ln.strip()[:160] + val)
                    break
        if found:
            out[name] = found[:40]
    return out


def tables_to_md(tables, limit=12):
    md = []
    for tag, rows in tables[:limit]:
        md.append(f'\n### 表格：{tag}\n')
        for r in rows[:40]:
            cells = [(c or '').replace('\n', ' ').strip() for c in r]
            md.append('| ' + ' | '.join(cells) + ' |')
            if len(md) > 1 and md[-2].startswith('| 表格') is False and rows.index(r) == 0:
                md.append('|' + '---|' * len(cells))
        md.append('')
    return '\n'.join(md)


# ══════════════ 主流程 ══════════════
def main():
    ap = argparse.ArgumentParser(description='招标文件读取器')
    ap.add_argument('tender', help='招标文件路径（.pdf/.docx/.doc）')
    ap.add_argument('--out', help='输出目录（默认与输入同级的 <文件名>_拆解/）')
    ap.add_argument('--ocr', action='store_true', help='提示扫描件处理')
    args = ap.parse_args()

    src = Path(args.tender).expanduser().resolve()
    if not src.exists():
        raise SystemExit(f'❌ 文件不存在：{src}')

    outdir = Path(args.out).expanduser() if args.out else src.parent / f'{src.stem}_拆解'
    outdir.mkdir(parents=True, exist_ok=True)

    log(f'📄 读取：{src.name}（{src.stat().st_size / 1024:,.0f} KB）')
    text, tables, notes = extract(src, args.ocr)
    raw_lines = [l for l in text.splitlines() if l.strip()]
    lines = clean_lines(text)
    dropped = len(raw_lines) - len(lines)
    log(f'   抽出 {len(lines):,} 行 / {len(text):,} 字符 / {len(tables)} 张表'
        + (f'（另剔除目录与空行 {dropped:,} 行）' if dropped > 0 else ''))

    import datetime
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    stamp = DISCLAIMER.format(ts=ts)

    # 01 原文
    (outdir / '01_原文.txt').write_text(text, encoding='utf-8')

    # 02 基本信息
    nature, tn, bn = guess_nature(lines)
    fields = find_fields(lines, src.stem)
    buf = [stamp, '# 项目基本信息（脚本抽取）\n']
    buf.append(f'> **文件性质判断：{nature}**（招标类标记 {tn} 个／自称 {bn} 处）\n')
    if nature.startswith('投标'):
        buf.append('> ⚠️ 这看起来是**投标文件**，不是招标文件。\n'
                   '> 投标文件里不会有资格条件、评标办法、报价上限——那些在招标方发的文件里。\n'
                   '> 下面的「未抽到」是正常的，不是脚本坏了。\n')
    for k in FIELDS:
        buf.append(f'- **{k}**：{fields.get(k, "⚠️ 未抽到 —— 请回原文找")}')
    if notes:
        buf.append('\n## 抽取备注\n')
        for n in notes:
            buf.append(f'- ⚠️ {n}')
    (outdir / '02_项目基本信息.md').write_text('\n'.join(buf), encoding='utf-8')

    # 03 评分标准
    secs = slice_sections(lines)
    buf = [stamp, '# 评分标准与资格条件（脚本抽取）\n']
    for name in ('评分办法', '资格条件', '报价要求', '投标有效期', '封装要求'):
        got = secs.get(name)
        if got:
            buf.append(f'\n## {name}（命中 {len(got)} 行）\n')
            # 不再 [:60] 截断：控制台报的是 len(got)，文件里却只写 60 行，
            # 看到的和报出来的对不上，等于又一处"沉默地少给你一半"。
            # 行数上限由 slice_sections 的 SECTION_CAP 管，一处管就够了。
            buf += [f'> {l.strip()}' for l in got]
        else:
            sc = scatter_lines(lines, name)
            if sc:
                buf.append(f'\n## {name}（未成章节；散见 {len(sc)} 行）\n')
                buf.append('> 没有找到该节的标题。以下是全文里提到这件事的地方，'
                           '可能只是顺带一句，**不等于就是要求**，请回原文看上下文。\n')
                buf += [f'> {l.strip()}' for l in sc]
            else:
                buf.append(f'\n## {name}\n\n⚠️ **没有找到** —— 全文连相关字眼都没有。'
                           '请确认招标文件是否用了别的说法。')
    if tables:
        buf.append('\n---\n# 原文件中的表格\n')
        buf.append(tables_to_md(tables))
    (outdir / '03_评分标准.md').write_text('\n'.join(buf), encoding='utf-8')

    # 04 风险提示
    risks = find_risks(lines)
    buf = [stamp, '# 风险提示（脚本抽取）\n']
    buf.append('本文件只做**提示**：下面每一条都要回原文确认适用范围。\n')
    for name in ('★条款', '废标表述', '有效期'):
        got = risks.get(name)
        if got:
            buf.append(f'\n## {name}（命中 {len(got)} 处）\n')
            buf += [f'{i + 1}. {l}' for i, l in enumerate(got[:30])]
        else:
            buf.append(f'\n## {name}\n\n未抽到。**这不等于不存在** —— '
                       '招标文件的★条款有时是图片或特殊符号，请人工过一遍。')

    # 章节形态的废标条款 / 保证金 / 时间节点。
    # 上面那三个是"散见"视图（全文提到就列一行），这里是**成章节的原文**——
    # 散见能提醒你"有这回事"，成章节才看得出"整段要求是什么"。两者都要。
    for name in ('废标条款', '保证金', '时间节点'):
        got = secs.get(name)
        if got:
            buf.append(f'\n## {name}（成章节的原文章节，{len(got)} 行）\n')
            buf += [f'> {l.strip()}' for l in got]

    dates = find_dates(lines)
    if dates:
        # 名字要和上面那节「时间节点」区分开：那节是原文里讲递交/开标的章节，
        # 这节是"全文凡带日期的行"，两者不是一回事，名字像会让人以为重复了。
        buf.append(f'\n## 原文中所有带日期的行（{len(dates)} 行）\n')
        buf.append('漏一个期限就是废标，所以这里宁可多列。请按下面的日期倒推自己的进度。\n')
        buf += [f'{i + 1}. {l.strip()[:150]}' for i, l in enumerate(dates)]

    buf.append('\n---\n\n**下一步**：03_评分标准.md 里的资格条件与评分表，'
               '必须回 01_原文.txt 逐条核对；本文件的清单只用来提醒你"该去看什么"。')
    (outdir / '04_风险提示.md').write_text('\n'.join(buf), encoding='utf-8')

    # ── 控制台小结（明确报命中／未命中）──
    log('')
    log('─' * 58)
    log(f'文件性质：{nature}（招标类标记 {tn} 个／自称 {bn} 处）')
    if nature.startswith('投标'):
        log('  ⚠️ 这看起来是投标文件，不是招标文件 —— 未抽到资格条件/评标办法是正常的。')
    log('')
    log('抽取结果：')
    for k in FIELDS:
        mark = '✅' if k in fields else '⚠️ 未抽到'
        log(f'  {mark:10} {k}' + (f'：{fields[k]}' if k in fields else ''))
    log('')
    for name in SECTIONS:
        n = len(secs.get(name, []))
        if n:
            log(f'  {"✅":10} {name}（{n} 行）')
        else:
            sc = len(scatter_lines(lines, name))
            note = f'（未成章节，散见 {sc} 行）' if sc else '（全文无此字眼）'
            log(f'  {"⚠️ 未成章节" if sc else "⚠️ 未抽到":10} {name}{note}')
    log('')
    log(f'  {"✅" if tables else "⚠️ 无表":10} 表格 {len(tables)} 张')
    for n in notes:
        log(f'  ⚠️ {n}')
    log('─' * 58)
    log(f'📁 产出：{outdir}')
    log('')
    log('⚠️ 抽取结果只作导航。资格条件、评标办法、报价上限三项必须回原文核对。')


if __name__ == '__main__':
    main()
