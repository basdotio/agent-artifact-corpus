#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_pipeline.py — md2docx-historypaper-skill 离线回归测试

不依赖 editor_sdk / Zotero / 网络：用 fixture 模拟 build 阶段产出的 docx
（edsdk 风格：正文 run 带 SimSun 全槽字体、脚注 Arial 无 pPr、docDefaults 对齐为 end、
脚注 id 从 0 起），然后验证 postprocess / verify_docx 的行为。

运行：<python> tests/test_pipeline.py   （或 python -m unittest discover -s tests -v）
"""
import json, os, subprocess, sys, tempfile, unittest, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKILL, "scripts"))

DOC_H = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

def make_fixture_docx(path, n_footnotes=3):
    """构造 edsdk 风格的未处理后 docx"""
    refs = "".join(
        '<w:r><w:rPr><w:rFonts w:hint="eastAsia" w:ascii="SimSun" w:hAnsi="SimSun" w:eastAsia="SimSun"/>'
        '<w:sz w:val="24"/><w:szCs w:val="24"/><w:vertAlign w:val="superscript"/></w:rPr>'
        '<w:footnoteReference w:id="%d"/></w:r>' % i for i in range(n_footnotes))
    document = (DOC_H + '\n<w:document %s><w:body>'
        '<w:p><w:pPr><w:pStyle w:val="hchh7s"/>'
        '<w:spacing w:before="120" w:after="120" w:line="360" w:lineRule="auto"/>'
        '<w:ind w:firstLineChars="0"/><w:jc w:val="center"/>'
        '<w:rPr><w:rFonts w:ascii="SimSun" w:hAnsi="SimSun" w:eastAsia="SimSun"/><w:sz w:val="24"/></w:rPr></w:pPr>'
        '<w:r><w:rPr><w:rFonts w:hint="eastAsia" w:ascii="黑体" w:hAnsi="黑体" w:eastAsia="黑体"/>'
        '<w:sz w:val="32"/></w:rPr><w:t>测试论文标题</w:t></w:r></w:p>'
        '<w:p><w:pPr><w:pStyle w:val="hchh7s"/></w:pPr>'
        '<w:r><w:rPr><w:rFonts w:hint="eastAsia" w:ascii="SimSun" w:hAnsi="SimSun" w:eastAsia="SimSun"/>'
        '<w:sz w:val="24"/></w:rPr><w:t>正文第一段，含脚注。</w:t></w:r>' + refs + '</w:p>'
        '<w:p w14:paraId="3C249373"/>'
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:right="1800" w:bottom="1440" w:left="1800"/></w:sectPr>'
        '</w:body></w:document>') % W
    styles = (DOC_H + '\n<w:styles %s><w:docDefaults><w:rPrDefault><w:rPr>'
        '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体" w:cs="Times New Roman"/>'
        '<w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr>'
        '<w:spacing w:before="120" w:after="120" w:line="360" w:lineRule="auto"/>'
        '<w:ind w:firstLine="480"/><w:jc w:val="end"/></w:pPr></w:pPrDefault></w:docDefaults>'
        '<w:style w:type="paragraph" w:styleId="hchh7s"><w:name w:val="Normal"/></w:style>'
        '</w:styles>') % W
    fns = [DOC_H + '\n<w:footnotes %s>' % W]
    for i in range(n_footnotes):
        fns.append('<w:footnote w:id="%d"><w:p><w:r>'
                   '<w:rPr><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>'
                   '<w:r><w:rPr><w:rFonts w:hint="eastAsia" w:ascii="Arial" w:hAnsi="Arial"/>'
                   '<w:sz w:val="18"/></w:rPr><w:t xml:space="preserve"> 脚注%d内容。</w:t></w:r>'
                   '</w:p></w:footnote>' % (i, i))
    fns.append('</w:footnotes>')
    footer = (DOC_H + '\n<w:ftr %s><w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
              '<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
              '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>') % W
    core = (DOC_H + '\n<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/"></cp:coreProperties>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
          '<Override PartName="/word/footnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/>'
          '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
          '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
          '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>')
    drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
             '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes" Target="footnotes.xml"/>'
             '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
             '<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/metadata/core-properties" Target="../docProps/core.xml"/>'
             '</Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/footnotes.xml", "".join(fns))
        z.writestr("word/footer1.xml", footer)
        z.writestr("word/_rels/document.xml.rels", drels)
        z.writestr("docProps/core.xml", core)

def make_spec(path, n=3, extra_orphan=False):
    spec = {
        "output": path,
        "format": {"page": {"width": 595.3, "height": 841.9, "top": 72, "bottom": 72, "left": 90, "right": 90},
                   "body": {"east_asia": "宋体", "ascii": "Times New Roman", "size": 12},
                   "line_spacing": 1.5, "spacing_before": 6, "spacing_after": 6,
                   "first_line_indent_pt": 24, "title_font": "黑体", "title_size": 16,
                   "meta_font": "楷体", "meta_size": 12, "h1_font": "黑体", "h1_size": 16,
                   "footnote_size": 9},
        "title": "测试论文标题",
        "meta": [{"label": "摘要：", "text": "测试摘要。"}],
        "blocks": [{"type": "p", "segments": [{"t": "正文第一段，含脚注。"},
                                              {"fn": 1}, {"fn": 2}, {"fn": 3}]}],
        "footnotes": {str(i): {"text": "测试脚注%d。" % i, "italics": []} for i in range(1, n + 1)},
    }
    if extra_orphan:
        spec["footnotes"][str(n + 1)] = {"text": "从未被引用的孤儿脚注。", "italics": []}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False)
    return spec

class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="md2docx-test-")
        self.docx = os.path.join(self.tmp, "fixture.docx")
        self.spec_path = os.path.join(self.tmp, "spec.json")

    def _post(self):
        return subprocess.run([sys.executable, os.path.join(SKILL, "scripts", "postprocess.py"),
                               self.docx, self.spec_path],
                              capture_output=True, text=True, encoding="utf-8")

    def _verify(self):
        return subprocess.run([sys.executable, os.path.join(SKILL, "scripts", "verify_docx.py"),
                               self.docx, "--spec", self.spec_path, "--quiet"],
                              capture_output=True, text=True, encoding="utf-8")

    def test_postprocess_fixes_and_idempotent(self):
        import re
        make_fixture_docx(self.docx, 3)
        make_spec(self.spec_path, 3)
        r = self._post()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        z = zipfile.ZipFile(self.docx)
        doc = z.read("word/document.xml").decode("utf-8")
        fn = z.read("word/footnotes.xml").decode("utf-8")
        st = z.read("word/styles.xml").decode("utf-8")
        self.assertEqual(re.findall(r'<w:footnoteReference w:id="(\d+)"/>', doc), ["2", "3", "4"])
        self.assertIn('w:type="separator"', fn)
        self.assertEqual(re.findall(r'<w:footnote w:id="(\d+)">', fn), ["2", "3", "4"])
        self.assertIn("测试脚注1。", fn)
        self.assertIn("decimalEnclosedCircle", doc)
        self.assertIn("eachPage", doc)
        self.assertNotIn('w:ascii="SimSun"', doc)
        self.assertNotIn("Arial", fn)
        m = re.search(r"<w:docDefaults>.*?</w:docDefaults>", st, re.S)
        self.assertIn('w:val="both"', m.group(0))
        self.assertIn('firstLineChars="200"', m.group(0))
        self.assertEqual(self._verify().returncode, 0)
        # 幂等：再跑一次，编号与内容不变
        r2 = self._post()
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
        self.assertIn("skip footnote rebuild", r2.stdout)
        z2 = zipfile.ZipFile(self.docx)
        doc2 = z2.read("word/document.xml").decode("utf-8")
        fn2 = z2.read("word/footnotes.xml").decode("utf-8")
        self.assertEqual(re.findall(r'<w:footnoteReference w:id="(\d+)"/>', doc2), ["2", "3", "4"])
        self.assertIn("测试脚注1。", fn2)
        self.assertEqual(self._verify().returncode, 0)

    def test_orphan_footnote_rejected(self):
        make_fixture_docx(self.docx, 3)
        make_spec(self.spec_path, 3, extra_orphan=True)
        r = self._post()
        self.assertNotEqual(r.returncode, 0, "孤儿脚注必须被断言拦截")
        self.assertIn("AssertionError", r.stderr)

    def test_missing_footnote_rejected(self):
        make_fixture_docx(self.docx, 3)
        make_spec(self.spec_path, 2)  # spec 只声明 2 条，文档有 3 条
        r = self._post()
        self.assertNotEqual(r.returncode, 0, "脚注数不符必须被断言拦截")

if __name__ == "__main__":
    unittest.main(verbosity=2)
