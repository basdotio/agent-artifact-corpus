#!/usr/bin/env python3
"""kb.py — resume-learn 的个人术语库（纯标准库；读 PDF 时借 pypdf）

数据目录默认 ~/Desktop/面试/术语库/（环境变量 RESUME_KB 可改）：
  index.json      真相源：术语 → 状态/别名/分类/卡片路径/在哪些简历里见过
  cards/*.md      每个术语一张学习卡
  README.md       render 生成的总览（按分类、按状态）

子命令：
  pdf <file>                          打印 PDF 全文（全部页）
  pending [dir ...]                   列出还没处理过的简历 PDF（默认扫 ~/Desktop 和 ~/Desktop/算法）
  lookup <term> [<term> ...]          逐个查：已有(状态/卡片) 还是 NEW；按别名和归一化匹配
  add <terms.json>                    批量入库：新术语写卡片，已有术语只追加「见过」记录
  cards <term> [<term> ...]           按给定顺序打印卡片正文（标题降到 ###），拼学习包用
  mark <status> <term> [<term> ...]   改状态：new / learning / mastered / known
  link <links.json>                   批量挂讲义：{术语: 讲义路径}，写进 deep_dive 字段
  processed <pdf> --candidate 姓名    记录这份简历已处理（按内容哈希，改名也认得）
  stats                               各状态数量 + 最近处理的简历
  trend [--last N]                    最近 N 份简历里反复出现的术语（行业信号）
  review [--n 10]                     挑出该复习的术语（非 mastered，见得多/入库早的优先）
  seed-analyse                        把 ~/Desktop/Analyse/ 里 grok 讲义登记成 learning（避免重复学）
  render                              重写 README.md 总览
"""
import argparse, datetime as dt, hashlib, json, os, re, subprocess, sys, unicodedata
from pathlib import Path

KB = Path(os.path.expanduser(os.environ.get("RESUME_KB", "~/Desktop/面试/术语库")))
INDEX = KB / "index.json"
CARDS = KB / "cards"
STATUSES = ["new", "learning", "mastered", "known"]
STATUS_CN = {"new": "🆕 待学", "learning": "📖 学习中", "mastered": "✅ 已掌握", "known": "☑️ 本来就会"}
COPILOT_PY = Path.home() / ".claude/skills/interview-copilot/.venv/bin/python"


def today():
    return dt.date.today().isoformat()


def norm(s):
    """归一化：小写、去空格/连字符/标点，全角转半角。'Diffusion-Policy' == 'diffusion policy' == 'DiffusionPolicy'"""
    s = s.strip().lower()
    s = "".join(chr(ord(c) - 0xFEE0) if 0xFF01 <= ord(c) <= 0xFF5E else c for c in s)
    return re.sub(r"[\s\-_·./（）()\[\]【】,，:：'\"]+", "", s)


def load():
    if INDEX.exists():
        return json.loads(INDEX.read_text())
    return {"terms": {}, "resumes": {}}


def save(db):
    KB.mkdir(parents=True, exist_ok=True)
    tmp = INDEX.with_suffix(".tmp")
    tmp.write_text(json.dumps(db, ensure_ascii=False, indent=1))
    tmp.replace(INDEX)


def find(db, term):
    """返回库里的规范名，找不到返回 None。先精确归一化匹配名字和别名。"""
    n = norm(term)
    if not n:
        return None
    for name, t in db["terms"].items():
        if norm(name) == n or any(norm(a) == n for a in t.get("aliases", [])):
            return name
    return None


def safe_filename(s):
    s = re.sub(r"[/\\:*?\"<>|\s]+", "-", s.strip()).strip("-")
    return s[:80] or "term"


# ---------- PDF ----------
def pdf_text(path):
    code = ("import sys; from pypdf import PdfReader; r=PdfReader(sys.argv[1]); "
            "print('\\n\\n'.join(f'--- 第{i+1}页 ---\\n' + (pg.extract_text() or '') for i, pg in enumerate(r.pages)))")
    try:
        import pypdf  # noqa: F401
        py = [sys.executable]
    except ImportError:
        py = [str(COPILOT_PY)] if COPILOT_PY.exists() else ["uv", "run", "--with", "pypdf", "python"]
    r = subprocess.run(py + ["-c", code, str(path)], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"读 PDF 失败：{r.stderr.strip()[-500:]}")
    return r.stdout


def file_hash(path):
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()[:16]


# ---------- commands ----------
def cmd_pdf(a):
    # NFKC：有些 PDF 用康熙部首字符（⼤⼀⾦）冒充常用汉字，不归一化会搜不到、查不到库
    text = unicodedata.normalize("NFKC", pdf_text(a.file))
    print(text)
    if len(re.sub(r"\s", "", text)) < 200:
        print("\n[kb] ⚠️ 提取出的文字很少，可能是扫描件/图片简历：改用 Read 工具直接看 PDF 页面。", file=sys.stderr)


def cmd_pending(a):
    db = load()
    dirs = a.dirs or [str(Path.home() / "Desktop"), str(Path.home() / "Desktop/算法")]
    done = set(db["resumes"].keys())
    rows = []
    for d in dirs:
        for p in sorted(Path(os.path.expanduser(d)).glob("*.pdf")):
            h = file_hash(p)
            if h not in done:
                rows.append((p.stat().st_mtime, p))
    rows.sort(reverse=True)
    looks_resume = re.compile(r"简历|resume|cv|应届|实习|工程师|算法|【.*】", re.I)
    for _, p in rows:
        tag = "" if looks_resume.search(p.name) else "  (文件名不像简历，确认一下)"
        print(f"{p}{tag}")
    print(f"[kb] 未处理 {len(rows)} 份", file=sys.stderr)


def cmd_lookup(a):
    db = load()
    for term in a.terms:
        name = find(db, term)
        if name:
            t = db["terms"][name]
            print(f"HAVE\t{term}\t→ {name}\t{t['status']}\tseen={len(t.get('seen', []))}\t{t.get('card', '')}")
        else:
            # 没精确命中时给「可能相关」提示：grok 讲义的标题常带后缀（如「Diffusion-Policy原理」）
            n = norm(term)
            rel = [nm for nm, t in db["terms"].items()
                   if len(n) >= 3 and any(n in norm(x) or (len(norm(x)) >= 3 and norm(x) in n)
                                          for x in [nm] + t.get("aliases", []))]
            ment = []
            if len(term) >= 3:
                for nm, t in db["terms"].items():
                    f = t.get("deep_dive") or (str(KB / t["card"]) if t.get("card") else "")
                    if f and Path(f).exists() and nm not in rel:
                        if Path(f).read_text(errors="ignore").lower().count(term.lower()) >= 2:
                            ment.append(nm)
            print(f"NEW\t{term}" + (f"\tRELATED: {' | '.join(rel[:5])}" if rel else "")
                  + (f"\tMENTIONED_IN: {' | '.join(ment[:5])}" if ment else ""))


def cmd_add(a):
    """terms.json: [{"term","aliases":[],"category","card_md","deep_dive_worthy":bool,
                    "seen":{"candidate","date","context"}}]
    已有术语：只追加 seen、合并别名，不覆盖卡片（除非 --overwrite-cards）。"""
    db = load()
    items = json.loads(Path(a.file).read_text())
    CARDS.mkdir(parents=True, exist_ok=True)
    added = updated = 0
    for it in items:
        term = it["term"].strip()
        if it.get("card_file") and not it.get("card_md"):
            it["card_md"] = Path(os.path.expanduser(it["card_file"])).read_text()
        if it.get("same_as"):
            name = find(db, it["same_as"])
            if not name:
                print(f"[kb] ⚠️ same_as 找不到「{it['same_as']}」，{term} 按新术语处理")
        else:
            name = find(db, term)
            if not name:
                for al in it.get("aliases", []):
                    hit = find(db, al)
                    if hit:
                        print(f"[kb] ⚠️ {term} 经别名「{al}」合并进已有的「{hit}」——不是同一个东西就把这个别名删掉重跑")
                        name = hit
                        break
        seen = it.get("seen")
        if seen and not seen.get("date"):
            seen["date"] = today()
        if name is None:
            fn = safe_filename(term)
            card = CARDS / f"{fn}.md"
            i = 2
            while card.exists():
                card = CARDS / f"{fn}-{i}.md"; i += 1
            if it.get("card_md"):
                card.write_text(it["card_md"].rstrip() + "\n")
            db["terms"][term] = {
                "aliases": sorted(set(it.get("aliases", []))),
                "category": it.get("category", "未分类"),
                "status": it.get("status", "new"),
                "card": str(card.relative_to(KB)) if it.get("card_md") else "",
                "deep_dive": it.get("deep_dive", ""),
                "deep_dive_worthy": bool(it.get("deep_dive_worthy")),
                "added": today(),
                "seen": [seen] if seen else [],
            }
            added += 1
        else:
            t = db["terms"][name]
            t["aliases"] = sorted(set(t.get("aliases", [])) | set(it.get("aliases", [])) | ({term} - {name}))
            if seen and not any(s.get("candidate") == seen.get("candidate") for s in t.get("seen", [])):
                t.setdefault("seen", []).append(seen)
            if it.get("card_md") and (a.overwrite_cards or not t.get("card")):
                card = KB / t["card"] if t.get("card") else CARDS / f"{safe_filename(name)}.md"
                card.write_text(it["card_md"].rstrip() + "\n")
                t["card"] = str(card.relative_to(KB))
            updated += 1
    save(db)
    render(db)
    print(f"[kb] 新增 {added}，已有并追加记录 {updated}，库内共 {len(db['terms'])} 条")


def cmd_mark(a):
    if a.status not in STATUSES:
        sys.exit(f"状态只能是 {STATUSES}")
    db = load()
    for term in a.terms:
        name = find(db, term)
        if not name:
            if a.status == "known":  # 「本来就会」的基础项允许直接登记，免得下次再出卡
                db["terms"][term] = {"aliases": [], "category": "基础", "status": "known", "card": "",
                                     "added": today(), "seen": []}
                print(f"登记 {term} → known")
            else:
                print(f"找不到 {term}（先 add）")
            continue
        db["terms"][name]["status"] = a.status
        db["terms"][name]["status_at"] = today()
        print(f"{name} → {a.status}")
    save(db)
    render(db)


def cmd_link(a):
    db = load()
    n = 0
    for term, path in json.loads(Path(a.file).read_text()).items():
        name = find(db, term)
        if not name:
            print(f"[kb] 找不到 {term}")
            continue
        db["terms"][name]["deep_dive"] = str(Path(os.path.expanduser(path)))
        n += 1
    save(db)
    render(db)
    print(f"[kb] 挂上讲义 {n} 条")


def cmd_processed(a):
    db = load()
    db["resumes"][file_hash(a.pdf)] = {"file": str(Path(a.pdf).resolve()), "candidate": a.candidate,
                                       "date": today(), "pack": a.pack or ""}
    save(db)
    print(f"[kb] 记录已处理：{a.candidate}")


def cmd_stats(a):
    db = load()
    cnt = {s: 0 for s in STATUSES}
    for t in db["terms"].values():
        cnt[t.get("status", "new")] = cnt.get(t.get("status", "new"), 0) + 1
    print("术语库：" + "  ".join(f"{STATUS_CN[s]} {cnt[s]}" for s in STATUSES) + f"  （共 {len(db['terms'])}）")
    rs = sorted(db["resumes"].values(), key=lambda r: r["date"], reverse=True)
    print(f"已处理简历 {len(rs)} 份" + ("：" + "、".join(r["candidate"] for r in rs[:10]) if rs else ""))


def cmd_trend(a):
    db = load()
    recent = [r["candidate"] for r in sorted(db["resumes"].values(), key=lambda r: r["date"], reverse=True)[:a.last]]
    rs = set(recent)
    rows = []
    for name, t in db["terms"].items():
        who = {s.get("candidate") for s in t.get("seen", [])} & rs
        if len(who) >= 2:
            rows.append((len(who), name, t))
    rows.sort(key=lambda x: (-x[0], x[1]))
    print(f"最近 {len(recent)} 份简历里出现 ≥2 次的术语：")
    for n, name, t in rows[:40]:
        print(f"  {n:>2} 份  {name}  [{t.get('category', '')}]  {STATUS_CN.get(t.get('status'), '')}")
    if not rows:
        print("  （还没有重复出现的术语，简历积累多了再看）")


def cmd_review(a):
    db = load()
    rows = [(name, t) for name, t in db["terms"].items() if t.get("status") in ("new", "learning") and t.get("card")]
    rows.sort(key=lambda x: (-len(x[1].get("seen", [])), x[1].get("added", "")))
    for name, t in rows[:a.n]:
        print(f"{name}\t{t['status']}\tseen={len(t.get('seen', []))}\t{KB / t['card']}")


def cmd_seed_analyse(a):
    db = load()
    d = Path.home() / "Desktop/Analyse"
    n = 0
    for p in sorted(d.glob("20??-??-??-*.md")):
        topic = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", p.stem)
        if find(db, topic):
            continue
        head = re.split(r"[-—与和及原理]", topic)[0].strip()
        aliases = [head] if head and head != topic and len(norm(head)) >= 2 else []
        db["terms"][topic] = {"aliases": aliases, "category": "grok讲义", "status": "learning", "card": "",
                              "deep_dive": str(p), "added": today(), "seen": []}
        n += 1
    save(db)
    render(db)
    print(f"[kb] 从 Analyse 登记 {n} 个已学主题（状态 learning，可用 mark mastered 升级）")


def cmd_cards(a):
    db = load()
    for term in a.terms:
        name = find(db, term)
        t = db["terms"].get(name) if name else None
        if not t or not t.get("card"):
            print(f"[kb] {term} 没有卡片", file=sys.stderr)
            continue
        body = (KB / t["card"]).read_text().rstrip()
        body = re.sub(r"^# ", "### ", body, count=1, flags=re.M)
        print(body + "\n\n---\n")


def render(db):
    lines = ["# 简历术语库", "", f"_由 resume-learn 自动生成，{today()} 更新。别手改这个文件，改状态用 `kb.py mark`。_", ""]
    cnt = {}
    for t in db["terms"].values():
        cnt[t.get("status", "new")] = cnt.get(t.get("status", "new"), 0) + 1
    lines.append("  ".join(f"{STATUS_CN[s]} {cnt.get(s, 0)}" for s in STATUSES))
    lines.append("")
    cats = {}
    for name, t in db["terms"].items():
        if t.get("status") == "known":
            continue
        cats.setdefault(t.get("category", "未分类"), []).append((name, t))
    for cat in sorted(cats):
        lines += [f"## {cat}", "", "| 术语 | 状态 | 见过 | 卡片 / 讲义 |", "|---|---|---|---|"]
        for name, t in sorted(cats[cat], key=lambda x: (-len(x[1].get("seen", [])), x[0])):
            links = []
            if t.get("card"):
                links.append(f"[卡片]({t['card']})")
            if t.get("deep_dive"):
                links.append(f"[讲义]({t['deep_dive']})")
            elif t.get("deep_dive_worthy"):
                links.append("值得 grok 深挖")
            who = "、".join(sorted({s.get("candidate", "") for s in t.get("seen", [])}))
            lines.append(f"| {name} | {STATUS_CN.get(t.get('status'), t.get('status'))} | {who} | {' '.join(links)} |")
        lines.append("")
    known = sorted(n for n, t in db["terms"].items() if t.get("status") == "known")
    if known:
        lines += ["## 本来就会（不出卡）", "", "、".join(known), ""]
    KB.mkdir(parents=True, exist_ok=True)
    (KB / "README.md").write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("pdf"); p.add_argument("file"); p.set_defaults(f=cmd_pdf)
    p = sp.add_parser("pending"); p.add_argument("dirs", nargs="*"); p.set_defaults(f=cmd_pending)
    p = sp.add_parser("lookup"); p.add_argument("terms", nargs="+"); p.set_defaults(f=cmd_lookup)
    p = sp.add_parser("add"); p.add_argument("file"); p.add_argument("--overwrite-cards", action="store_true"); p.set_defaults(f=cmd_add)
    p = sp.add_parser("mark"); p.add_argument("status"); p.add_argument("terms", nargs="+"); p.set_defaults(f=cmd_mark)
    p = sp.add_parser("link"); p.add_argument("file"); p.set_defaults(f=cmd_link)
    p = sp.add_parser("processed"); p.add_argument("pdf"); p.add_argument("--candidate", required=True); p.add_argument("--pack"); p.set_defaults(f=cmd_processed)
    p = sp.add_parser("cards"); p.add_argument("terms", nargs="+"); p.set_defaults(f=cmd_cards)
    p = sp.add_parser("stats"); p.set_defaults(f=cmd_stats)
    p = sp.add_parser("trend"); p.add_argument("--last", type=int, default=20); p.set_defaults(f=cmd_trend)
    p = sp.add_parser("review"); p.add_argument("--n", type=int, default=10); p.set_defaults(f=cmd_review)
    p = sp.add_parser("seed-analyse"); p.set_defaults(f=cmd_seed_analyse)
    p = sp.add_parser("render"); p.set_defaults(f=lambda a: (render(load()), print(f"[kb] 已写 {KB / 'README.md'}")))
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
