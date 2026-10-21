#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_paper.py — md 论文 → 期刊格式 docx 构建驱动（editor_sdk 通道）

用法：
    python3 build_paper.py <spec.json> [--edsdk-dir <editor_sdk skill 目录>]

spec.json 结构见 references/spec-example.json（本 skill 自带范本，照抄改内容即可）。
核心字段：
    output   交付 docx 路径（正斜杠）
    format   格式配置（页面/字体/行距/缩进/字号）
    title    论文标题
    meta     [{"label":"摘要：","text":"..."}, ...] 摘要/关键词段（楷体）
    blocks   [{"type":"h1","text":"..."}, {"type":"p","segments":[...]}]
             segments: {"t":文本,"fmt":{"bold":true}|{"italic":true}} 或 {"fn":脚注编号}
    footnotes {"1":{"text":"...","italics":["斜体子串",...]}, ...}

流程：create_doc → set_document_style → 逐段插入（runs 带格式）→
占位符〔FNnn〕转真脚注（find → delete → insert_footnote）→ 页码 → save_file。
保存后必须继续跑 postprocess.py 做 XML 规范化（脚注编号/字体/斜体）。
"""
import subprocess, json, os, sys, io, argparse

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
# editor_sdk（edsdk.py）所在目录：默认 WorkBuddy 宿主安装路径，可用环境变量 MD2DOCX_EDSDK_DIR 覆盖
DEFAULT_EDSDK = os.environ.get(
    "MD2DOCX_EDSDK_DIR",
    r"D:\QClaw\WorkBuddy\resources\app.asar.unpacked\resources\plugins\workbuddy-builtin\skills\workbuddy-local-office-edit")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--edsdk-dir", default=DEFAULT_EDSDK)
    args = ap.parse_args()
    with io.open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)
    edsdk = args.edsdk_dir
    tmp = os.path.join(SKILL_DIR, ".tmp")
    os.makedirs(tmp, exist_ok=True)

    def call(tool, a):
        a = dict(a)
        if FILE_ID:
            a.setdefault("file_id", FILE_ID)
        p = os.path.join(tmp, "args.json")
        with io.open(p, "w", encoding="utf-8") as f:
            json.dump(a, f, ensure_ascii=False)
        r = subprocess.run([sys.executable, "edsdk.py", "call", tool, "--json-file", p],
                           cwd=edsdk, capture_output=True, text=True, encoding="utf-8")
        out = (r.stdout or "") + (r.stderr or "")
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    return json.loads(line)
                except Exception:
                    pass
        if '"ok": false' in out:
            raise RuntimeError("call %s failed: %s" % (tool, out[:400]))
        import re as _re
        m = _re.search(r"file_id=([^\s,]+)", out)
        if m:
            return {"file_id": m.group(1)}
        if "saved to" in out or "ok" in out.lower():
            return {"raw": out.strip()[:200]}
        raise RuntimeError("call %s unparseable: %s" % (tool, out[:400]))

    global FILE_ID
    FILE_ID = None

    fmt = spec["format"]
    page = fmt["page"]; body = fmt["body"]

    # 1. 新建文档 + 文档级默认样式（docDefaults）
    r = call("create_doc", {})
    FILE_ID = r["file_id"]
    print("created:", FILE_ID, flush=True)
    call("doc_set_document_style", {
        "default_text_style": {"font_east_asia": body["east_asia"],
                               "font_ascii": body["ascii"], "font_size": body["size"]},
        "default_paragraph_style": {"line_spacing": fmt["line_spacing"], "line_spacing_rule": 1,
                                    "spacing_before": fmt["spacing_before"], "spacing_after": fmt["spacing_after"],
                                    "first_line_indent": fmt["first_line_indent_pt"], "jc": "justify"},
        "page_style": {"page_width": page["width"], "page_height": page["height"],
                       "top_margin": page["top"], "bottom_margin": page["bottom"],
                       "left_margin": page["left"], "right_margin": page["right"]},
    })

    # 2. 标题（黑体大字居中、无缩进）
    r = call("doc_insert_paragraph_with_text", {
        "idx": 0, "text": spec["title"],
        "text_format": {"font_family": fmt["title_font"], "font_size": fmt["title_size"]},
        "paragraph_property": {"jc": "center", "spacing_before": fmt["spacing_before"],
                               "spacing_after": fmt["spacing_after"],
                               "line_spacing": fmt["line_spacing"], "line_spacing_rule": 1}})
    call("doc_modify_paragraph", {"paragraph_id": r["paragraph_id"], "first_line_indent_chars": 0})

    # 3. 摘要/关键词（楷体、无缩进）
    idx = r["next_index"]
    for m in spec.get("meta", []):
        r = call("doc_insert_paragraph_with_text", {
            "idx": idx,
            "runs": [{"text": m["label"], "format": {"font_family": fmt["meta_font"], "font_size": fmt["meta_size"], "bold": True}},
                     {"text": m["text"], "format": {"font_family": fmt["meta_font"], "font_size": fmt["meta_size"]}}],
            "paragraph_property": {"spacing_before": fmt["spacing_before"], "spacing_after": fmt["spacing_after"],
                                   "line_spacing": fmt["line_spacing"], "line_spacing_rule": 1}})
        call("doc_modify_paragraph", {"paragraph_id": r["paragraph_id"], "first_line_indent_chars": 0})
        idx = r["next_index"]

    # 4. 正文块（h1 / p）
    for blk in spec["blocks"]:
        if blk["type"] == "h1":
            r = call("doc_insert_paragraph_with_text", {
                "idx": idx, "text": blk["text"],
                "text_format": {"font_family": fmt["h1_font"], "font_size": fmt["h1_size"]},
                "paragraph_property": {"jc": "left", "spacing_before": fmt["spacing_before"],
                                       "spacing_after": fmt["spacing_after"],
                                       "line_spacing": fmt["line_spacing"], "line_spacing_rule": 1}})
        else:
            runs = []
            for seg in blk["segments"]:
                if "fn" in seg:
                    runs.append({"text": token(seg["fn"]), "format": {}})
                else:
                    runs.append({"text": seg["t"], "format": dict(seg.get("fmt") or {})})
            r = call("doc_insert_paragraph_with_text", {"idx": idx, "runs": runs})
        idx = r["next_index"]
        print("block ok, next=%d" % idx, flush=True)

    # 5. 占位符 → 真脚注（先删 token 再在其原位置插脚注，避免 token 被脚注结构切断）
    used = sorted({seg["fn"] for blk in spec["blocks"] if blk["type"] == "p"
                   for seg in blk["segments"] if "fn" in seg})
    declared = sorted(int(k) for k in spec["footnotes"])
    assert used == declared, (
        "脚注编号不一致：正文占位符引用 %s，spec footnotes 声明 %s。"
        "spec 中不允许存在未被引用的孤儿脚注（删掉或补占位符）" % (used, declared))
    for n in used:
        tk = token(n)
        r = call("doc_find", {"text": tk})
        locs = r.get("locations") or []
        assert locs, "token not found: %s" % tk
        begin = locs[0]["begin"]
        call("doc_find_and_set", {"text": tk, "action": "delete"})
        call("doc_insert_footnote", {"idx": begin, "content": spec["footnotes"][str(n)]["text"]})
        print("fn %d ok" % n, flush=True)

    # 6. 页码（页脚居中）——必须传 section_index
    call("doc_set_page_number", {"position": "center", "format": "decimal", "scope": "whole_doc",
                                 "section_index": 0,
                                 "text_format": {"font_family": "Times New Roman", "font_size": fmt["footnote_size"]}})

    # 7. 保存
    call("save_file", {"file_path": spec["output"]})
    print("saved:", spec["output"], flush=True)

def token(n):
    return "〔FN%02d〕" % n

FILE_ID = None

if __name__ == "__main__":
    main()
