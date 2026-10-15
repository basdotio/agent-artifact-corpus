#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_card.py — 把现有角色卡（PNG / JSON）拆成可编辑的「卡工程目录」

用法:
    python extract_card.py <卡.png|卡.json> <输出目录>

输出目录结构:
    card.json        角色卡本体字段（可直接编辑再打包）
    worldbook.json   由卡内 character_book 还原的 ST 世界书（若有）
    regex.json       卡内正则数组（若有）
    scripts/*.js     卡内酒馆助手脚本，一文件一脚本（若有）
    原始卡.json      解码出的完整原始卡 JSON（备份，改坏了从这里找）
    底图.png         输入是 PNG 时复制一份作打包底图
    说明.md          若不存在则生成骨架
"""

import base64
import json
import os
import struct
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def fail(msg):
    print(f"[错误] {msg}")
    sys.exit(1)


def save_json(path, obj, indent=4):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)
        f.write("\n")


def decode_png_card(path):
    data = open(path, "rb").read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        fail("不是合法 PNG")
    pos = 8
    found = {}
    while pos + 12 <= len(data):
        (ln,) = struct.unpack(">I", data[pos:pos + 4])
        typ = data[pos + 4:pos + 8]
        payload = data[pos + 8:pos + 8 + ln]
        if typ == b"tEXt":
            keyword, _, text = payload.partition(b"\x00")
            if keyword in (b"chara", b"ccv3"):
                try:
                    found[keyword.decode()] = json.loads(base64.b64decode(text))
                except Exception as e:
                    print(f"[警告] 解析 {keyword.decode()} 块失败：{e}")
        if typ == b"tEXt" and payload.startswith(b"naidata"):
            pass  # NovelAI 元数据，忽略
        pos += 12 + ln
        if typ == b"IEND":
            break
    if "chara" in found:
        return found["chara"]
    if "ccv3" in found:
        return found["ccv3"]
    fail("PNG 中没有找到 chara/ccv3 卡数据（这不是角色卡，或不含元数据）")


def character_book_to_worldbook(cb):
    """character_book -> ST 世界书导入格式"""
    entries = {}
    used_uids = set()
    for i, e in enumerate(cb.get("entries", [])):
        ext = e.get("extensions", {}) or {}
        pos = ext.get("position")
        if pos is None:
            pos = 0 if e.get("position") == "before_char" else 1
        try:
            uid = int(e.get("id"))
        except (TypeError, ValueError):
            uid = i
        # id 缺失/重复/非法时顺延到下一个空闲 uid（真实卡里出现过 id: null / 重复 id）
        while uid in used_uids:
            uid += 1
        used_uids.add(uid)
        entries[str(uid)] = {
            "uid": uid,
            "key": list(e.get("keys", []) or []),
            "keysecondary": list(e.get("secondary_keys", []) or []),
            "comment": e.get("comment", ""),
            "content": e.get("content", ""),
            "constant": bool(e.get("constant", False)),
            "vectorized": bool(ext.get("vectorized", False)),
            "selective": bool(e.get("selective", False)),
            "selectiveLogic": ext.get("selectiveLogic", 0),
            "addMemo": bool(e.get("comment", "").strip()),
            "order": int(e.get("insertion_order", 100)),
            "position": int(pos),
            "disable": not bool(e.get("enabled", True)),
            "depth": ext.get("depth", 4),
            "probability": ext.get("probability", 100),
            "useProbability": bool(ext.get("useProbability", True)),
            "role": ext.get("role", 0),
            "excludeRecursion": bool(ext.get("exclude_recursion", False)),
            "preventRecursion": bool(ext.get("prevent_recursion", False)),
            "delayUntilRecursion": ext.get("delay_until_recursion", False),
            "group": ext.get("group", ""),
            "groupOverride": bool(ext.get("group_override", False)),
            "groupWeight": ext.get("group_weight", 100),
            "scanDepth": ext.get("scan_depth"),
            "caseSensitive": ext.get("case_sensitive"),
            "matchWholeWords": ext.get("match_whole_words"),
            "useGroupScoring": ext.get("use_group_scoring"),
            "automationId": ext.get("automation_id", ""),
            "outletName": ext.get("outlet_name", ""),
            "sticky": ext.get("sticky"),
            "cooldown": ext.get("cooldown"),
            "delay": ext.get("delay"),
            "ignoreBudget": bool(ext.get("ignore_budget", False)),
        }
    return {"name": cb.get("name", ""), "entries": entries}


def collect_card_scripts(data):
    out = []
    ext = data.get("extensions", {}) or {}
    th = ext.get("tavern_helper")
    if isinstance(th, dict):
        trees = th.get("scripts", [])
    elif isinstance(th, list):
        # 兼容旧形态 A：[["scripts", [...]], ["variables", ...]]（Object.fromEntries 型）
        is_pairs = bool(th) and all(isinstance(x, (list, tuple)) and len(x) == 2 and isinstance(x[0], str) for x in th)
        if is_pairs and any(isinstance(x[1], (list, dict)) for x in th):
            trees = dict((k, v) for k, v in th).get("scripts", [])
        else:
            trees = th  # 形态 B：[{"type":"script","value":{…}}]；形态 C：[[name, content], …]
    else:
        legacy = ext.get("TavernHelper_scripts")
        trees = legacy if isinstance(legacy, list) else []

    def walk(items, prefix=""):
        for item in items:
            # 形态 C：[[name, content], …]
            if isinstance(item, (list, tuple)) and len(item) >= 2 and isinstance(item[0], str):
                content = item[1]
                if not isinstance(content, str):
                    content = json.dumps(content, ensure_ascii=False, indent=2)
                out.append({"name": prefix + item[0], "content": content, "enabled": True, "buttons": []})
                continue
            if not isinstance(item, dict):
                continue
            # 形态 B（嵌套）：{"type":"script","value":{id,name,content,…}}
            if "value" in item and isinstance(item.get("value"), dict) and "content" in item["value"]:
                item = item["value"]
            if item.get("type") == "folder":
                walk(item.get("scripts", []), prefix + str(item.get("name", "文件夹")) + "--")
            else:
                content = item.get("content", "")
                if not isinstance(content, str):
                    content = json.dumps(content, ensure_ascii=False, indent=2)
                out.append({
                    "name": prefix + str(item.get("name", "未命名")),
                    "content": content,
                    "enabled": bool(item.get("enabled", True)),
                    "buttons": (item.get("button") or {}).get("buttons", []),
                })
    walk(trees)
    return out


def extract(src, outdir):
    is_png = src.lower().endswith(".png")
    if is_png:
        card = decode_png_card(src)
    else:
        with open(src, "r", encoding="utf-8-sig") as f:
            card = json.load(f)
    if "data" not in card and "name" not in card:
        fail("这看起来不是一个角色卡 JSON")

    data = card.get("data", card)
    os.makedirs(outdir, exist_ok=True)

    # 1. 本体字段
    ext_all = data.get("extensions", {}) or {}
    base = {
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "personality": data.get("personality", ""),
        "scenario": data.get("scenario", ""),
        "first_mes": data.get("first_mes", ""),
        "mes_example": data.get("mes_example", ""),
        "creator_notes": data.get("creator_notes", ""),
        "alternate_greetings": data.get("alternate_greetings", []) or [],
        "tags": data.get("tags", []) or [],
        "creator": data.get("creator", ""),
        "character_version": data.get("character_version", "1.0"),
        "talkativeness": ext_all.get("talkativeness", "0.5"),
        "fav": bool(ext_all.get("fav", False)),
    }
    spec = card.get("spec") or data.get("spec")
    spec_version = card.get("spec_version") or data.get("spec_version")
    if spec:
        base["spec"] = spec
    if spec_version:
        base["spec_version"] = str(spec_version)
    # 保真关键：保留本工具不管理的扩展字段（depth_prompt、第三方编辑器元数据等），打包时原样写回
    reserved = {"regex_scripts", "tavern_helper", "world", "talkativeness", "fav",
                "TavernHelper_scripts", "TavernHelper_characterScriptVariables"}
    extras = {k: v for k, v in ext_all.items() if k not in reserved}
    base["extensions_extra"] = extras
    save_json(os.path.join(outdir, "card.json"), base)
    print(f"[输出] card.json（{base['name']}，规格 {spec or 'chara_card_v2'}）")
    if extras:
        print("[提示] 保留下来的扩展字段（打包时原样写回）：" + "、".join(extras.keys()))

    # 2. 世界书
    cb = data.get("character_book")
    if cb and cb.get("entries"):
        wb = character_book_to_worldbook(cb)
        save_json(os.path.join(outdir, "worldbook.json"), wb)
        print(f"[输出] worldbook.json（{len(wb['entries'])} 条目）")
    else:
        world = (data.get("extensions", {}) or {}).get("world")
        if world:
            print(f"[提示] 本卡未内嵌世界书，但关联了外部世界书「{world}」——需要在酒馆中自行导出该世界书为 worldbook.json 才能一起编辑打包")

    # 3. 正则
    regexes = (data.get("extensions", {}) or {}).get("regex_scripts")
    if isinstance(regexes, list) and regexes:
        save_json(os.path.join(outdir, "regex.json"), regexes)
        print(f"[输出] regex.json（{len(regexes)} 条）")

    # 4. 脚本
    scripts = collect_card_scripts(data)
    if scripts:
        sdir = os.path.join(outdir, "scripts")
        os.makedirs(sdir, exist_ok=True)
        used = set()
        for s in scripts:
            fname = "".join(c for c in s["name"] if c not in '\\/:*?"<>|').strip() or "未命名"
            candidate = fname
            i = 2
            while candidate in used:
                candidate = f"{fname}_{i}"
                i += 1
            used.add(candidate)
            with open(os.path.join(sdir, candidate + ".js"), "w", encoding="utf-8", newline="\n") as f:
                f.write(s["content"])
        print(f"[输出] scripts/（{len(scripts)} 个脚本：" + "、".join(s['name'] for s in scripts) + "）")

    # 5. 原始卡备份 + 底图
    save_json(os.path.join(outdir, "原始卡.json"), card)
    print("[输出] 原始卡.json（完整备份）")
    if is_png:
        dst = os.path.join(outdir, "底图.png")
        with open(src, "rb") as fi, open(dst, "wb") as fo:
            fo.write(fi.read())
        print("[输出] 底图.png（打包时用 --image 底图.png）")

    # 6. 说明骨架
    readme = os.path.join(outdir, "说明.md")
    if not os.path.exists(readme):
        with open(readme, "w", encoding="utf-8", newline="\n") as f:
            f.write(f"# {base['name']} 游玩说明\n\n（用 templates/readme-template.md 补全）\n")
        print("[输出] 说明.md（骨架）")

    print("\n拆分完成。编辑后重新打包：python build_card.py " + outdir)


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    src, outdir = sys.argv[1], sys.argv[2]
    if not os.path.isfile(src):
        fail(f"文件不存在：{src}")
    if os.path.abspath(src).startswith(os.path.abspath(outdir) + os.sep):
        fail("输出目录不能是源文件所在目录的子目录")
    extract(src, outdir)


if __name__ == "__main__":
    main()
