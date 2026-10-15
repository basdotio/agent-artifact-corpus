#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_card.py — 校验「角色卡工程目录」或「已打包的角色卡（JSON/PNG）」

用法:
    python check_card.py <卡工程目录 | 卡.json | 卡.png>

检查内容:
  * JSON 结构合法性；卡必填字段
  * 变量条目约定（[initvar] 必须禁用、变量列表宏、输出格式 JSONPatch 等）
  * 正则：字段完整性、findRegex 可编译性（Python 近似校验）、开关组合
  * 脚本：MVU 引入、变量结构注册、相对 import 等常见错误
  * 前端界面：渲染要素（代码块 / <body> / 等待 MVU）
退出码：存在 [错误] 时为 1，否则 0
"""

import base64
import json
import os
import re
import struct
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ERRORS, WARNINGS, INFOS = [], [], []


def error(msg):
    ERRORS.append(msg)
    print(f"  [错误] {msg}")


def warn(msg):
    WARNINGS.append(msg)
    print(f"  [警告] {msg}")


def info(msg):
    INFOS.append(msg)
    print(f"  [信息] {msg}")


def load_json_safe(path, label):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        error(f"{label} 不是合法 JSON：{e}")
        return None


# ---------------------------------------------------------------------------
# 正则可编译性（JS -> Python 近似）
# ---------------------------------------------------------------------------

def compile_js_regex(find_regex):
    """返回 (status, detail)。status: 'ok' | 'js_only' | 'fail'"""
    s = find_regex.strip()
    pattern, flags = s, ""
    m = re.match(r"^/(.*)/?$", s, re.DOTALL)
    if s.startswith("/") and s.rfind("/") > 0:
        last = s.rfind("/")
        pattern, flags = s[1:last], s[last + 1:]
    py_flags = 0
    if "i" in flags:
        py_flags |= re.IGNORECASE
    if "s" in flags:
        py_flags |= re.DOTALL
    if "m" in flags:
        py_flags |= re.MULTILINE
    adapted = pattern.replace("\\/", "/")
    adapted = re.sub(r"\(\?<([A-Za-z_])", r"(?P<\1", adapted)  # JS 命名组 -> Python
    try:
        re.compile(adapted, py_flags)
        return "ok", None
    except re.error as e1:
        msg = str(e1).lower()
        # JS 支持但 Python 不支持的特性：变长后顾、\p{...} 等 —— 归为"无法在 Python 完整校验"，不算错误
        if "look-behind requires fixed-width" in msg or "look-behind" in msg and "fixed" in msg:
            return "js_only", "含变长后顾（JS 支持、Python 不支持）"
        stripped = re.sub(r"\\[pP]\{[^}]*\}", ".", adapted)
        try:
            re.compile(stripped, py_flags)
            return "js_only", f"含 JS 专属语法（\\p{{...}} 等），Python 无法完整校验"
        except re.error as e2:
            return "fail", str(e2)


def check_regex_list(regexes, label):
    if not isinstance(regexes, list):
        error(f"{label} 必须是 JSON 数组")
        return
    if not regexes:
        warn(f"{label} 为空数组")
        return
    seen_ids, names = set(), []
    for i, r in enumerate(regexes):
        if not isinstance(r, dict):
            error(f"{label}[{i}] 不是对象")
            continue
        name = r.get("scriptName", f"<未命名#{i}>")
        names.append(name)
        rid = r.get("id")
        if not rid:
            warn(f"正则「{name}」缺少 id（建议补 UUID，跨卡复制时应更换）")
        elif rid in seen_ids:
            error(f"正则「{name}」的 id 与前面重复：{rid}")
        else:
            seen_ids.add(rid)
        fr = r.get("findRegex")
        if not fr or not isinstance(fr, str):
            error(f"正则「{name}」缺少 findRegex")
        else:
            status, detail = compile_js_regex(fr)
            if status == "fail":
                error(f"正则「{name}」的 findRegex 无法编译：{detail}（原文：{fr[:80]}）")
            elif status == "js_only":
                info(f"正则「{name}」{detail}")
        if "replaceString" not in r:
            warn(f"正则「{name}」没有 replaceString 字段（应显式写 \"\"）")
        markdown_only = r.get("markdownOnly", False)
        prompt_only = r.get("promptOnly", False)
        if markdown_only and prompt_only:
            info(f"正则「{name}」markdownOnly 与 promptOnly 同时为 true：显示与提示词两条路径都会替换、且不做永久改写（常见于开场白/双用替换，确认是有意为之）")
        if not markdown_only and not prompt_only:
            info(f"正则「{name}」两个开关都未勾选：消息在收发时被永久替换（不可逆，确认这是有意为之）")
        # 界面类正则的渲染要素
        rs = r.get("replaceString", "") or ""
        if "<body" in rs or "<head" in rs or "<html" in rs:
            if "```" not in rs and "~~~" not in rs and "$(" not in rs:
                warn(f"正则「{name}」替换内容像 HTML，但没有用 ``` / ~~~ 代码块包裹——酒馆助手不会渲染")
            if "waitGlobalInitialized" not in rs and "Mvu" in rs:
                info(f"正则「{name}」界面里操作 MVU 变量但未见 waitGlobalInitialized('Mvu') 等待")
            if re.search(r"min-height\s*:\s*[^;{}]*\d(vh|dvh)", rs):
                info(f"正则「{name}」界面用到 min-height + vh（酒馆助手会自动转换为视口变量，一般可用；更稳的做法是用内容撑高）")
            if "localhost" in rs or "127.0.0.1" in rs:
                warn(f"正则「{name}」替换内容包含 localhost/127.0.0.1 地址——玩家环境无法访问（开发期残留）")
    if names:
        print(f"     正则：{'、'.join(names)}")

    # 闸门（校验-放行，Impl→READY）与界面正则的一致性
    def is_gate(x):
        n = str(x.get("scriptName", ""))
        return ("校验" in n and "放行" in n) or "闸门" in n
    def is_ui(x):
        n = str(x.get("scriptName", ""))
        return any(k in n for k in ("状态栏", "界面", "前端", "控制台", "面板", "表单"))
    def not_masked(x):
        n = str(x.get("scriptName", ""))
        return not any(k in n for k in ("不发送", "隐藏", "警告", "去除"))
    def fstr(x):
        return str(x.get("findRegex", ""))
    gates = [x for x in regexes if isinstance(x, dict) and is_gate(x)]
    ready_ui = [x for x in regexes if isinstance(x, dict) and "READY" in fstr(x)]
    ui_impl = [x for x in regexes if isinstance(x, dict)
               and "Impl" in fstr(x)
               and not x.get("disabled") and is_ui(x) and not_masked(x)]
    for x in ui_impl:
        ui_name = str(x.get("scriptName"))
        if gates:
            if "READY" in fstr(x):
                warn(f"闸门已启用，但界面正则「{ui_name}」同时匹配 Impl|READY：未更新的楼层也会渲染界面，并与未更新警告抢同一个占位符——闸门场景建议界面只匹配 <StatusPlaceHolderREADY/>")
            else:
                warn(f"检测到闸门（校验-放行→READY），但界面正则「{ui_name}」只匹配 <StatusPlaceHolderImpl/>：放行后占位符已改名 READY，该界面不会渲染（应改为匹配 READY）")
    if ready_ui and not gates:
        warn("有正则匹配 <StatusPlaceHolderREADY/>，但未发现闸门（校验-放行/闸门）正则：READY 从未生成，这些界面不会渲染")


# ---------------------------------------------------------------------------
# 变量条目约定检查（世界书 / character_book 通用）
# ---------------------------------------------------------------------------

def check_variable_entries(entries, get_field, label, scripts_text=""):
    def g(e, k, default=None):
        return get_field(e, k, default)

    comments = [str(g(e, "comment", "")) for e in entries]
    joined = "\n".join(comments)
    is_mvu = any(("[mvu_update]" in c) or ("[initvar]" in c.lower()) or (c.strip() == "变量列表") for c in comments)
    if not is_mvu:
        info(f"{label} 未发现 MVU 变量条目（非变量卡可忽略）")
        return

    for e in entries:
        c = str(g(e, "comment", ""))
        content = str(g(e, "content", ""))
        if "[initvar]" in c.lower():
            disabled = g(e, "disable", None)
            if disabled is None:  # character_book: enabled
                disabled = not bool(g(e, "enabled", True))
            if not disabled:
                error(f"[{label}]「{c}」必须处于禁用状态（MVU 仍会读取它，但启用会把初始值发给 AI）")
        if c.strip() == "变量列表":
            if not bool(g(e, "constant", False)):
                error(f"[{label}]「变量列表」必须是蓝灯（constant=true）且启用，否则 AI 看不到最新变量")
            if "format_message_variable::stat_data" not in content:
                if "get_message_variable" in content:
                    warn(f"[{label}]「变量列表」还在用旧宏 {{get_message_variable::...}}，建议换 {{format_message_variable::...}}")
                else:
                    error(f"[{label}]「变量列表」内容缺少 {{format_message_variable::stat_data}}")
        if "[mvu_update]变量输出格式" in c and "强调" not in c:
            if "<UpdateVariable>" not in content or "JSONPatch" not in content:
                if "_.set" in content:
                    info(f"[{label}]「变量输出格式」是旧式 _.set 写法（可用，但新卡建议 JSONPatch 模板）")
                else:
                    error(f"[{label}]「变量输出格式」缺少 <UpdateVariable>/JSONPatch 模板")
        if "[mvu_update]变量更新规则" in c and not content.strip():
            error(f"[{label}]「变量更新规则」内容为空")

    # 变量列表：名字不是硬接口（MVU 只识别 [initvar]/[mvu_update] 前缀），按内容判定
    def is_var_list(e):
        content = str(g(e, "content", ""))
        if "format_message_variable::stat_data" in content:
            return True
        # EJS 自定义快照：必须读取“整个 stat_data”（不是子路径），并把它输出出去
        whole = re.search(r"getvar\(\s*['\"]stat_data['\"]\s*[,)]", content)
        outputs = "JSON.stringify" in content or "YAML.stringify" in content or "<%= " in content or "status_current_variable" in content
        return bool(whole) and outputs

    macro_entries = [e for e in entries if is_var_list(e)]
    if not macro_entries:
        script_inject = bool(scripts_text) and "stat_data" in scripts_text and bool(
            re.search(r"injectPrompts|setExtensionPrompt|replaceVariables", scripts_text))
        if script_inject:
            info(f"[{label}] 世界书没有变量快照条目；检测到脚本注入方案（stat_data + injectPrompts/setExtensionPrompt，如差分注入设计）——脚本驱动的变量暴露，确认符合预期即可")
        else:
            error(f"[{label}] 没有任何条目输出变量当前值（无 {{format_message_variable::stat_data}}，也无 EJS getvar('stat_data') 快照）——AI 将看不到变量状态")
    else:
        if not any(c.strip() == "变量列表" for c in comments):
            sample = "、".join(str(g(e, "comment", ""))[:24] for e in macro_entries[:3])
            info(f"[{label}] 变量列表使用了自定义条目名（{sample}）——可行；MVU 不依赖该名字")
        for e in macro_entries:
            if not bool(g(e, "constant", False)):
                warn(f"[{label}] 输出变量值的条目「{str(g(e, 'comment', ''))[:24]}」不是蓝灯（constant）——可能不会每轮发送")

    named_format = any("[mvu_update]变量输出格式" in c and "强调" not in c for c in comments)
    named_rules = any("[mvu_update]变量更新规则" in c and "强调" not in c for c in comments)
    content_fmt = any("<UpdateVariable>" in str(g(e, "content", ""))
                      and ("JSONPatch" in str(g(e, "content", "")) or "_.set" in str(g(e, "content", "")))
                      for e in entries)
    content_rules = any("变量更新规则" in str(g(e, "content", "")) for e in entries)
    if not named_format:
        if any("变量输出格式" in c for c in comments) or content_fmt:
            info(f"[{label}]「变量输出格式」使用自定义命名或内容内联（无 [mvu_update] 前缀）：随 AI 输出模式可用，但无法启用 MVU 额外模型解析更新模式")
        else:
            warn(f"[{label}] 缺少变量输出格式条目——AI 可能不会输出更新块")
    if not named_rules:
        if any("变量更新规则" in c for c in comments) or content_rules:
            info(f"[{label}]「变量更新规则」使用自定义命名或内容内联（无 [mvu_update] 前缀），同上")
        elif any("<UpdateVariable>" in str(g(e, "content", "")) for e in entries):
            info(f"[{label}] 未找到'变量更新规则'类条目，但检测到更新协议（<UpdateVariable>）——若卡以自定义方式（如'输出协议/处理手册'条目）规定更新逻辑，可忽略本提示")
        else:
            warn(f"[{label}] 缺少变量更新规则条目——AI 将自由发挥更新逻辑")


def check_scripts_list(script_texts, label):
    ok_mvu, ok_schema = False, False
    for name, text in script_texts:
        if not text.strip():
            warn(f"[{label}] 脚本「{name}」内容为空")
        stripped = text.lstrip("﻿ \t\r\n")
        if stripped.startswith("{") and '"type"' in stripped[:200] and '"content"' in stripped[:2000]:
            error(f"[{label}] 脚本「{name}」内容疑似为 JSON 导出格式被整体粘贴（以 {{ 开头且含 \"type\"/\"content\" 字段）——内嵌执行会因语法错误失败，应只保留 content 字段里的代码")
        if "MagVarUpdate" in text:
            ok_mvu = True
        # 变量结构脚本：内联注册（registerMvuSchema / mvu_zod）或按名引用（如 CDN 方式）
        if "registerMvuSchema" in text or "mvu_zod" in text or "变量结构" in name:
            ok_schema = True
        if re.search(r"from\s+['\"]\.\.?/", text) or re.search(r"import\s+['\"]\.\.?/", text):
            error(f"[{label}] 脚本「{name}」使用了相对路径 import——内嵌脚本无法解析相对路径，改用 CDN 绝对地址或内联代码")
        if re.search(r"https?://(localhost|127\.0\.0\.1)[:/]", text):
            warn(f"[{label}] 脚本「{name}」包含 localhost/127.0.0.1 地址——玩家环境无法访问（开发期残留），应改为线上地址或内联")
        if "import " in text and ".ts'" in text:
            warn(f"[{label}] 脚本「{name}」import 了 .ts 文件——酒馆助手只支持 .js/远程模块")
    if not ok_mvu:
        warn(f"[{label}] 没有找到 MVU 引入脚本（import '…/MagVarUpdate/artifact/bundle.js'）")
    if not ok_schema:
        warn(f"[{label}] 没有找到变量结构脚本（registerMvuSchema）")


# ---------------------------------------------------------------------------
# 工程目录 / 成品卡 两条路径
# ---------------------------------------------------------------------------

def decode_png_card(path):
    data = open(path, "rb").read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        error("不是合法 PNG")
        return None
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
                    error(f"解析 PNG 的 {keyword.decode()} 块失败：{e}")
        pos += 12 + ln
        if typ == b"IEND":
            break
    if "chara" in found:
        return found["chara"]
    if "ccv3" in found:
        info("PNG 只有 ccv3 块（没有 chara）——兼容性略降，建议打包时同时写入")
        return found["ccv3"]
    error("PNG 中没有 chara/ccv3 卡数据")
    return None


def check_packaged_card(card, label):
    if not isinstance(card, dict):
        error("卡数据不是 JSON 对象")
        return
    data = card.get("data", card)
    if not data.get("name"):
        error("缺少 name")
    if not data.get("first_mes"):
        error("缺少 first_mes（开场白）")
    ext = data.get("extensions", {}) or {}
    regexes = ext.get("regex_scripts")
    if regexes is not None:
        print("  · 检查卡内正则")
        check_regex_list(regexes, f"{label}·regex_scripts")
    th = ext.get("tavern_helper", {}) or {}
    scripts = th.get("scripts", []) if isinstance(th, dict) else []

    def flatten(trees, prefix=""):
        out = []
        for it in trees:
            if not isinstance(it, dict):
                continue
            if it.get("type") == "folder":
                out += flatten(it.get("scripts", []), prefix + str(it.get("name", "")) + "/")
            else:
                out.append((prefix + str(it.get("name", "")), str(it.get("content", ""))))
        return out

    script_texts = flatten(scripts)
    if script_texts:
        print("  · 检查卡内脚本")
        check_scripts_list(script_texts, label)
    else:
        warn(f"[{label}] 卡内没有酒馆助手脚本——如果这是变量卡，玩家将无法运行 MVU/变量结构")

    cb = data.get("character_book")
    if cb and cb.get("entries"):
        print("  · 检查卡内世界书")
        check_variable_entries(cb["entries"], lambda e, k, d=None: e.get(k, d), f"{label}·character_book",
                               "\n".join(c for _n, c in script_texts))
    elif ext.get("world"):
        info(f"卡关联外部世界书「{ext.get('world')}」，未内嵌——变量条目请在独立世界书中检查")


def check_project(project_dir):
    print("== 检查工程目录 ==")
    card_path = os.path.join(project_dir, "card.json")
    if not os.path.isfile(card_path):
        error("缺少 card.json")
    else:
        card = load_json_safe(card_path, "card.json")
        if card is not None:
            print("  · card.json")
            name = str(card.get("name", ""))
            if not name:
                error("card.json 缺少 name")
            elif any(m in name for m in ("【卡名", "填写", "与世界书名称保持一致", "占位")):
                error(f"card.json 的 name 还是占位文本：{name}")
            if not card.get("first_mes"):
                error("card.json 缺少 first_mes（开场白）")
            if not card.get("description"):
                info("card.json 的 description 为空（不少变量卡把人设放在世界书条目里，属可接受设计）")

    wb_path = os.path.join(project_dir, "worldbook.json")
    if os.path.isfile(wb_path):
        wb = load_json_safe(wb_path, "worldbook.json")
        if isinstance(wb, dict) and isinstance(wb.get("entries"), dict):
            print(f"  · worldbook.json（{len(wb['entries'])} 条目）")
            uids = []
            for k, e in wb["entries"].items():
                if not isinstance(e, dict):
                    error(f"worldbook entries[{k}] 不是对象")
                    continue
                uids.append(k)
                if not str(e.get("comment", "")).strip():
                    warn(f"worldbook entries[{k}] 没有 comment（标题），面板里难以辨认")
                for field, expected in (("uid", k),):
                    if str(e.get(field)) != expected:
                        warn(f"worldbook entries[{k}] 的 uid={e.get(field)} 与键不一致（推荐一致）")
            if len(uids) != len(set(uids)):
                error("worldbook 的 uid 有重复")
            scripts_pre = os.path.join(project_dir, "scripts")
            stext = ""
            if os.path.isdir(scripts_pre):
                for f in os.listdir(scripts_pre):
                    if f.lower().endswith(".js"):
                        try:
                            stext += open(os.path.join(scripts_pre, f), encoding="utf-8-sig").read()
                        except OSError:
                            pass
            check_variable_entries(list(wb["entries"].values()), lambda e, k, d=None: e.get(k, d), "worldbook", stext)
        else:
            error("worldbook.json 结构不对（应为 {\"name\":…, \"entries\":{…}}）")
    else:
        info("没有 worldbook.json（纯内容卡可忽略；变量卡应该有）")

    regex_path = os.path.join(project_dir, "regex.json")
    if os.path.isfile(regex_path):
        regexes = load_json_safe(regex_path, "regex.json")
        print("  · regex.json")
        check_regex_list(regexes, "regex")
    else:
        info("没有 regex.json（不打正则包可忽略）")

    scripts_dir = os.path.join(project_dir, "scripts")
    if os.path.isdir(scripts_dir):
        files = [f for f in sorted(os.listdir(scripts_dir)) if f.lower().endswith(".js")]
        if not files:
            warn("scripts/ 目录为空")
        else:
            print(f"  · scripts/（{len(files)} 个）")
            texts = []
            for f in files:
                p = os.path.join(scripts_dir, f)
                texts.append((f, open(p, "r", encoding="utf-8-sig").read()))
            check_scripts_list(texts, "scripts")
    else:
        info("没有 scripts/ 目录")

    meta_path = os.path.join(project_dir, "meta.json")
    if os.path.isfile(meta_path):
        meta = load_json_safe(meta_path, "meta.json")
        if meta is not None and not isinstance(meta, dict):
            error("meta.json 必须是对象")


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    target = sys.argv[1]
    if os.path.isdir(target):
        check_project(target)
    elif os.path.isfile(target):
        lower = target.lower()
        if lower.endswith(".png"):
            print("== 检查成品卡 PNG ==")
            card = decode_png_card(target)
        else:
            print("== 检查成品卡 JSON ==")
            card = load_json_safe(target, "卡 JSON")
        if card is not None:
            check_packaged_card(card, "卡")
    else:
        print(f"[错误] 路径不存在：{target}")
        sys.exit(1)

    print()
    print(f"结果：[错误] {len(ERRORS)} 项，[警告] {len(WARNINGS)} 项，[信息] {len(INFOS)} 项")
    if ERRORS:
        print("存在错误：修好上面 [错误] 项后再打包/发布。")
        sys.exit(1)
    else:
        print("没有发现致命错误。")
        sys.exit(0)


if __name__ == "__main__":
    main()
