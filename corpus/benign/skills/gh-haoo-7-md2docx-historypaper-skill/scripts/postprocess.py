#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""postprocess.py — 对 build_paper.py 产出的 docx 做 XML 规范化

用法：
    python3 postprocess.py <docx路径> <spec.json>

修复六件事（都是 editor_sdk 工具链不暴露或实现有误的，详见 references/pitfalls.md）：
1. styles.xml docDefaults：对齐 end→both；首行缩进补 firstLineChars=200（按字号自适应2字符）
2. document.xml：正文 run 的西文字体 SimSun→Times New Roman（中文保持宋体）
3. sectPr：写入 footnotePr（decimalEnclosedCircle ①编号 + eachPage 每页重排）
4. footnotes.xml：整体重建——补 separator/continuationSeparator；脚注 id 顺延+2；
   每个脚注段按规格重排（宋体/Times New Roman 小五、无首行缩进、单倍行距、文献题名斜体）
5. docProps/core.xml：写入论文标题
"""
import zipfile, shutil, os, re, sys, io, json

FONT_RPR_T = ('<w:rFonts w:hint="eastAsia" w:ascii="Times New Roman" '
              'w:hAnsi="Times New Roman" w:eastAsia="宋体"/>')

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def split_runs(text, italics):
    """按斜体子串列表切分文本 → [(segment, italic_bool), ...]（跳过重叠匹配）"""
    marks = []
    for it in italics:
        start = 0
        while True:
            p = text.find(it, start)
            if p < 0:
                break
            marks.append((p, p + len(it)))
            start = p + len(it)
    marks.sort()
    cleaned = []
    for a, b in marks:
        if any(not (b <= c or a >= d) for c, d in cleaned):
            continue
        cleaned.append((a, b))
    segs, pos = [], 0
    for a, b in cleaned:
        if a > pos:
            segs.append((text[pos:a], False))
        segs.append((text[a:b], True))
        pos = b
    if pos < len(text):
        segs.append((text[pos:], False))
    return segs

def main():
    src = sys.argv[1]
    with io.open(sys.argv[2], encoding="utf-8") as f:
        spec = json.load(f)
    FOOTNOTES = {int(k): v for k, v in spec["footnotes"].items()}
    TITLE = spec["title"]
    fsize = int(spec["format"].get("footnote_size", 9) * 2)  # pt → 半磅
    FONT_RPR = FONT_RPR_T + '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (fsize, fsize)
    SEP = ('<w:footnote w:type="separator" w:id="-1"><w:p><w:pPr>'
           '<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'
           '</w:pPr><w:r><w:separator/></w:r></w:p></w:footnote>'
           '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:pPr>'
           '<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'
           '</w:pPr><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>')

    def build_footnote(fid, text, italics):
        parts = ['<w:footnote w:id="%d">' % fid,
                 '<w:p><w:pPr>'
                 '<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'
                 '<w:ind w:firstLine="0" w:firstLineChars="0"/>'
                 '<w:jc w:val="both"/>'
                 '<w:rPr>%s</w:rPr></w:pPr>' % FONT_RPR,
                 '<w:r><w:rPr>%s<w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>' % FONT_RPR,
                 '<w:r><w:rPr>%s</w:rPr><w:t xml:space="preserve"> </w:t></w:r>' % FONT_RPR]
        for seg, it in split_runs(text, italics):
            rpr = FONT_RPR + ("<w:i/>" if it else "")
            parts.append('<w:r><w:rPr>%s</w:rPr><w:t xml:space="preserve">%s</w:t></w:r>' % (rpr, esc(seg)))
        parts.append('</w:p></w:footnote>')
        return "".join(parts)

    tmp = src + ".tmp"
    zin = zipfile.ZipFile(src, "r")
    names = zin.namelist()
    data = {n: zin.read(n) for n in names}
    zin.close()

    # 1. styles.xml：docDefaults 对齐 + 首行缩进Chars
    st = data["word/styles.xml"].decode("utf-8")
    m = re.search(r"(<w:docDefaults>.*?</w:docDefaults>)", st, re.S)
    if m:
        dd = m.group(1)
        dd2 = dd.replace('<w:jc w:val="end"/>', '<w:jc w:val="both"/>')
        if dd2 == dd:
            dd2 = dd.replace("<w:pPrDefault>", '<w:pPrDefault><w:jc w:val="both"/>', 1)
        dd2 = dd2.replace('<w:ind w:firstLine="480"/>',
                          '<w:ind w:firstLine="480" w:firstLineChars="200"/>')
        st = st.replace(m.group(1), dd2)
        data["word/styles.xml"] = st.encode("utf-8")

    # 2/3. document.xml：西文字体 + sectPr footnotePr（引用 id 顺延在脚注重建分支内同步做）
    doc = data["word/document.xml"].decode("utf-8")
    n_fix = doc.count('w:ascii="SimSun" w:hAnsi="SimSun"')
    doc = doc.replace('w:ascii="SimSun" w:hAnsi="SimSun"',
                      'w:ascii="Times New Roman" w:hAnsi="Times New Roman"')
    if "<w:footnotePr>" not in doc:
        doc = doc.replace("<w:sectPr>",
                          '<w:sectPr><w:footnotePr><w:numFmt w:val="decimalEnclosedCircle"/>'
                          '<w:numRestart w:val="eachPage"/></w:footnotePr>', 1)
    data["word/document.xml"] = doc.encode("utf-8")

    # 4. footnotes.xml 整体重建（幂等：已含 separator 条目即判定处理过，跳过）
    fn = data["word/footnotes.xml"].decode("utf-8")
    if 'w:type="separator"' in fn:
        print("detected already post-processed (separator present), skip footnote rebuild")
        fn_count = len(re.findall(r'<w:footnote w:id="\d+">', fn))
        assert fn_count == len(FOOTNOTES), (
            "文档已有 %d 条脚注，spec 声明 %d 条；若文档被外部改动过，"
            "请从 build_paper.py 重新生成" % (fn_count, len(FOOTNOTES)))
    else:
        n_existing = len(re.findall(r'<w:footnote w:id="\d+">', fn))
        assert n_existing == len(FOOTNOTES), (
            "文档现有 %d 条脚注，spec 声明 %d 条；检查 spec 是否存在未引用的孤儿脚注"
            "（build 阶段的断言应已拦截，若从外部文档进入请核对）" % (n_existing, len(FOOTNOTES)))
        root_m = re.match(r"(<\?xml[^>]*\?>\s*<w:footnotes[^>]*>)(.*)(</w:footnotes>)", fn, re.S)
        assert root_m, "footnotes.xml root not matched"
        body = [SEP]
        for old_id in range(len(FOOTNOTES)):
            item = FOOTNOTES[old_id + 1]
            body.append(build_footnote(old_id + 2, item["text"], item.get("italics") or []))
        fn = root_m.group(1) + "".join(body) + root_m.group(3)
        # 引用 id 顺延 +2（与上面重建同步，仅首次运行时进入本分支）
        doc = data["word/document.xml"].decode("utf-8")
        doc = re.sub(r'<w:footnoteReference w:id="(\d+)"/>',
                     lambda mo: '<w:footnoteReference w:id="%d"/>' % (int(mo.group(1)) + 2), doc)
        data["word/document.xml"] = doc.encode("utf-8")
    data["word/footnotes.xml"] = fn.encode("utf-8")

    # 5. core.xml 标题
    if "docProps/core.xml" in data:
        core = data["docProps/core.xml"].decode("utf-8")
        if "<dc:title>" in core:
            core = re.sub(r"<dc:title>.*?</dc:title>", "<dc:title>%s</dc:title>" % esc(TITLE), core)
        else:
            core = core.replace("</cp:coreProperties>",
                                "<dc:title>%s</dc:title></cp:coreProperties>" % esc(TITLE))
        data["docProps/core.xml"] = core.encode("utf-8")

    zout = zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED)
    for n in names:
        zout.writestr(n, data[n])
    zout.close()
    shutil.move(tmp, src)
    print("post-processed ok (font-runs fixed=%d, footnotes=%d)" % (n_fix, len(FOOTNOTES)))

if __name__ == "__main__":
    main()
