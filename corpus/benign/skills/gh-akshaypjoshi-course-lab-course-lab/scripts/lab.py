#!/usr/bin/env python3
"""course-lab: quizzes on top of course-studio pages.

    python3 lab.py build <course-dir> [--catalog]
        Builds the course with course-studio (course page + every written chapter), then adds
        each chapter's quiz (chapters/<nn-slug>/quiz.json) to its page and the final test
        (final-quiz.json) to the course page. --catalog also rebuilds the course catalog.

    python3 lab.py validate <quiz.json> [--course-dir <course-dir>]
        Checks one quiz without building (structure, difficulty mix, answer skew, sections).

    python3 lab.py quiz <quiz.json> <course-dir>
        A standalone quiz page in <course-dir>/dist/ (for retests after an evaluation). Every
        question needs "chapter" (or a top-level "chapter") so its section link resolves.

Quiz format: references/quiz-format.md. Exit code 1 on any ERROR; WARNs should be fixed too.
"""
import base64
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
DIFFS = ("easy", "medium", "hard")
DEFAULT_MIX = {"easy": 3, "medium": 4, "hard": 3}


# ---------- locate course-studio ----------
def find_course_studio() -> Path:
    cands = [os.environ.get("COURSE_STUDIO")]
    mnt = Path("/mnt/skills")
    if mnt.exists():
        cands += [mnt / "user/course-studio"] + sorted(p for p in mnt.glob("*/course-studio") if p.parent.name != "user")
    home = Path.home()
    cands += [Path.cwd() / ".claude/skills/course-studio", Path.cwd() / ".agents/skills/course-studio"]
    cands += [home / ".claude/skills/course-studio", home / ".agents/skills/course-studio"]
    cands += sorted(home.glob(".claude/skills/**/course-studio")) + sorted(HERE.parent.parent.glob("*course-studio*"))
    # Claude Code plugin installs: marketplaces/<m>/skills/course-studio, cache/<m>/course-studio/<version>/skills/course-studio
    cands += sorted(home.glob(".claude/plugins/marketplaces/*/skills/course-studio"))
    cands += sorted(home.glob(".claude/plugins/cache/*/course-studio/*/skills/course-studio"), reverse=True)
    for c in cands:
        if c and (Path(c) / "scripts" / "build_chapter.py").exists():
            return Path(c)
    sys.exit("ERROR: course-studio skill not found (a folder with scripts/build_chapter.py). Set COURSE_STUDIO=<path>.")


CS = None


def cs():
    global CS
    if CS is None:
        CS = find_course_studio()
        sys.path.insert(0, str(CS / "scripts"))
    return CS


def chapter_dir(ch: dict) -> str:
    return ch.get("dir") or f'{int(ch["n"]):02d}-{ch["slug"]}'


# ---------- page parsing ----------
def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#x27;", "'").strip()


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def sections_of(html_text: str):
    """[(id, number, title)] of the numbered ## sections in a built course-studio page."""
    out = []
    for m in re.finditer(r'<h2 id="([^"]+)"><span class="num">(\d+)</span>(.*?)</h2>', html_text, re.S):
        out.append((m.group(1), m.group(2), strip_tags(m.group(3))))
    return out


def resolve_section(ref: str, secs):
    if not ref:
        return None
    r = norm(str(ref).lstrip("#"))
    for sid, num, title in secs:
        if norm(sid) == r or norm(title) == r:
            return sid, num, title
    for sid, num, title in secs:
        if norm(title).startswith(r) or r.startswith(norm(title)):
            return sid, num, title
    return None


# ---------- validation ----------
def validate(quiz: dict, scope: str):
    errs, warns = [], []
    qs = quiz.get("questions") or []
    if not quiz.get("title"):
        errs.append("missing 'title'")
    if not qs:
        errs.append("no questions")
        return errs, warns
    want = quiz.get("mix", DEFAULT_MIX)
    if len(qs) != sum(want.values()):
        warns.append(f"{len(qs)} questions; course-lab's standard is {sum(want.values())}")
    got = Counter(q.get("difficulty") for q in qs)
    for d in DIFFS:
        if want.get(d) and not got.get(d):
            errs.append(f"no {d} questions (mix must include easy, medium and hard)")
    if all(got.get(d) for d in DIFFS) and {d: got.get(d, 0) for d in DIFFS} != {d: want.get(d, 0) for d in DIFFS}:
        warns.append(f"difficulty mix {dict((d, got.get(d, 0)) for d in DIFFS)} differs from {want}")
    seen = set()
    for i, q in enumerate(qs, 1):
        p = f"Q{i}"
        if q.get("difficulty") not in DIFFS:
            errs.append(f"{p}: difficulty must be easy/medium/hard")
        for k in ("question", "explanation", "topic"):
            if not str(q.get(k, "")).strip():
                errs.append(f"{p}: missing '{k}'")
        opts = q.get("options") or []
        if not 2 <= len(opts) <= 6:
            errs.append(f"{p}: needs 2–6 options (has {len(opts)})")
        elif len(opts) != 4:
            warns.append(f"{p}: {len(opts)} options; use 4")
        n = [re.sub(r"\s+", " ", str(o)).strip().lower() for o in opts]  # keep symbols: O(n) ≠ O(n²)
        if len(set(n)) != len(n) or not all(str(o).strip() for o in opts):
            errs.append(f"{p}: options must be unique and non-empty")
        a = q.get("answer")
        if not isinstance(a, int) or not 0 <= a < len(opts):
            errs.append(f"{p}: 'answer' must be a 0-based index into options")
        rats = q.get("rationales")
        if rats is not None:
            if len(rats) != len(opts):
                errs.append(f"{p}: 'rationales' must have one entry per option (null for the correct one)")
            elif isinstance(a, int) and sum(1 for k, r in enumerate(rats) if k != a and not r) > 0:
                warns.append(f"{p}: a wrong option has no rationale")
        else:
            warns.append(f"{p}: no 'rationales'; say why each wrong option is tempting and wrong")
        if any(re.search(r"\b(all|none) of the above\b", str(o), re.I) for o in opts):
            warns.append(f"{p}: avoid 'all/none of the above'")
        if scope == "chapter" and not q.get("section"):
            errs.append(f"{p}: missing 'section' (the ## heading it tests)")
        if scope in ("final", "standalone") and not (q.get("chapter") or quiz.get("chapter")):
            errs.append(f"{p}: missing 'chapter'")
        key = norm(str(q.get("question", "")))
        if key in seen:
            errs.append(f"{p}: duplicate question")
        seen.add(key)
    pos = Counter(q.get("answer") for q in qs if isinstance(q.get("answer"), int))
    top, c = pos.most_common(1)[0] if pos else (0, 0)
    if len(qs) >= 6 and c / len(qs) > 0.4:
        warns.append(f"answer skew: option {'ABCDEF'[top]} is correct in {c}/{len(qs)} questions; rebalance")
    if len(qs) >= 4 and len(pos) < 3:
        warns.append("correct answers use fewer than 3 positions; rebalance")
    topics = {q.get("topic") for q in qs}
    if len(qs) >= 8 and len(topics) < 3:
        warns.append(f"only {len(topics)} topics; spread questions over at least 3")
    if scope == "final":
        chs = Counter(q.get("chapter") for q in qs)
        if len(chs) < 2:
            warns.append("final test covers one chapter only")
    return errs, warns


def report(name, errs, warns):
    for e in errs:
        print(f"ERROR {name}: {e}")
    for w in warns:
        print(f"WARN  {name}: {w}")
    return not errs


# ---------- assembly ----------
def pack(obj) -> str:
    return base64.b64encode(json.dumps(obj, ensure_ascii=False).encode()).decode()


def section_html(payload: dict, anchor="quiz") -> str:
    return f'<section class="lab" id="{anchor}" data-quiz="{pack(payload)}"><noscript>This quiz needs JavaScript.</noscript></section>'


def add_assets(html_text: str) -> str:
    if "course-lab quiz runtime" in html_text:
        return html_text
    css = (ASSETS / "quiz.css").read_text(encoding="utf-8")
    js = (ASSETS / "quiz.js").read_text(encoding="utf-8").replace("</script", "<\\/script")
    html_text = html_text.replace("</head>", f"<style>{css}</style>\n</head>", 1)
    return html_text.replace("</body>", f"<script>{js}</script>\n</body>", 1)


def resolve_questions(quiz, course_dir: Path, course: dict, here_slug=None):
    """Attach link {href,label} and group to every question; return errors."""
    errs, cache = [], {}
    chapters = {int(c["n"]): c for c in course.get("chapters", [])}

    def page_secs(n):
        if n not in cache:
            ch = chapters.get(n)
            if not ch:
                cache[n] = (None, None, f"chapter {n} is not in course.json")
            else:
                pg = course_dir / "dist" / f"{chapter_dir(ch)}.html"
                cache[n] = (ch, sections_of(pg.read_text(encoding="utf-8")), None) if pg.exists() else (ch, None, f"chapter {n} has no built page (write it first)")
        return cache[n]

    out = []
    for i, q in enumerate(quiz["questions"], 1):
        q = dict(q)
        n = q.get("chapter", quiz.get("chapter"))
        if n is None and here_slug:
            ch, secs = here_slug
            href_base = ""
        else:
            ch, secs, err = page_secs(int(n))
            if err:
                errs.append(f"Q{i}: {err}")
                out.append(q)
                continue
            href_base = f"{chapter_dir(ch)}.html"
            if quiz.get("_scope") == "final":
                q["group"] = f'Ch {int(ch["n"]):02d} · {ch["title"]}'
        ref = q.get("section")
        hit = resolve_section(ref, secs) if ref else None
        if ref and not hit:
            errs.append(f"Q{i}: section '{ref}' not found in {ch['title'] if ch else 'this chapter'}: use a ## heading's text or id")
        if hit:
            sid, num, title = hit
            label = f"§{num} {title}" + (f' (Ch {int(ch["n"]):02d})' if href_base and quiz.get("_scope") != "chapter" else "")
            q["link"] = {"href": f"{href_base}#{sid}", "label": label}
        elif href_base:
            q["link"] = {"href": href_base, "label": ch["title"]}
        for k in ("section", "chapter"):
            q.pop(k, None)
        out.append(q)
    return out, errs


def inject_chapter(page: Path, quiz: dict, course: dict, course_dir: Path, ch: dict):
    text = page.read_text(encoding="utf-8")
    secs = sections_of(text)
    quiz["_scope"] = "chapter"
    qs, errs = resolve_questions(quiz, course_dir, course, here_slug=(ch, secs))
    if errs:
        return errs
    payload = {"id": quiz.get("id") or f'{course["slug"]}-{chapter_dir(ch)}', "title": quiz["title"],
               "course": course.get("title"), "scope": "chapter", "num": f"{len(secs) + 1:02d}",
               "heading": quiz.get("heading", "Test yourself"), "intro": quiz.get("intro", ""), "questions": qs}
    block = section_html(payload)
    if '<nav class="pager">' in text:
        text = text.replace('<nav class="pager">', block + '<nav class="pager">', 1)
    else:
        text = text.replace("</main>", block + "</main>", 1)
    text = re.sub(r'(<nav class="toc">.*?)(</ol></nav>)', lambda m: m.group(1) + '<li><a href="#quiz">Test yourself</a></li>' + m.group(2), text, count=1, flags=re.S)
    page.write_text(add_assets(text), encoding="utf-8")
    return []


def inject_final(page: Path, quiz: dict, course: dict, course_dir: Path):
    quiz["_scope"] = "final"
    qs, errs = resolve_questions(quiz, course_dir, course)
    if errs:
        return errs
    payload = {"id": quiz.get("id") or f'{course["slug"]}-final', "title": quiz["title"], "course": course.get("title"),
               "scope": "final", "heading": quiz.get("heading", "Final test"), "intro": quiz.get("intro", ""), "questions": qs}
    text = page.read_text(encoding="utf-8")
    text = text.replace("</main>", section_html(payload, "final-test") + "</main>", 1)
    page.write_text(add_assets(text), encoding="utf-8")
    return []


def load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"ERROR {p}: invalid JSON: {e}")


def cmd_build(course_dir: Path, catalog: bool):
    root = cs()
    r = subprocess.run([sys.executable, str(root / "scripts" / "build_course.py"), str(course_dir)], text=True, capture_output=True)
    print(r.stdout.strip())
    if r.returncode:
        print(r.stderr.strip())
        sys.exit("ERROR: course-studio build failed")
    from _pages import load_course  # noqa: E402  (course-studio)
    course = load_course(course_dir / "course.json")
    ok, n_quiz = True, 0
    for ch in course.get("chapters", []):
        qf = course_dir / "chapters" / chapter_dir(ch) / "quiz.json"
        page = course_dir / "dist" / f"{chapter_dir(ch)}.html"
        if not qf.exists():
            if page.exists():
                print(f"WARN  {chapter_dir(ch)}: written chapter has no quiz.json")
            continue
        if not page.exists():
            print(f"WARN  {qf}: quiz for a chapter that isn't written yet, skipped")
            continue
        quiz = load(qf)
        e, w = validate(quiz, "chapter")
        ok &= report(qf.parent.name + "/quiz.json", e, w)
        if not e:
            e2 = inject_chapter(page, quiz, course, course_dir, ch)
            ok &= report(qf.parent.name + "/quiz.json", e2, [])
            n_quiz += not e2
    fq = course_dir / "final-quiz.json"
    if fq.exists():
        quiz = load(fq)
        e, w = validate(quiz, "final")
        ok &= report("final-quiz.json", e, w)
        if not e:
            e2 = inject_final(course_dir / "dist" / "index.html", quiz, course, course_dir)
            ok &= report("final-quiz.json", e2, [])
            if not e2:
                print("final test added to the course page")
    if catalog:
        import build_course  # course-studio; build_catalog only writes catalog.html
        build_course.build_catalog(course_dir.parent)
    print(f"{n_quiz} chapter quiz(zes) added")
    sys.exit(0 if ok else 1)


def cmd_validate(qf: Path, course_dir):
    quiz = load(qf)
    scope = {"final-quiz.json": "final", "quiz.json": "chapter"}.get(qf.name, "standalone")
    e, w = validate(quiz, scope)
    ok = report(qf.name, e, w)
    if ok and course_dir:
        cs()
        from _pages import load_course  # noqa: E402
        course = load_course(course_dir / "course.json")
        if scope == "chapter":
            ch_dir = qf.parent.name
            ch = next((c for c in course["chapters"] if chapter_dir(c) == ch_dir), None)
            page = course_dir / "dist" / f"{ch_dir}.html"
            if ch and page.exists():
                quiz["_scope"] = "chapter"
                _, e2 = resolve_questions(quiz, course_dir, course, here_slug=(ch, sections_of(page.read_text(encoding="utf-8"))))
                ok &= report(qf.name, e2, [])
            else:
                print(f"WARN  {qf.name}: chapter page not built, sections not checked")
        else:
            quiz["_scope"] = scope
            _, e2 = resolve_questions(quiz, course_dir, course)
            ok &= report(qf.name, e2, [])
    print("ok" if ok and not w else ("ok with warnings" if ok else "failed"))
    sys.exit(0 if ok else 1)


def cmd_quiz(qf: Path, course_dir: Path):
    cs()
    from _pages import accent_vars, esc, load_course, page  # noqa: E402
    course = load_course(course_dir / "course.json")
    quiz = load(qf)
    e, w = validate(quiz, "standalone")
    if not report(qf.name, e, w):
        sys.exit(1)
    quiz["_scope"] = "standalone"
    qs, e2 = resolve_questions(quiz, course_dir, course)
    if not report(qf.name, e2, []):
        sys.exit(1)
    qid = quiz.get("id") or qf.stem
    payload = {"id": qid, "title": quiz["title"], "course": course.get("title"), "scope": "retest",
               "heading": quiz.get("heading", quiz["title"]), "intro": quiz.get("intro", ""), "questions": qs}
    body = (f'<main class="page"><nav class="crumbs"><a href="index.html">{esc(course.get("title", "Course"))}</a><span>/</span>'
            f'<span>{esc(quiz["title"])}</span></nav>{section_html(payload)}</main>')
    out = course_dir / "dist" / f"{re.sub(r'[^a-z0-9-]+', '-', qid.lower())}.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(add_assets(page(quiz["title"], body, accent_vars(course))), encoding="utf-8")
    print(f"wrote {out}")


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    if a[0] == "build":
        cmd_build(Path(a[1]).resolve(), "--catalog" in a)
    elif a[0] == "validate":
        cd = Path(a[a.index("--course-dir") + 1]).resolve() if "--course-dir" in a else None
        cmd_validate(Path(a[1]).resolve(), cd)
    elif a[0] == "quiz" and len(a) >= 3:
        cmd_quiz(Path(a[1]).resolve(), Path(a[2]).resolve())
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
