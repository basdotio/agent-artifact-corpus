#!/usr/bin/env python3
"""
Flag writing that reads as AI-generated or generic in a resume or cover letter.

This is a detector, not an editor. A hit means "look at this", not "change
this". Hits are graded:
  HARD  - remove or rewrite (stock AI resume words, chatbot phrasing, dashes)
  SOFT  - review in context (may be fine once, a problem when clustered)
  SHAPE - structural tells (uniform bullet length, repeated openers, -ing riders)

Also runs the unslop skill's general scanner when it is installed and merges
its hard hits.

Usage:
    lint.py resume.md
    lint.py cover-letter.md --type cover
    lint.py resume.md --json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import subprocess
import sys
from collections import Counter
from pathlib import Path

# Words and phrases whose use rose sharply in AI-written resumes (Simplify 2023-2026
# data, Wikipedia "Signs of AI writing", recruiter surveys). Kept short on purpose:
# each one is a reliable tell in a resume/cover letter.
HARD = {
    # verbs
    r"spearhead(ed|ing|s)?": "say what you did: led, started, built, ran",
    r"leverag(e|ed|es|ing)": "used / built on, or drop it",
    r"orchestrat(e|ed|es|ing)": "ran, coordinated, or name the actual work (unless the tech meaning: container orchestration)",
    r"hon(e|ed|ing)\b": "drop it or say what improved",
    r"streamlin(e|ed|es|ing)": "say what got shorter/faster and by how much",
    r"synerg(y|ies|ize|istic)": "cut",
    r"utiliz(e|ed|es|ing|ation)": "use / used",
    r"empower(ed|s|ing)?": "say what people could now do",
    r"elevat(e|ed|es|ing)": "improved, raised (with a number)",
    r"harness(ed|es|ing)?": "used",
    r"delv(e|ed|es|ing)": "cut",
    r"championed": "pushed for / argued for / led",
    r"revolutioniz(e|ed|ing)": "say what changed",
    r"pioneer(ed|ing)": "first to X at company (only if true)",
    r"foster(ed|ing|s)?": "built, ran, or cut",
    r"showcas(e|ed|es|ing)": "showed, or cut",
    r"underscor(e|ed|es|ing)": "cut",
    r"navigat(e|ed|ing) (complex|ambiguity|challenges)": "say what the situation was",
    # adjectives / nouns
    r"results-driven|results-oriented": "cut; show results instead",
    r"detail-oriented": "cut",
    r"self-starter|go-getter": "cut",
    r"dynamic (professional|leader|engineer|environment)": "cut",
    r"proven track record": "cut; the bullets are the track record",
    r"fast-paced": "cut or name the pace (weekly releases, 3-person team)",
    r"cutting-edge|state-of-the-art|bleeding-edge": "name the technology",
    r"best-in-class|world-class": "give the comparison or cut",
    r"seamless(ly)?": "say what broke less, or cut",
    r"innovative|innovation-driven": "say what was new",
    r"passionate|passion for": "show it with a fact (side project, talk, OSS)",
    r"thought leader(ship)?": "name the talk, post, or standard",
    r"visionary": "cut",
    r"transformative|transformational": "say what changed",
    r"game[- ]chang(er|ing)": "cut",
    r"impactful": "say the impact",
    r"drive (impact|results|value|growth|innovation)": "say the result",
    r"tapestry|testament|pivotal|landscape|realm|intricate|meticulous(ly)?": "cut",
    r"ever-evolving|rapidly evolving": "cut",
    r"team player": "cut; show a collaboration fact",
    r"excellent (communication|communicator|interpersonal)": "cut; show a communication fact",
    r"strong (work ethic|communication skills)": "cut",
    r"responsible for": "say what you did, not what you were assigned",
    r"duties included": "say what you did",
    r"wide (range|array|variety) of": "name them or say how many",
    r"diverse (range|array|set) of": "name them",
    r"a myriad of|plethora": "cut",
    r"robust and scalable|scalable and robust": "give the scale number",
    # cover letter / chatbot
    r"I am (excited|thrilled|eager|delighted) to": "open with the match, not a feeling",
    r"I('m| am) writing to (express|apply)": "open with the match",
    r"(perfect|ideal|great|strong) fit": "show the fit, don't assert it",
    r"aligns? (perfectly |closely )?with": "say the specific overlap",
    r"resonat(e|es|ed) with me": "say what specifically, or cut",
    r"dream (job|company|role)": "cut",
    r"I would welcome the opportunity|I look forward to the opportunity": "end with a plain next step",
    r"thank you for (your )?(time and )?consideration": "fine once at the end; never twice",
    r"in today's": "cut",
    r"unique (blend|combination|mix) of": "cut; say the two things",
    r"bring (a )?wealth of": "cut",
    r"hit the ground running": "cut",
    r"make a (meaningful|real|significant) (impact|difference)": "say what you'd work on",
    r"(furthermore|moreover|additionally)\b": "cut the connector",
    r"not only\b.{0,60}\bbut also": "state both facts plainly",
    r"it'?s not (just|merely|only)\b": "state the point directly",
    r"\bdeeply\b|\btruly\b|\bgenuinely\b": "cut the intensifier",
}

SOFT = {
    r"\brobust\b": "fine for a technical property, otherwise give the number",
    r"\bscalable\b": "give the scale (rps, users, data size)",
    r"\bkey\b": "fine once; often filler",
    r"\bcrucial|critical\b": "say why",
    r"\benhanc(e|ed|es|ing)\b": "improved (by how much?)",
    r"\boptimiz(e|ed|ing)\b": "say what metric moved",
    r"\bcross-functional\b": "name the teams",
    r"\bstakeholders?\b": "name who (product, finance, customers)",
    r"\bend-to-end\b": "say which ends",
    r"\bcollaborat(ed|ing) (closely )?with\b": "fine; say what came of it",
    r"\bsuccessfully\b": "cut; success is implied",
    r"\bvarious\b|\bnumerous\b|\bmultiple\b": "give the count",
    r"\bhelped\b|\bassisted\b|\bparticipated in\b|\bworked on\b": "weak verb; say your part",
    r"\bensur(e|ed|ing)\b": "say what you did to make it true",
}

RIDERS = re.compile(r",\s+(ensuring|enabling|fostering|driving|resulting in|showcasing|highlighting|"
                    r"demonstrating|empowering|reflecting|underscoring|contributing to|paving the way)\b", re.I)
DASHES = re.compile(r"—|–| -- |(?<=\w)--(?=\w)")
CURLY = re.compile("[‘’“”]")
TRIAD = re.compile(r"\b\w+(?: \w+)?, \w+(?: \w+)?,? and \w+(?: \w+)?\b")
STACK = re.compile(r"^Stack:\s", re.I)
PRONOUN = re.compile(r"(?<![\w/-])(I|[Mm]e|[Mm]y|[Ww]e|[Oo]ur|us)(?![\w/-])")
CONTEXT_OPENER = re.compile(r"^(As part of|In order to|Working (with|on)|Tasked with|While|During|Through|With the|In my role)\b", re.I)
TEAM_WORDS = re.compile(r"\b(collaborat\w*|assist\w*|support(?:ed|ing)|helped|participat\w*)\b", re.I)
WORDS_MIN, WORDS_MAX = 475, 750
RECENT_MAX, OLDER_MAX = 5, 3


def scrub(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def lines_with_numbers(text: str):
    return [(i + 1, l) for i, l in enumerate(text.splitlines())]


def scan_phrases(text: str, table: dict, level: str, out: list):
    for n, line in lines_with_numbers(text):
        if line.startswith("#") and level != "HARD":
            continue
        for pat, fix in table.items():
            for m in re.finditer(r"(?<![\w-])(?:" + pat + r")(?![\w-])", line, re.I):
                word = m.group(0)
                # technical-sense exemptions
                if re.match(r"orchestrat", word, re.I) and re.search(r"container|kubernetes|workflow|k8s", line, re.I):
                    continue
                out.append({"level": level, "line": n, "match": word, "fix": fix, "context": line.strip()[:110]})


def bullets_of(text: str) -> list[tuple[int, str, str]]:
    """(line, section, bullet text) for experience/project bullets."""
    out, sec = [], ""
    for n, line in lines_with_numbers(text):
        if line.startswith("## "):
            sec = line[3:].strip().lower()
        m = re.match(r"^\s*[-*]\s+(.*)", line)
        if m and "skill" not in sec and "certif" not in sec and not STACK.match(m.group(1)):
            out.append((n, sec, m.group(1).strip()))
    return out


def roles_of(text: str) -> list[tuple[int, str, int]]:
    """(line, role header, bullet count without Stack lines) for each ### entry under Experience."""
    roles, sec = [], ""
    for n, line in lines_with_numbers(text):
        if line.startswith("## "):
            sec = line[3:].strip().lower()
            continue
        if "experience" not in sec:
            continue
        if line.startswith("### "):
            roles.append([n, line[4:].split("|")[0].strip(), 0])
            continue
        m = re.match(r"^\s*[-*]\s+(.*)", line)
        if m and roles and not STACK.match(m.group(1)):
            roles[-1][2] += 1
    return [tuple(r) for r in roles]


def resume_words(text: str) -> int:
    body = [l for l in text.splitlines() if l.strip() and not l.startswith("<!--")]
    return len(re.sub(r"[#|*`]", " ", "\n".join(body)).split())


def shape_resume(text: str, out: list):
    bl = bullets_of(text)
    for n, _, b in bl:
        if PRONOUN.search(b):
            out.append({"level": "HARD", "line": n, "match": PRONOUN.search(b).group(0),
                        "fix": "no pronouns in bullets; start with the verb or the result", "context": b[:110]})
        if CONTEXT_OPENER.match(b):
            out.append({"level": "SHAPE", "line": n, "match": "context-clause opener",
                        "fix": "front-load: put the result or metric in the first 5-8 words", "context": b[:110]})
    team = sum(len(TEAM_WORDS.findall(b)) for _, _, b in bl)
    if team >= 3:
        out.append({"level": "SHAPE", "line": 0, "match": f"team/assist words used {team} times",
                    "fix": "keep where accurate; otherwise say what you owned", "context": ""})
    if len(bl) >= 6:
        lens = [len(b.split()) for _, _, b in bl]
        sd = statistics.pstdev(lens)
        mean = statistics.mean(lens)
        if sd < 3.5:
            out.append({"level": "SHAPE", "line": bl[0][0], "match": f"bullet length stdev {sd:.1f} (mean {mean:.0f})",
                        "fix": "bullets are suspiciously uniform; let simple items be short and big ones longer",
                        "context": ""})
        for n, _, b in bl:
            w = len(b.split())
            if w > 32:
                out.append({"level": "SHAPE", "line": n, "match": f"{w}-word bullet",
                            "fix": "split or cut; hiring managers skim", "context": b[:110]})
        firsts = Counter(b.split()[0].lower().strip(",.") for _, _, b in bl if b.split())
        for verb, c in firsts.items():
            if c >= 3:
                out.append({"level": "SHAPE", "line": 0, "match": f"{c} bullets start with '{verb}'",
                            "fix": "vary openers; some bullets can lead with the result", "context": ""})
        with_num = sum(1 for _, _, b in bl if re.search(r"\d", b))
        pct = 100 * with_num / len(bl)
        if pct < 40:
            out.append({"level": "SHAPE", "line": 0, "match": f"only {pct:.0f}% of bullets have a number",
                        "fix": "ask the user for scale/baseline numbers (never invent them)", "context": ""})
        if pct == 100 and len(bl) >= 8:
            out.append({"level": "SHAPE", "line": 0, "match": "every bullet has a number",
                        "fix": "a metric in every line reads manufactured; keep the strongest", "context": ""})
        triads = sum(1 for _, _, b in bl if TRIAD.search(b))
        if triads >= max(3, len(bl) // 3):
            out.append({"level": "SHAPE", "line": 0, "match": f"{triads} bullets use an 'X, Y, and Z' list",
                        "fix": "rule-of-three habit; keep lists only where there really are three things",
                        "context": ""})
    for i, (n, role, count) in enumerate(roles_of(text)):
        cap = RECENT_MAX if i < 2 else OLDER_MAX
        if count > cap:
            out.append({"level": "SHAPE", "line": n, "match": f"{count} bullets in '{role}'",
                        "fix": f"budget is {cap} for {'one of the two most recent roles' if i < 2 else 'an older role'}; keep the strongest for this JD",
                        "context": ""})
    words = resume_words(text)
    if words > WORDS_MAX or words < WORDS_MIN:
        out.append({"level": "SHAPE", "line": 0, "match": f"~{words} words",
                    "fix": f"budget is {WORDS_MIN}-{WORDS_MAX}; cut the weakest and oldest bullets first" if words > WORDS_MAX
                    else f"budget is {WORDS_MIN}-{WORDS_MAX}; add the strongest missing results",
                    "context": ""})
    m = re.search(r"^## (?:Professional )?Summary\s*\n(.+?)(?=^## |\Z)", text, re.M | re.S)
    if m:
        s = " ".join(m.group(1).split())
        if re.search(r"\b(I|my|me)\b", s):
            out.append({"level": "SOFT", "line": 0, "match": "first person in summary",
                        "fix": "resume summaries drop 'I'", "context": s[:110]})
        if re.search(r"\b(seeking|looking for|looking to)\b", s, re.I):
            out.append({"level": "HARD", "line": 0, "match": "objective-style summary",
                        "fix": "say what you offer, not what you want", "context": s[:110]})


def shape_cover(text: str, out: list):
    body = [l for l in text.splitlines() if l.strip() and not l.startswith("#")]
    words = len(" ".join(body[1:]).split())  # skip contact line
    if words > 320:
        out.append({"level": "SHAPE", "line": 0, "match": f"{words} words",
                    "fix": "target 180-300 words", "context": ""})
    paras = [p for p in re.split(r"\n\s*\n", text) if p.strip() and not p.strip().startswith("#")]
    sents = re.findall(r"[^.!?]+[.!?]", " ".join(paras))
    i_starts = sum(1 for s in sents if re.match(r"\s*I\b", s))
    if sents and i_starts / len(sents) > 0.5:
        out.append({"level": "SHAPE", "line": 0, "match": f"{i_starts}/{len(sents)} sentences start with 'I'",
                    "fix": "lead some sentences with the work or their problem", "context": ""})
    if sents:
        lens = [len(s.split()) for s in sents]
        if len(lens) >= 6 and statistics.pstdev(lens) < 4:
            out.append({"level": "SHAPE", "line": 0, "match": "sentence lengths uniform",
                        "fix": "mix short and long sentences", "context": ""})
    if paras and len(paras[-1].split()) < 6 and paras[-1].strip().endswith("."):
        pass
    if "!" in " ".join(paras):
        out.append({"level": "SOFT", "line": 0, "match": "exclamation mark", "fix": "cut", "context": ""})


def scan_punct(text: str, out: list):
    for n, line in lines_with_numbers(text):
        for m in DASHES.finditer(line):
            out.append({"level": "HARD", "line": n, "match": "dash", "fix": "use a comma, period, colon, or parentheses",
                        "context": line.strip()[:110]})
        if CURLY.search(line):
            out.append({"level": "SOFT", "line": n, "match": "curly quote", "fix": "use straight quotes",
                        "context": line.strip()[:110]})
        for m in RIDERS.finditer(line):
            out.append({"level": "SHAPE", "line": n, "match": m.group(0).strip(", "),
                        "fix": "-ing rider tacked onto a fact; make it its own clause with a real result or cut",
                        "context": line.strip()[:110]})


def profile_rules(src: Path) -> set[str]:
    """Read `writing_rules` from the nearest profile/career-profile.md above the source file."""
    for d in [src.resolve().parent, *src.resolve().parents]:
        prof = d / "profile" / "career-profile.md"
        if prof.exists():
            fm = prof.read_text(encoding="utf-8").split("---")
            if len(fm) < 3:
                return set()
            m = re.search(r"^writing_rules:\s*\n((?:\s+-\s*.+\n?)+)", fm[1], re.M)
            if not m:
                return set()
            return {re.sub(r"#.*", "", x).strip(" -\t") for x in m.group(1).splitlines() if x.strip()}
    return set()


YEARS = re.compile(r"\b\d+\+?\s*(?:years?|yrs)\b|\b(?:last|past|over|nearly|almost) (?:a )?(?:few|several|many|couple of)? ?(?:years|decades?)\b"
                   r"|\b(?:a|over a|nearly a|two) decades?\b", re.I)


def scan_rules(text: str, rules: set[str], out: list):
    if "no-years-of-experience" in rules:
        for n, line in lines_with_numbers(text):
            for m in YEARS.finditer(line):
                out.append({"level": "HARD", "line": n, "match": m.group(0),
                            "fix": "profile rule no-years-of-experience: drop the time span; let roles and dates show it",
                            "context": line.strip()[:110]})


def find_unslop_scanner(path: Path) -> Path | None:
    """Find one optional scanner across shared and agent-specific skill folders."""
    roots = [Path(__file__).resolve().parents[2]]
    project_dirs = (".agents", ".bob", ".claude", ".github", ".gemini", ".opencode")
    for parent in path.resolve().parents:
        roots.extend(parent / agent / "skills" for agent in project_dirs)
    roots.append(Path.home() / ".agents/skills")
    codex_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
    roots.append(codex_home / "skills")
    roots.extend(Path.home() / agent / "skills"
                 for agent in (".bob", ".claude", ".copilot", ".gemini", ".config/opencode"))
    for root in roots:
        scanner = root / "unslop/scripts/banned_phrase_scan.py"
        if scanner.is_file():
            return scanner
    return None


def unslop_hits(path: Path) -> list:
    scanner = find_unslop_scanner(path)
    if scanner is None:
        return []
    try:
        r = subprocess.run([sys.executable, "-I", str(scanner), str(path)], capture_output=True, text=True, timeout=60)
        data = json.loads(r.stdout or "{}")
    except Exception:
        return []
    return [{"level": "HARD" if v.get("severity") == "hard" else "SOFT", "line": v.get("line_number", 0),
             "match": v.get("phrase"), "fix": f"unslop[{v.get('category')}]: {v.get('suggestion') or 'rewrite'}",
             "context": (v.get("context") or "")[:110]} for v in data.get("violations", [])]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path)
    ap.add_argument("--type", choices=["resume", "cover"], default="resume")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    text = scrub(a.source.read_text(encoding="utf-8"))
    out: list = []
    scan_phrases(text, HARD, "HARD", out)
    scan_phrases(text, SOFT, "SOFT", out)
    scan_punct(text, out)
    scan_rules(text, profile_rules(a.source), out)
    (shape_cover if a.type == "cover" else shape_resume)(text, out)

    seen = {(h["line"], h["match"].lower()) for h in out}
    for h in unslop_hits(a.source):
        if (h["line"], str(h["match"]).lower()) not in seen:
            out.append(h)

    order = {"HARD": 0, "SHAPE": 1, "SOFT": 2}
    out.sort(key=lambda h: (order[h["level"]], h["line"]))
    if a.json:
        print(json.dumps(out, indent=2))
    else:
        for h in out:
            loc = f"L{h['line']}" if h["line"] else "   "
            print(f"[{h['level']:<5}] {loc:<5} {h['match']!s:<34} -> {h['fix']}")
            if h["context"]:
                print(f"               {h['context']}")
        c = Counter(h["level"] for h in out)
        print(f"\n{c.get('HARD', 0)} HARD, {c.get('SHAPE', 0)} SHAPE, {c.get('SOFT', 0)} SOFT")
    sys.exit(1 if any(h["level"] == "HARD" for h in out) else 0)


if __name__ == "__main__":
    main()
