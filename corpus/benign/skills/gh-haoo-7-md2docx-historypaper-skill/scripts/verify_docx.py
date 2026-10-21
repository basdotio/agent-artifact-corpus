#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_docx.py — md2docx-paper 交付前验证（纯本地、无 edsdk 依赖）

用法：
    python3 verify_docx.py <docx> [--spec spec.json] [--quiet]

检查 pitfalls.md 验证清单的全部可机械判定项；全部通过 exit 0，任一失败 exit 1。
带 --spec 时额外核对脚注数量、编号-内容对应与斜体 run 数。
"""
import zipfile, re, sys, json, io, argparse

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("docx")
    ap.add_argument("--spec")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    fails, passes = [], []
    def check(name, ok, detail=""):
        (passes if ok else fails).append((name, detail))
        if not args.quiet:
            print("%s %s%s" % ("[PASS]" if ok else "[FAIL]", name, (" — " + detail) if detail else ""))

    z = zipfile.ZipFile(args.docx)
    check("zip 完整性", z.testzip() is None)
    names = z.namelist()
    check("footnotes.xml 存在", "word/footnotes.xml" in names)
    doc = z.read("word/document.xml").decode("utf-8")
    fn = z.read("word/footnotes.xml").decode("utf-8")
    st = z.read("word/styles.xml").decode("utf-8")

    # 脚注标记与条目一一对应
    refs = re.findall(r'<w:footnoteReference w:id="(\d+)"/>', doc)
    ids = re.findall(r'<w:footnote w:id="(\d+)">', fn)
    check("脚注标记数 = 条目数", len(refs) == len(ids), "refs=%d entries=%d" % (len(refs), len(ids)))
    check("标记与条目 id 一一对应", sorted(set(refs)) == sorted(set(ids)),
          "仅标记有: %s / 仅条目有: %s" % (sorted(set(refs) - set(ids))[:5], sorted(set(ids) - set(refs))[:5]))
    check("脚注 id 不与 separator（-1/0）冲突",
          ids and min(int(i) for i in ids) >= 1,
          "min=%s（后处理产物为 2 起；经编辑器增删脚注后重排为 1 起亦属正常）"
          % (min(ids, key=int) if ids else "-"))

    # separator 与编号格式
    check("separator/continuationSeparator 存在",
          'w:type="separator"' in fn and 'w:type="continuationSeparator"' in fn)
    check("sectPr footnotePr（①编号 + 每页重排）",
          'decimalEnclosedCircle' in doc and 'eachPage' in doc)

    # docDefaults
    m = re.search(r"<w:docDefaults>.*?</w:docDefaults>", st, re.S)
    dd = m.group(0) if m else ""
    check("docDefaults 两端对齐", 'w:val="both"' in dd)
    check("docDefaults 首行缩进2字符（Chars 自适应）", 'firstLineChars="200"' in dd)
    check("docDefaults 中西文字体（TNR/宋体）",
          'w:ascii="Times New Roman"' in dd and 'w:eastAsia="宋体"' in dd)

    # 字体卫生
    check("正文无 SimSun 西文字体", doc.count('w:ascii="SimSun"') == 0)
    check("脚注无 Arial", "Arial" not in fn)
    check("脚注字号为小五（sz=18）", fn.count('w:val="18"') > 0)

    # 标题段
    paras = re.findall(r"<w:p\b[^>]*>.*?</w:p>", doc, re.S)
    if paras:
        p0 = paras[0]
        txt0 = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p0))
        check("标题居中", '<w:jc w:val="center"/>' in p0)
        check("标题黑体大字", 'w:eastAsia="黑体"' in p0 and 'w:val="32"' in p0, txt0[:30])
        check("标题无首行缩进", 'firstLineChars="0"' in p0)

    # 页码
    footers = [n for n in names if "footer" in n]
    page_ok = any("PAGE" in z.read(n).decode("utf-8") for n in footers)
    check("页脚 PAGE 字段", page_ok, "footers=%d" % len(footers))

    # 残留占位符
    check("无残留占位符", "〔FN" not in doc)

    # spec 深度核对
    if args.spec:
        with io.open(args.spec, encoding="utf-8") as f:
            spec = json.load(f)
        F = {int(k): v for k, v in spec["footnotes"].items()}
        check("脚注数量与 spec 一致", len(ids) == len(F), "doc=%d spec=%d" % (len(ids), len(F)))
        # 编号-内容对应（抽验首末各一条）
        for n in (1, len(F)):
            mm = re.search(r'<w:footnote w:id="%d">(.*?)</w:footnote>' % (n + 1), fn, re.S)
            if mm:
                t = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", mm.group(1))).strip()
                check("脚注%d 内容与 spec 对应" % n, t.startswith(F[n]["text"][:12]), t[:40])
        exp_ital = sum(len(v.get("italics") or []) for v in F.values())
        act_ital = fn.count("<w:i/>")
        check("斜体 run 数与 spec 一致", act_ital == exp_ital, "doc=%d spec=%d" % (act_ital, exp_ital))

    print()
    print("结果：%d 通过，%d 失败" % (len(passes), len(fails)))
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
