#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_card.py — 把「角色卡工程」打包成完备角色卡（JSON / PNG）

用法:
    python build_card.py <卡工程目录> [--image 底图.png] [--outdir 输出] [--name 卡名]

工程目录结构（见 SKILL.md）:
    card.json        角色卡本体字段（必须）
    worldbook.json   世界书（ST 导入格式，可选）
    regex.json       正则数组（ST 导入格式，可选）
    scripts/*.js     酒馆助手角色脚本，文件名即脚本名（可选）
    meta.json        可选：{"scripts_disabled": ["名"], "script_buttons": {"名": [{"name": "...", "visible": true}]}}

输出（默认在 <工程目录>/输出/）:
    <卡名>.json          完备卡 JSON（含 character_book / regex_scripts / tavern_helper 脚本）
    <卡名>.png           给底图时输出（chara + ccv3 两个 tEXt 块）
    世界书.json          独立世界书（备用）
    正则.json            独立正则（备用）
"""

import argparse
import base64
import json
import os
import struct
import sys
import uuid
import zlib
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SCRIPT_NS = uuid.UUID("6f9619ff-8b86-d011-b42d-00c04fc964ff")  # 固定命名空间：脚本 id 跨构建稳定


def log(msg=""):
    print(msg)


def fail(msg):
    print(f"[错误] {msg}")
    sys.exit(1)


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path, obj, indent=4):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)
        f.write("\n")


# ---------------------------------------------------------------------------
# 世界书: ST 格式 -> character_book（内嵌卡格式）
# ST 位置数字表: 0=CharacterBefore 1=CharacterAfter 2=ANTop 3=ANBottom
#                4=atDepth 5=EMTop 6=EMBottom 7=Outlet
# ---------------------------------------------------------------------------

def worldbook_entry_to_character_book_entry(uid, e, display_index):
    pos = int(e.get("position", 1))
    return {
        "id": int(uid),
        "keys": list(e.get("key", []) or []),
        "secondary_keys": list(e.get("keysecondary", []) or []),
        "comment": e.get("comment", ""),
        "content": e.get("content", ""),
        "constant": bool(e.get("constant", False)),
        "selective": bool(e.get("selective", False)),
        "insertion_order": int(e.get("order", 100)),
        "enabled": not bool(e.get("disable", False)),
        "position": "before_char" if pos == 0 else "after_char",
        "use_regex": True,
        "extensions": {
            "position": pos,
            "exclude_recursion": bool(e.get("excludeRecursion", False)),
            "display_index": display_index,
            "probability": e.get("probability", 100),
            "useProbability": bool(e.get("useProbability", True)),
            "depth": e.get("depth", 4),
            "selectiveLogic": e.get("selectiveLogic", 0),
            "outlet_name": e.get("outletName", ""),
            "group": e.get("group", ""),
            "group_override": bool(e.get("groupOverride", False)),
            "group_weight": e.get("groupWeight", 100),
            "prevent_recursion": bool(e.get("preventRecursion", False)),
            "delay_until_recursion": bool(e.get("delayUntilRecursion", False))
            if not isinstance(e.get("delayUntilRecursion", False), bool)
            else e.get("delayUntilRecursion", False),
            "scan_depth": e.get("scanDepth", None),
            "match_whole_words": e.get("matchWholeWords", None),
            "use_group_scoring": e.get("useGroupScoring", None),
            "case_sensitive": e.get("caseSensitive", None),
            "automation_id": e.get("automationId", ""),
            "role": e.get("role", 0),
            "vectorized": bool(e.get("vectorized", False)),
            "sticky": e.get("sticky", None),
            "cooldown": e.get("cooldown", None),
            "delay": e.get("delay", None),
            "match_persona_description": False,
            "match_character_description": False,
            "match_character_personality": False,
            "match_character_depth_prompt": False,
            "match_scenario": False,
            "match_creator_notes": False,
            "triggers": e.get("triggers", []),
            "ignore_budget": bool(e.get("ignoreBudget", False)),
        },
    }


def worldbook_to_character_book(wb):
    entries = wb.get("entries", {})
    ordered = sorted(entries.items(), key=lambda kv: int(kv[0]))
    out_entries = [worldbook_entry_to_character_book_entry(uid, e, i) for i, (uid, e) in enumerate(ordered)]
    return {"name": wb.get("name", ""), "entries": out_entries}


# ---------------------------------------------------------------------------
# PNG: 读写 tEXt 块
# ---------------------------------------------------------------------------

def read_png_chunks(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        fail("底图不是合法 PNG 文件")
    pos, chunks = 8, []
    while pos + 12 <= len(data):
        (ln,) = struct.unpack(">I", data[pos:pos + 4])
        typ = data[pos + 4:pos + 8]
        full = data[pos:pos + 12 + ln]
        if len(full) < 12 + ln:
            fail("PNG 文件被截断")
        chunks.append((typ, full))
        pos += 12 + ln
        if typ == b"IEND":
            break
    return chunks


def text_chunk_bytes(keyword, text):
    payload = keyword.encode("latin-1") + b"\x00" + text.encode("latin-1")
    crc = zlib.crc32(b"tEXt" + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + b"tEXt" + payload + struct.pack(">I", crc)


def strip_st_chunks(chunks):
    """剥掉旧的 chara / ccv3 tEXt 块，避免重复或旧数据残留。"""
    kept = []
    for typ, full in chunks:
        if typ == b"tEXt":
            payload = full[8:-4]
            keyword = payload.split(b"\x00", 1)[0]
            if keyword in (b"chara", b"ccv3"):
                continue
        kept.append((typ, full))
    return kept


def write_card_png(image_path, card_json_obj, out_path):
    raw = open(image_path, "rb").read()
    chunks = strip_st_chunks(read_png_chunks(raw))
    payload = json.dumps(card_json_obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    b64 = base64.b64encode(payload).decode("ascii")
    new_chunks = [text_chunk_bytes("chara", b64), text_chunk_bytes("ccv3", b64)]
    out = bytearray(raw[:8])
    inserted = False
    for typ, full in chunks:
        out += full
        if typ == b"IHDR" and not inserted:
            for c in new_chunks:
                out += c
            inserted = True
    if not inserted:
        fail("PNG 中找不到 IHDR 块")
    with open(out_path, "wb") as f:
        f.write(bytes(out))


# ---------------------------------------------------------------------------
# 组装
# ---------------------------------------------------------------------------

def collect_scripts(project_dir, meta):
    scripts_dir = os.path.join(project_dir, "scripts")
    entries = []
    if not os.path.isdir(scripts_dir):
        return entries
    disabled = set(meta.get("scripts_disabled", []))
    buttons_map = meta.get("script_buttons", {})
    for fname in sorted(os.listdir(scripts_dir)):
        if not fname.lower().endswith(".js"):
            continue
        name = os.path.splitext(fname)[0]
        content = open(os.path.join(scripts_dir, fname), "r", encoding="utf-8-sig").read()
        buttons = buttons_map.get(name, [])
        entries.append({
            "name": name,
            "id": str(uuid.uuid5(SCRIPT_NS, f"script:{name}")),
            "enabled": name not in disabled,
            "type": "script",
            "content": content,
            "info": "",
            "button": {"enabled": True, "buttons": buttons},
            "data": {},
            "export_with": {"data": True, "button": True},
        })
    return entries


def build(project_dir, image_path, outdir, name_override):
    card_src_path = os.path.join(project_dir, "card.json")
    if not os.path.isfile(card_src_path):
        fail(f"找不到 {card_src_path}")
    card_src = load_json(card_src_path)

    name = name_override or card_src.get("name") or "未命名"
    # 只拦截模板占位文本；真实卡名可以合法地包含【】等括号（如 【TESV】天际模拟器）
    if any(m in str(name) for m in ("【卡名", "填写", "与世界书名称保持一致", "占位")):
        fail(f"card.json 的 name 还是占位文本（{name}），请先填写卡名")

    meta = {}
    meta_path = os.path.join(project_dir, "meta.json")
    if os.path.isfile(meta_path):
        meta = load_json(meta_path)

    data = {
        "name": name,
        "description": card_src.get("description", ""),
        "personality": card_src.get("personality", ""),
        "scenario": card_src.get("scenario", ""),
        "first_mes": card_src.get("first_mes", ""),
        "mes_example": card_src.get("mes_example", ""),
        "creator_notes": card_src.get("creator_notes", card_src.get("creatorcomment", "")),
        "system_prompt": card_src.get("system_prompt", ""),
        "post_history_instructions": card_src.get("post_history_instructions", ""),
        "alternate_greetings": card_src.get("alternate_greetings", []) or [],
        "tags": card_src.get("tags", []) or [],
        "creator": card_src.get("creator", ""),
        "character_version": card_src.get("character_version", "1.0"),
        "group_only_greetings": [],
    }

    # 先透传未知/第三方扩展字段（depth_prompt、cfMvuVarGroups 等），再写入本工具管理的键
    extensions = {}
    extras = card_src.get("extensions_extra")
    if isinstance(extras, dict):
        extensions.update(extras)
    if isinstance(card_src.get("depth_prompt"), dict) and "depth_prompt" not in extensions:
        extensions["depth_prompt"] = card_src["depth_prompt"]
    if isinstance(extras, dict) and extras:
        log("[扩展字段] 透传保留：" + "、".join(extras.keys()))
    extensions.update({
        "talkativeness": card_src.get("talkativeness", "0.5"),
        "fav": bool(card_src.get("fav", False)),
    })

    # 世界书
    wb_path = os.path.join(project_dir, "worldbook.json")
    wb = None
    if os.path.isfile(wb_path):
        wb = load_json(wb_path)
        cb = worldbook_to_character_book(wb)
        data["character_book"] = cb
        extensions["world"] = wb.get("name") or name
        log(f"[世界书] {len(cb['entries'])} 个条目，名称：{extensions['world']}")

    # 正则
    regex_path = os.path.join(project_dir, "regex.json")
    regexes = []
    if os.path.isfile(regex_path):
        regexes = load_json(regex_path)
        if not isinstance(regexes, list):
            fail("regex.json 必须是 JSON 数组（ST 正则导入格式）")
        extensions["regex_scripts"] = regexes
        log(f"[正则] {len(regexes)} 条")

    # 脚本
    scripts = collect_scripts(project_dir, meta)
    extensions["tavern_helper"] = {"scripts": scripts, "variables": {}}
    if scripts:
        log(f"[脚本] {len(scripts)} 个：" + "、".join(s["name"] for s in scripts))

    data["extensions"] = extensions

    # 规格：沿用原卡（extract 保留下来的 spec），新卡默认 v3（当前生态主流，ST 1.13+ 均可导入）
    spec = str(card_src.get("spec") or "chara_card_v3")
    spec_version = str(card_src.get("spec_version") or ("3.0" if spec.endswith("v3") else "2.0"))
    card = {
        "name": name,
        "description": data["description"],
        "personality": data["personality"],
        "scenario": data["scenario"],
        "first_mes": data["first_mes"],
        "mes_example": data["mes_example"],
        "creatorcomment": data["creator_notes"],
        "avatar": "none",
        "chat": "",
        "talkativeness": extensions["talkativeness"],
        "fav": bool(card_src.get("fav", False)),
        "tags": data["tags"],
        "spec": spec,
        "spec_version": spec_version,
        "data": data,
        "create_date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + "000Z",
    }

    os.makedirs(outdir, exist_ok=True)
    json_out = os.path.join(outdir, f"{name}.json")
    save_json(json_out, card)
    log(f"[输出] {json_out}")

    if image_path:
        png_out = os.path.join(outdir, f"{name}.png")
        write_card_png(image_path, card, png_out)
        log(f"[输出] {png_out}")

    if wb is not None:
        save_json(os.path.join(outdir, "世界书.json"), wb)
        log(f"[输出] {os.path.join(outdir, '世界书.json')}")
    if regexes:
        save_json(os.path.join(outdir, "正则.json"), regexes)
        log(f"[输出] {os.path.join(outdir, '正则.json')}")

    log("")
    log("打包完成。建议接着跑：python check_card.py " + json_out)
    return card


def main():
    ap = argparse.ArgumentParser(description="打包 SillyTavern 角色卡工程")
    ap.add_argument("project", help="卡工程目录（内含 card.json 等）")
    ap.add_argument("--image", default=None, help="底图 PNG 路径（输出 PNG 卡）")
    ap.add_argument("--outdir", default=None, help="输出目录（默认 <工程>/输出）")
    ap.add_argument("--name", default=None, help="覆盖卡名")
    args = ap.parse_args()

    if not os.path.isdir(args.project):
        fail(f"工程目录不存在：{args.project}")
    outdir = args.outdir or os.path.join(args.project, "输出")
    build(args.project, args.image, outdir, args.name)


if __name__ == "__main__":
    main()
