#!/usr/bin/env python3
"""Render the report (Markdown or HTML) from fetch_tasks.py's JSON and the agent's summaries.

  python build_report.py tasks.json --summaries summaries.json --format html
  python build_report.py tasks.json --summaries summaries.json --format md --out report.md

summaries.json is written by the agent after it reads every ticket, in the report language:
  {
    "executive_summary": ["...", "..."],          # 3-5 bullets
    "talking_points":    ["...", "..."],          # 3-5 bullets
    "tickets":           {"<task id>": "2-4 sentences", ...},   # one per ticket, required
    "extra_risks":       [{"id": "<task id>", "reason": "...", "date": "YYYY-MM-DD"}]   # optional
  }
The build fails (exit 5) and lists the ids when a ticket has no summary, so nothing
unfinished reaches the meeting. --allow-missing renders a draft anyway.

Layout: header, KPI tiles, executive summary, talking points, risks, a count table
(group x status column), metrics, then every ticket by group (sprint/list by default)
and by ClickUp status column, in the workspace's own column order.
Language: meta.language "Arabic"/"ar" gives Arabic labels and right-to-left layout;
anything else gives English. Task names always stay as they are in ClickUp.
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clickup_client import emit, utf8_stdout  # noqa: E402

RISK_FLAGS = ("overdue", "blocked", "blocked_in_comment", "stale", "over_estimate")
REVIEW_RE = re.compile(r"review|qa|test|verify|approval", re.I)
BLOCK_RE = re.compile(r"block|hold|stuck|wait", re.I)

T = {
    "en": {
        "dir": "ltr", "lang": "en",
        "title_sprint": "Sprint report", "title_work": "Work report",
        "sprint": "Sprint", "period": "Period", "where": "Where", "workspace": "Workspace",
        "generated": "Generated", "columns": "Columns", "all_columns": "all columns",
        "scope_list": "List", "scope_folder": "Folder", "scope_space": "Space", "scope_tag": "Tag",
        "closed_in": "done tasks closed in",
        "exec": "Executive summary", "glance": "At a glance", "talking": "Talking points",
        "done": "Done", "in_progress": "In progress", "todo": "To do", "at_risk": "At risk", "total": "Total",
        "metric": "Metric", "value": "Value",
        "m_tracked": "Time tracked in period (all tasks)", "m_estimate": "Estimate of open tasks",
        "m_points": "Sprint points done / open", "m_undated": "Open tasks with no due date",
        "risks": "Blocked / at risk", "no_risk": "Nothing at risk.",
        "task": "Task", "why": "Why", "status": "Status", "place": "Where",
        "tasks_by": "Tasks by", "priority": "Priority", "due": "Due", "closed": "Closed",
        "tracked": "Tracked / estimate", "points": "Points", "folder": "Folder", "summary": "Summary",
        "notes": "Data notes", "missing": "(summary not written yet)", "progress": "Progress",
        "not_included": "Not included: the latest sprint of space {space} is {name} ({start} → {due}).",
        "h": "h", "m": "m",
        "group": {"list": "sprint / list", "folder": "folder", "space": "space", "tag": "tag", "status": "status"},
        "flag": {"overdue": "overdue", "blocked": "status says blocked / on hold",
                 "blocked_in_comment": "a recent comment mentions a blocker",
                 "stale": "no update for 14+ days", "over_estimate": "tracked time is over the estimate"},
        "prio": {"urgent": "Urgent", "high": "High", "normal": "Normal", "low": "Low"},
    },
    "ar": {
        "dir": "rtl", "lang": "ar",
        "title_sprint": "تقرير السبرنت", "title_work": "تقرير العمل",
        "sprint": "السبرنت", "period": "الفترة", "where": "المكان", "workspace": "مساحة العمل",
        "generated": "تاريخ الإنشاء", "columns": "الأعمدة", "all_columns": "كل الأعمدة",
        "scope_list": "القائمة", "scope_folder": "المجلد", "scope_space": "المساحة", "scope_tag": "الوسم",
        "closed_in": "المهام المنجزة المغلقة خلال",
        "exec": "الملخص التنفيذي", "glance": "نظرة سريعة", "talking": "نقاط للحديث في الاجتماع",
        "done": "منجزة", "in_progress": "قيد التنفيذ", "todo": "للتنفيذ", "at_risk": "معرّضة للخطر", "total": "المجموع",
        "metric": "المقياس", "value": "القيمة",
        "m_tracked": "الوقت المسجّل في الفترة (كل المهام)", "m_estimate": "تقدير المهام المفتوحة",
        "m_points": "نقاط السبرنت: منجزة / مفتوحة", "m_undated": "مهام مفتوحة بلا موعد تسليم",
        "risks": "العوائق والمخاطر", "no_risk": "لا توجد مخاطر.",
        "task": "المهمة", "why": "السبب", "status": "الحالة", "place": "المكان",
        "tasks_by": "المهام حسب", "priority": "الأولوية", "due": "موعد التسليم", "closed": "أُغلقت",
        "tracked": "الوقت المسجّل / التقدير", "points": "النقاط", "folder": "المجلد", "summary": "الملخص",
        "notes": "ملاحظات عن البيانات", "missing": "(لم يُكتب الملخص بعد)", "progress": "نسبة الإنجاز",
        "not_included": "غير مشمول: آخر سبرنت في المساحة {space} هو {name} ({start} → {due}).",
        "h": "س", "m": "د",
        "group": {"list": "السبرنت / القائمة", "folder": "المجلد", "space": "المساحة", "tag": "الوسم",
                  "status": "الحالة"},
        "flag": {"overdue": "تجاوزت موعد التسليم", "blocked": "الحالة تقول متوقفة / معلّقة",
                 "blocked_in_comment": "تعليق حديث يذكر عائقاً",
                 "stale": "لا تحديث منذ 14 يوماً أو أكثر", "over_estimate": "الوقت المسجّل تجاوز التقدير"},
        "prio": {"urgent": "عاجلة", "high": "عالية", "normal": "عادية", "low": "منخفضة"},
    },
}
PRIO_EMOJI = {"urgent": "🔴", "high": "🟠", "normal": "🔵", "low": "⚪"}
PRIO_COLOR = {"urgent": "#dc2626", "high": "#ea580c", "normal": "#2563eb", "low": "#64748b"}
KIND_COLOR = {"done": "#16a34a", "review": "#7c3aed", "blocked": "#dc2626", "in_progress": "#2563eb", "todo": "#64748b"}
KIND_EMOJI = {"done": "✅", "review": "🟣", "blocked": "🔴", "in_progress": "🔵", "todo": "⚪"}


# ---------- shared helpers ----------

def lang_of(meta):
    return "ar" if str(meta.get("language", "")).strip().lower() in ("arabic", "ar", "العربية", "عربي") else "en"


def duration(ms, t):
    if not ms:
        return "—"
    hours, minutes = divmod(round(ms / 60000), 60)
    return f"{hours}{t['h']} {minutes:02d}{t['m']}" if hours else f"{minutes}{t['m']}"


def natural(text):
    """Sort key where "Sprint 10" comes after "Sprint 9"."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", text or "")]


def group_key(task, group_by):
    if group_by == "tag":
        return task["tags"][0] if task.get("tags") else "(untagged)"
    field = {"list": "list", "folder": "folder", "space": "space", "status": "status"}[group_by]
    return task.get(field) or f"(no {field})"


def status_kind(task):
    """done / review / blocked / in_progress / todo — decides the color and the emoji."""
    if task["bucket"] == "done":
        return "done"
    if BLOCK_RE.search(task["status"]):
        return "blocked"
    if REVIEW_RE.search(task["status"]):
        return "review"
    return task["bucket"]


def status_order(tasks):
    """Status names in ClickUp's own order (the lowest orderindex seen for each name)."""
    rank = {}
    for t in tasks:
        name = t.get("status") or "(no status)"
        rank[name] = min(rank.get(name, 1e9), t.get("status_order", 1e9))
    return sorted(rank, key=lambda n: (rank[n], n.lower()))


def cap(text):
    return text[:1].upper() + text[1:] if text else text


def model(data, summaries, group_by):
    """Everything both renderers need, computed once."""
    meta, tasks = data["meta"], data["tasks"]
    t = T[lang_of(meta)]
    by_id = {x["id"]: x for x in tasks}
    reasons = {}
    for x in tasks:
        if x["bucket"] != "done":
            found = [t["flag"][f] for f in x["flags"] if f in RISK_FLAGS]
            if found:
                reasons[x["id"]] = found
    for extra in summaries.get("extra_risks") or []:
        if extra.get("id") in by_id:
            text = extra.get("reason", "") + (f" ({extra['date']})" if extra.get("date") else "")
            reasons.setdefault(extra["id"], []).append(text)
    groups = {}
    for x in tasks:
        groups.setdefault(group_key(x, group_by), []).append(x)
    names = sorted(groups, key=natural, reverse=group_by in ("list", "folder"))
    buckets = {b: [x for x in tasks if x["bucket"] == b] for b in ("done", "in_progress", "todo")}

    def points(ts):
        return sum(float(x["points"]) for x in ts if x.get("points") not in (None, ""))

    open_ = buckets["in_progress"] + buckets["todo"]
    scope = meta.get("scope") or {"type": "period"}
    notes = list(meta.get("warnings") or [])
    for other in scope.get("other_latest_sprints") or []:
        notes.append(t["not_included"].format(**other))
    return {
        "t": t, "meta": meta, "tasks": tasks, "scope": scope, "group_by": group_by,
        "groups": groups, "names": names, "statuses": status_order(tasks), "buckets": buckets,
        "risky": [(by_id[i], r) for i, r in reasons.items()],
        "metrics": [
            (t["m_tracked"], duration(sum(x["tracked_ms"] for x in tasks), t)),
            (t["m_estimate"], duration(sum(x["estimate_ms"] for x in open_), t)),
            (t["m_points"], f"{points(buckets['done']):g} / {points(open_):g}"),
            (t["m_undated"], str(sum(1 for x in tasks if "no_due_date" in x["flags"]))),
        ],
        "notes": notes,
        "summaries": summaries,
    }


def header_lines(m):
    """(title, [(label, value)]) for the report header."""
    t, meta, scope = m["t"], m["meta"], m["scope"]
    user = meta["user"].get("name") or meta["user"]["id"]
    workspace = meta["workspace"].get("name") or meta["workspace"]["id"]
    period = meta["period"]
    facts = []
    if scope["type"] == "sprint":
        sprint = scope["sprint"]
        title = f"{t['title_sprint']} — {user}"
        facts.append((t["sprint"], f"{sprint['name']} ({sprint['start']} → {sprint['due']})"))
        where = " / ".join(x for x in (sprint.get("space"), sprint.get("folder")) if x)
        if where:
            facts.append((t["where"], where))
    else:
        title = f"{t['title_work']} — {user}"
        if scope["type"] == "period":
            facts.append((t["period"], f"{period['since']} → {period['until']}"))
        else:
            target = scope["target"]
            facts.append((t["scope_" + scope["type"]], target["name"]))
            where = " / ".join(x for x in (target.get("space"), target.get("folder")) if x)
            if where:
                facts.append((t["where"], where))
            if scope.get("period_filter"):
                facts.append((t["closed_in"], f"{period['since']} → {period['until']}"))
    facts.append((t["columns"], "، ".join(scope["status_filter"]) if scope.get("status_filter") and t["lang"] == "ar"
                  else ", ".join(scope["status_filter"]) if scope.get("status_filter") else t["all_columns"]))
    facts.append((t["workspace"], workspace))
    facts.append((t["generated"], meta["generated_at"].replace("T", " ")[:16]))
    return title, facts


def ticket_facts(x, t):
    facts = []
    if x.get("priority"):
        facts.append(("prio", f"{t['priority']}: {t['prio'].get(x['priority'], x['priority'])}"))
    facts.append(("due", f"{t['due']}: {x['due'] or '—'}"))
    if x["bucket"] == "done" and x.get("closed"):
        facts.append(("closed", f"{t['closed']}: {x['closed']}"))
    if x["estimate_ms"] or x["tracked_ms"]:
        facts.append(("time", f"{t['tracked']}: {duration(x['tracked_ms'], t)} / {duration(x['estimate_ms'], t)}"))
    if x.get("points") not in (None, ""):
        facts.append(("points", f"{t['points']}: {x['points']}"))
    return facts


def label(x):
    return f"{x['custom_id']} {x['name']}" if x.get("custom_id") else x["name"]


# ---------- Markdown ----------

def md_cell(text):
    return (str(text) if text not in (None, "") else "—").replace("|", "\\|").replace("\n", " ")


def md_link(x):
    return f"[{md_cell(label(x))}]({x['url']})" if x.get("url") else md_cell(label(x))


def md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + ":---:|" * len(headers)]
    return "\n".join(lines + ["| " + " | ".join(r) + " |" for r in rows])


def md_bar(done, total, cells=20):
    filled = round(cells * done / total) if total else 0
    return "🟩" * filled + "⬜" * (cells - filled)


def render_md(m):
    t, s, b = m["t"], m["summaries"], m["buckets"]
    title, facts = header_lines(m)
    total = len(m["tasks"])
    out = [f'<div dir="{t["dir"]}">\n', f"# 📊 {title}\n",
           "\n".join(f"> **{k}:** {md_cell(v)}  " for k, v in facts) + "\n"]

    out += [f"## 📈 {t['glance']}\n",
            md_table([f"✅ {t['done']}", f"🔵 {t['in_progress']}", f"⚪ {t['todo']}", f"⚠️ {t['at_risk']}",
                      f"🧮 {t['total']}"],
                     [[f"**{len(b['done'])}**", f"**{len(b['in_progress'])}**", f"**{len(b['todo'])}**",
                       f"**{len(m['risky'])}**", f"**{total}**"]]) + "\n",
            f"**{t['progress']}:** {md_bar(len(b['done']), total)} "
            f"**{round(100 * len(b['done']) / total) if total else 0}%**\n"]

    out += [f"## 🧭 {t['exec']}\n", "> [!TIP]"]
    out += [f"> - {line}" for line in s.get("executive_summary") or [t["missing"]]]
    out += ["", f"## 🎤 {t['talking']}\n", "> [!IMPORTANT]"]
    out += [f"> - {line}" for line in s.get("talking_points") or [t["missing"]]]
    out.append("")

    out.append(f"## 🚧 {t['risks']} ({len(m['risky'])})\n")
    if m["risky"]:
        out += ["> [!WARNING]", f"> {len(m['risky'])} × ⚠️\n",
                md_table([t["task"], t["why"], t["status"], t["place"]],
                         [[md_link(x), md_cell("؛ ".join(r) if t["lang"] == "ar" else "; ".join(r)),
                           f"{KIND_EMOJI[status_kind(x)]} {md_cell(x['status'])}", md_cell(group_key(x, m['group_by']))]
                          for x, r in m["risky"]]) + "\n"]
    else:
        out.append(f"> [!NOTE]\n> ✅ {t['no_risk']}\n")

    if m["group_by"] != "status":
        emoji_of = {x["status"]: KIND_EMOJI[status_kind(x)] for x in m["tasks"]}
        rows = [[md_cell(n)] + [str(sum(1 for x in m["groups"][n] if x["status"] == st) or "·") for st in m["statuses"]]
                + [f"**{len(m['groups'][n])}**"] for n in m["names"]]
        out.append(md_table([cap(t["group"][m["group_by"]])] + [f"{emoji_of[st]} {md_cell(st)}" for st in m["statuses"]]
                            + [t["total"]], rows) + "\n")
    out.append(md_table([t["metric"], t["value"]], [[k, v] for k, v in m["metrics"]]) + "\n")

    out.append(f"## 🗂️ {t['tasks_by']} {t['group'][m['group_by']]}\n")
    for name in m["names"]:
        members = m["groups"][name]
        out.append(f"### 📁 {md_cell(name)} ({len(members)})\n")
        sections = [(None, members)] if m["group_by"] == "status" else [
            (st, [x for x in members if x["status"] == st]) for st in m["statuses"]]
        for st, items in sections:
            if not items:
                continue
            if st is not None:
                out.append(f"#### {KIND_EMOJI[status_kind(items[0])]} {md_cell(cap(st))} ({len(items)})\n")
            for x in items:
                risk = " ⚠️" if any(x is r[0] for r in m["risky"]) else ""
                out.append(f"##### {md_link(x)}{risk}\n")
                chips = [f"`{KIND_EMOJI[status_kind(x)]} {md_cell(x['status'])}`"]
                for kind, text in ticket_facts(x, t):
                    icon = {"prio": PRIO_EMOJI.get(x.get("priority"), "🔹"), "due": "📅", "closed": "🏁",
                            "time": "⏱️", "points": "🎯"}[kind]
                    chips.append(f"{icon} {md_cell(text)}")
                out.append(" · ".join(chips) + "\n")
                out.append(f"📝 {s.get('tickets', {}).get(x['id']) or t['missing']}\n")
            out.append("---\n")

    if m["notes"]:
        out.append(f"## ℹ️ {t['notes']}\n")
        out.append("\n".join(f"- {md_cell(n)}" for n in m["notes"]) + "\n")
    out.append("</div>\n")
    return "\n".join(out)


# ---------- HTML ----------

CSS = """
:root{--bg:#f4f6fb;--card:#fff;--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--soft:#f8fafc;
--done:#16a34a;--prog:#2563eb;--todo:#64748b;--risk:#dc2626;--rev:#7c3aed;
--hero1:#4f46e5;--hero2:#0ea5e9;--shadow:0 1px 2px rgba(15,23,42,.06),0 4px 16px rgba(15,23,42,.06)}
@media (prefers-color-scheme:dark){:root{--bg:#0b1120;--card:#131c2e;--ink:#e2e8f0;--muted:#94a3b8;--line:#243047;
--soft:#0f172a;--hero1:#3730a3;--hero2:#0369a1;--shadow:none}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.7 "IBM Plex Sans Arabic","Segoe UI",Tahoma,system-ui,sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:24px 16px 48px}
a{color:inherit}
.hero{background:linear-gradient(120deg,var(--hero1),var(--hero2));color:#fff;border-radius:18px;padding:28px;box-shadow:var(--shadow)}
.hero h1{margin:0 0 14px;font-size:clamp(22px,4vw,30px)}
.facts{display:flex;flex-wrap:wrap;gap:8px}
.fact{background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.25);border-radius:999px;padding:3px 12px;font-size:13px}
.fact b{opacity:.8;font-weight:600}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}
.kpi{background:var(--card);border-radius:14px;padding:16px;box-shadow:var(--shadow);border-top:4px solid var(--c)}
.kpi .n{font-size:32px;font-weight:700;color:var(--c);line-height:1.2}
.kpi .l{color:var(--muted);font-size:13px}
.bar{display:flex;height:12px;border-radius:999px;overflow:hidden;background:var(--line);margin:6px 0 2px}
.bar span{display:block;height:100%}
.card{background:var(--card);border-radius:14px;padding:18px 20px;box-shadow:var(--shadow);margin:14px 0}
.card h2{margin:0 0 10px;font-size:19px;display:flex;align-items:center;gap:8px}
.card.tip{border-inline-start:5px solid var(--done)}.card.talk{border-inline-start:5px solid var(--rev)}
.card.warn{border-inline-start:5px solid var(--risk)}
.card ul{margin:0;padding-inline-start:20px}.card li{margin:4px 0}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}
.grid2 .card{margin:0}
.tablewrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:start;vertical-align:top}
th{background:var(--soft);color:var(--muted);font-weight:600;white-space:nowrap}
td.num,th.num{text-align:center}
.pill{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:1px 10px;font-size:12.5px;font-weight:600;
background:color-mix(in srgb,var(--c) 14%,transparent);color:var(--c);border:1px solid color-mix(in srgb,var(--c) 35%,transparent);white-space:nowrap}
.dot{width:9px;height:9px;border-radius:50%;background:var(--c);display:inline-block;flex:none}
.group{margin-top:26px}
.group>h2{font-size:21px;margin:0 0 4px;padding-bottom:6px;border-bottom:2px solid var(--line)}
.col{margin:16px 0 6px;display:flex;align-items:center;gap:8px;font-size:16px}
.col .count{color:var(--muted);font-weight:500}
.tickets{display:grid;gap:10px}
.ticket{background:var(--card);border-radius:12px;padding:14px 16px;box-shadow:var(--shadow);border-inline-start:5px solid var(--c);break-inside:avoid}
.ticket h3{margin:0 0 6px;font-size:15.5px;line-height:1.5}
.ticket h3 a{text-decoration:none}.ticket h3 a:hover{text-decoration:underline}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px}
.chip{font-size:12.5px;color:var(--muted);background:var(--soft);border:1px solid var(--line);border-radius:8px;padding:0 8px}
.summary{margin:0;padding:10px 12px;background:var(--soft);border-radius:8px}
.risk{color:var(--risk);font-weight:700}
.muted{color:var(--muted)}
.notes li{color:var(--muted)}
bdi{unicode-bidi:isolate}
@media print{body{background:#fff}.card,.ticket,.kpi{box-shadow:none;border:1px solid #ddd}.hero{print-color-adjust:exact;-webkit-print-color-adjust:exact}
.kpi,.ticket,.card{break-inside:avoid}}
@media (max-width:600px){.hero{padding:20px}.grid2{grid-template-columns:1fr}}
"""


def esc(text):
    return html.escape(str(text if text not in (None, "") else "—"))


def color_of(x):
    return KIND_COLOR["done"] if x["bucket"] == "done" else (x.get("status_color") or KIND_COLOR[status_kind(x)])


def h_link(x):
    name = f"<bdi>{esc(label(x))}</bdi>"
    return f'<a href="{esc(x["url"])}" target="_blank" rel="noopener">{name}</a>' if x.get("url") else name


def h_status(x):
    return f'<span class="pill" style="--c:{esc(color_of(x))}"><span class="dot"></span><bdi>{esc(x["status"])}</bdi></span>'


CHIP_ICON = {"prio": "🚩", "due": "📅", "closed": "🏁", "time": "⏱️", "points": "🎯"}


def h_chip(x, kind, text):
    color = PRIO_COLOR.get(x.get("priority")) if kind == "prio" else None
    style = f' style="color:{color};border-color:{color}"' if color else ""
    return f'<span class="chip"{style}>{CHIP_ICON[kind]} {esc(text)}</span>'


def render_html(m):
    t, s, b = m["t"], m["summaries"], m["buckets"]
    title, facts = header_lines(m)
    total = len(m["tasks"])
    pct = (lambda n: 100 * n / total if total else 0)
    p = []
    p.append(f'<!doctype html><html lang="{t["lang"]}" dir="{t["dir"]}"><head><meta charset="utf-8">'
             '<meta name="viewport" content="width=device-width,initial-scale=1">'
             f"<title>{esc(title)}</title>"
             '<link rel="preconnect" href="https://fonts.googleapis.com">'
             '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&display=swap" rel="stylesheet">'
             f"<style>{CSS}</style></head><body><div class=\"wrap\">")
    p.append(f'<header class="hero"><h1>📊 {esc(title)}</h1><div class="facts">'
             + "".join(f'<span class="fact"><b>{esc(k)}:</b> <bdi>{esc(v)}</bdi></span>' for k, v in facts)
             + "</div></header>")

    kpis = [(t["done"], len(b["done"]), "var(--done)", "✅"), (t["in_progress"], len(b["in_progress"]), "var(--prog)", "🔵"),
            (t["todo"], len(b["todo"]), "var(--todo)", "⚪"), (t["at_risk"], len(m["risky"]), "var(--risk)", "⚠️"),
            (t["total"], total, "var(--hero1)", "🧮")]
    p.append('<section class="kpis">' + "".join(
        f'<div class="kpi" style="--c:{c}"><div class="n">{n}</div><div class="l">{i} {esc(l)}</div></div>'
        for l, n, c, i in kpis) + "</section>")
    p.append(f'<div class="card"><h2>📈 {esc(t["progress"])} — {round(pct(len(b["done"])))}%</h2><div class="bar">'
             f'<span style="width:{pct(len(b["done"])):.2f}%;background:var(--done)"></span>'
             f'<span style="width:{pct(len(b["in_progress"])):.2f}%;background:var(--prog)"></span>'
             f'<span style="width:{pct(len(b["todo"])):.2f}%;background:var(--todo)"></span></div>'
             f'<div class="muted" style="font-size:13px">✅ {len(b["done"])} · 🔵 {len(b["in_progress"])} · ⚪ {len(b["todo"])}</div></div>')

    def bullets(items):
        return "<ul>" + "".join(f"<li>{esc(i)}</li>" for i in items or [t["missing"]]) + "</ul>"

    p.append(f'<div class="grid2"><div class="card tip"><h2>🧭 {esc(t["exec"])}</h2>{bullets(s.get("executive_summary"))}</div>'
             f'<div class="card talk"><h2>🎤 {esc(t["talking"])}</h2>{bullets(s.get("talking_points"))}</div></div>')

    sep = "؛ " if t["lang"] == "ar" else "; "
    if m["risky"]:
        rows = "".join(f"<tr><td>{h_link(x)}</td><td class=\"risk\">{esc(sep.join(r))}</td><td>{h_status(x)}</td>"
                       f"<td><bdi>{esc(group_key(x, m['group_by']))}</bdi></td></tr>" for x, r in m["risky"])
        body = (f'<div class="tablewrap"><table><thead><tr><th>{esc(t["task"])}</th><th>{esc(t["why"])}</th>'
                f'<th>{esc(t["status"])}</th><th>{esc(t["place"])}</th></tr></thead><tbody>{rows}</tbody></table></div>')
    else:
        body = f'<p class="muted">✅ {esc(t["no_risk"])}</p>'
    p.append(f'<div class="card warn"><h2>🚧 {esc(t["risks"])} ({len(m["risky"])})</h2>{body}</div>')

    tables = []
    if m["group_by"] != "status":
        sample = {x["status"]: x for x in m["tasks"]}
        head = "".join(f'<th class="num">{h_status(sample[st])}</th>' for st in m["statuses"])
        rows = "".join(
            f"<tr><td><bdi>{esc(n)}</bdi></td>"
            + "".join(f'<td class="num">{sum(1 for x in m["groups"][n] if x["status"] == st) or "·"}</td>' for st in m["statuses"])
            + f'<td class="num"><b>{len(m["groups"][n])}</b></td></tr>' for n in m["names"])
        tables.append(f'<div class="card"><h2>🧮 {esc(t["glance"])}</h2><div class="tablewrap"><table><thead><tr>'
                      f'<th>{esc(cap(t["group"][m["group_by"]]))}</th>{head}<th class="num">{esc(t["total"])}</th></tr></thead>'
                      f"<tbody>{rows}</tbody></table></div></div>")
    tables.append(f'<div class="card"><h2>📐 {esc(t["metric"])}</h2><div class="tablewrap"><table><tbody>'
                  + "".join(f"<tr><td>{esc(k)}</td><td class=\"num\"><b>{esc(v)}</b></td></tr>" for k, v in m["metrics"])
                  + "</tbody></table></div></div>")
    p.append('<div class="grid2">' + "".join(tables) + "</div>")

    risky_ids = {x["id"] for x, _ in m["risky"]}
    p.append(f'<h2 style="margin-top:30px">🗂️ {esc(t["tasks_by"])} {esc(t["group"][m["group_by"]])}</h2>')
    for name in m["names"]:
        members = m["groups"][name]
        p.append(f'<section class="group"><h2>📁 <bdi>{esc(name)}</bdi> <span class="muted">({len(members)})</span></h2>')
        sections = [(None, members)] if m["group_by"] == "status" else [
            (st, [x for x in members if x["status"] == st]) for st in m["statuses"]]
        for st, items in sections:
            if not items:
                continue
            if st is not None:
                p.append(f'<div class="col">{h_status(items[0])}<span class="count">({len(items)})</span></div>')
            p.append('<div class="tickets">')
            for x in items:
                chips = "".join(h_chip(x, k, v) for k, v in ticket_facts(x, t))
                warn = ' <span class="risk" title="risk">⚠️</span>' if x["id"] in risky_ids else ""
                summary = s.get("tickets", {}).get(x["id"]) or t["missing"]
                p.append(f'<article class="ticket" style="--c:{esc(color_of(x))}"><h3>{h_link(x)}{warn}</h3>'
                         f'<div class="chips">{h_status(x) if st is None else ""}{chips}</div>'
                         f'<p class="summary">📝 {esc(summary)}</p></article>')
            p.append("</div>")
        p.append("</section>")

    if m["notes"]:
        p.append(f'<div class="card notes"><h2>ℹ️ {esc(t["notes"])}</h2><ul>'
                 + "".join(f"<li><bdi>{esc(n)}</bdi></li>" for n in m["notes"]) + "</ul></div>")
    p.append("</div></body></html>")
    return "\n".join(p)


def main():
    utf8_stdout()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("tasks_json")
    p.add_argument("--summaries", help="the agent's summaries JSON (see the docstring)")
    p.add_argument("--format", choices=("md", "html"), default="md")
    p.add_argument("--out", help="default: <report_dir>/clickup-report-<until>.<md|html>")
    p.add_argument("--group-by", choices=("list", "folder", "space", "tag", "status"))
    p.add_argument("--allow-missing", action="store_true", help="render even when summaries are missing (draft)")
    args = p.parse_args()

    data = json.loads(Path(args.tasks_json).read_text(encoding="utf-8"))
    summaries = json.loads(Path(args.summaries).read_text(encoding="utf-8")) if args.summaries else {}
    meta = data["meta"]
    ids = {x["id"] for x in data["tasks"]}
    written = summaries.get("tickets") or {}
    missing = sorted(i for i in ids if not str(written.get(i) or "").strip())
    problems = []
    if missing:
        problems.append(f"{len(missing)} ticket(s) have no summary: {', '.join(missing)}")
    for key in ("executive_summary", "talking_points"):
        if not summaries.get(key):
            problems.append(f"{key} is empty")
    unknown = sorted(set(written) - ids)
    if problems and not args.allow_missing:
        emit({"ok": False, "error": "SUMMARIES_INCOMPLETE", "problems": problems, "missing_ids": missing})
        return 5

    group_by = args.group_by or meta.get("group_by") or "list"
    m = model(data, summaries, group_by)
    text = render_html(m) if args.format == "html" else render_md(m)
    if args.out:
        out = Path(args.out).expanduser()
    else:
        out = Path(meta.get("report_dir") or ".").expanduser() / f"clickup-report-{meta['period']['until']}.{args.format}"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    emit({"ok": True, "out": str(out), "format": args.format, "group_by": group_by, "language": m["t"]["lang"],
          "counts": meta["counts"], "at_risk": len(m["risky"]), "problems": problems,
          "unknown_summary_ids": unknown})
    return 0


if __name__ == "__main__":
    sys.exit(main())
