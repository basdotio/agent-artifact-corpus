#!/usr/bin/env python3
"""Check built course-lab pages: runs course-studio's page check, then takes every quiz
in a headless browser and verifies the grading.

    python3 check_lab.py <course-dir>/dist | <page.html> [--mobile] [--dark] [--all]

--all runs desktop light, then phone + dark. A page path checks only that page.

Per quiz: answers all correct (must score n/n, level Mastered), all wrong (0/n, Needs review),
a mixed attempt with guesses and a blank (counts, "confident mistakes" and "guessed" insights,
blank-submit confirmation), checks every "Revisit" link points at a real heading, and checks the
copy-for-Claude report. Screenshots: quiz-<page>-<k>-before.png / -result.png.
Exit 1 on any problem.
"""
import base64
import json
import re
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lab import find_course_studio  # noqa: E402


def payloads(html_text):
    return [json.loads(base64.b64decode(m)) for m in re.findall(r'<section class="lab" id="[^"]+" data-quiz="([^"]+)"', html_text)]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    target = Path(args[0]).resolve()
    if "--all" in sys.argv:
        bad = check(target, False, False) + check(target, True, True)
    else:
        bad = check(target, "--mobile" in sys.argv, "--dark" in sys.argv)
    print(f"RESULT: {len(bad)} problem(s)" + (", clean" if not bad else ""))
    sys.exit(1 if bad else 0)


def check(target: Path, mobile: bool, dark: bool):
    dist = target if target.is_dir() else target.parent
    print(f"== {'phone' if mobile else 'desktop'} · {'dark' if dark else 'light'}")
    suffix = "-".join(x for x, on in (("mobile", mobile), ("dark", dark)) if on)
    shots = dist / ("shots" + (f"-{suffix}" if suffix else ""))
    problems = []

    cs = find_course_studio()
    flags = (["--mobile"] if mobile else []) + (["--dark"] if dark else [])
    r = subprocess.run([sys.executable, str(cs / "scripts" / "check_pages.py"), str(target), str(shots)] + flags, text=True, capture_output=True)
    for line in r.stdout.splitlines():
        if line.startswith("PROBLEM") and "is pending" not in line:
            problems.append(line[9:])
        elif "pending" in line:
            print(line)

    pool = sorted(dist.glob("*.html")) if target.is_dir() else [target]
    pages = [p for p in pool if "data-quiz=" in p.read_text(encoding="utf-8")]
    with sync_playwright() as p:
        b = p.chromium.launch()
        for page_path in pages:
            text = page_path.read_text(encoding="utf-8")
            for k, quiz in enumerate(payloads(text)):
                tag = f"{page_path.name} quiz {k + 1}"
                qs = quiz["questions"]
                n = len(qs)
                # links resolve
                for i, q in enumerate(qs, 1):
                    link = q.get("link")
                    if not link:
                        problems.append(f"{tag}: Q{i} has no revisit link")
                        continue
                    target, _, anchor = link["href"].partition("#")
                    tp = page_path if not target else dist / target
                    if not tp.exists():
                        problems.append(f"{tag}: Q{i} links to missing page {target}")
                    elif anchor and f'id="{anchor}"' not in tp.read_text(encoding="utf-8"):
                        problems.append(f"{tag}: Q{i} links to missing section #{anchor} in {tp.name}")

                def run(plan, guesses=(), shot=None):
                    pg = b.new_page(viewport={"width": 390 if mobile else 1180, "height": 900},
                                    color_scheme="dark" if dark else "light", device_scale_factor=2 if mobile else 1)
                    errs = []
                    pg.on("pageerror", lambda e: errs.append(str(e)))
                    pg.goto(page_path.as_uri())
                    pg.wait_for_timeout(300)
                    sec = pg.locator("section.lab").nth(k)
                    sec.scroll_into_view_if_needed()
                    if shot:
                        sec.screenshot(path=str(shots / f"quiz-{page_path.stem}-{k + 1}-before.png"))
                    cards = sec.locator(".lab-q")
                    for i, choice in enumerate(plan):
                        if choice is not None:
                            cards.nth(i).locator(".lab-opt").nth(choice).click()
                        if i in guesses:
                            cards.nth(i).locator(".lab-guess input").check()
                    submit = sec.locator(".lab-bar .lab-btn")
                    submit.click()
                    blank = any(c is None for c in plan)
                    note = sec.locator(".lab-note").inner_text()
                    if blank:
                        if "unanswered" not in note:
                            problems.append(f"{tag}: blank submit did not ask for confirmation")
                        submit.click()
                    pg.wait_for_timeout(500)
                    res = sec.locator(".lab-result")
                    out = {"big": res.locator(".lab-big").inner_text().replace("\n", ""), "badge": res.locator(".lab-badge").inner_text(),
                           "insights": res.locator(".lab-insights").inner_text(), "errs": errs}
                    sec.locator('[data-act="copy"]').click()
                    pg.wait_for_timeout(200)
                    out["report"] = sec.get_attribute("data-report") or ""
                    if shot:
                        sec.screenshot(path=str(shots / f"quiz-{page_path.stem}-{k + 1}-result.png"))
                    # retake resets
                    res.locator('[data-act="retake"]').click()
                    pg.wait_for_timeout(200)
                    if sec.locator(".lab-result").count() or sec.locator('.lab-opt[aria-pressed="true"]').count():
                        problems.append(f"{tag}: retake did not reset the quiz")
                    pg.close()
                    return out

                right = [q["answer"] for q in qs]
                wrong = [(q["answer"] + 1) % len(q["options"]) for q in qs]
                a = run(right)
                if a["big"].upper().replace(" ", "") != f"{n}/{n}" or a["badge"].lower() != "mastered":
                    problems.append(f"{tag}: all-correct attempt scored {a['big']} / {a['badge']}")
                z = run(wrong)
                if not z["big"].startswith("0") or z["badge"].lower() != "needs review":
                    problems.append(f"{tag}: all-wrong attempt scored {z['big']} / {z['badge']}")
                # mixed: first half right (Q1 guessed), Q2 blank, rest wrong and sure
                mix = [right[i] if i < n // 2 else wrong[i] for i in range(n)]
                mix[1] = None
                m = run(mix, guesses={0}, shot=True)
                exp = n // 2 - 1
                if not m["big"].startswith(str(exp)):
                    problems.append(f"{tag}: mixed attempt scored {m['big']}, expected {exp}/{n}")
                if "Confident mistakes" not in m["insights"] or "guessed" not in m["insights"].lower():
                    problems.append(f"{tag}: insights missing confident-mistake / guessed notes")
                if "course-lab results" not in m["report"] or f"Q{n} " not in m["report"]:
                    problems.append(f"{tag}: copy-for-Claude report is incomplete")
                for e in a["errs"] + z["errs"] + m["errs"]:
                    problems.append(f"{tag}: page error {e}")
                print(f"  {tag}: {n} questions: all right {a['big']} {a['badge']}, all wrong {z['big']} {z['badge']}, mixed {m['big']} {m['badge']}")
        b.close()
    print(f"{len(pages)} page(s) with quizzes checked; screenshots in {shots}")
    problems = list(dict.fromkeys(problems))
    for pr in problems:
        print("PROBLEM:", pr)
    return problems


if __name__ == "__main__":
    main()
