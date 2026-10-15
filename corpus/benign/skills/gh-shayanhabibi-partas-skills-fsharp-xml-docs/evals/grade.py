"""Programmatic grading for the fsharp-xml-docs evals.

python grade.py <iteration-dir>
Writes grading.json into every <eval>/<config>/run-<n>/ directory.
"""
import json
import xml.etree.ElementTree as ET
import re
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
AUDIT = SKILL / "scripts" / "audit.fsx"
CONVENTION_KINDS = {"bare-doc", "missing-summary", "empty-param", "empty-tag", "code-lang", "non-standard-tag",
                    "long-line", "include-unresolved"}


def audit(path: Path) -> list[tuple[int, str, str]]:
    out = subprocess.run(["dotnet", "fsi", str(AUDIT), "--compiler", str(path)],
                         capture_output=True, text=True, encoding="utf-8").stdout
    found = []
    for line in out.splitlines():
        m = re.match(r".*\((\d+)\): ([\w-]+): (.*)", line)
        if m:
            found.append((int(m[1]), m[2], m[3]))
    return found


def code_lines(text: str) -> list[str]:
    return [l.rstrip() for l in text.splitlines() if not l.strip().startswith("///") and l.strip()]


def doc_blocks(text: str) -> list[tuple[int, str]]:
    blocks, cur, start = [], [], 0
    for i, l in enumerate(text.splitlines(), 1):
        s = l.strip()
        if s.startswith("///"):
            if not cur:
                start = i
            cur.append(s[3:].strip())
        elif cur:
            blocks.append((start, "\n".join(cur)))
            cur = []
    return blocks


def prose_lines(block: str, tag: str) -> int:
    worst = 0
    for m in re.finditer(rf"<{tag}\b[^>]*>(.*?)</{tag}>", block, re.S):
        inner = re.sub(r"<code\b.*?</code>", "", m[1], flags=re.S)
        lines = [re.sub(r"<[^>]+>", "", l).strip() for l in inner.splitlines()]
        worst = max(worst, sum(1 for l in lines if l))
    return worst


def check(text: str, passed: bool, evidence: str) -> dict:
    return {"text": text, "passed": bool(passed), "evidence": evidence}


def comment_only(inp: Path, out: Path) -> dict:
    if not out.exists():
        return check("Only /// lines differ from the input (comment-only change)", False, f"{out.name} missing")
    a, b = code_lines(inp.read_text(encoding="utf-8-sig")), code_lines(out.read_text(encoding="utf-8-sig"))
    diff = [x for x in b if x not in a] + [x for x in a if x not in b]
    return check("Only /// lines differ from the input (comment-only change)", not diff,
                 "identical code lines" if not diff else f"{len(diff)} code line(s) differ, e.g. {diff[0][:80]!r}")


def audit_checks(out: Path) -> list[dict]:
    if not out.exists():
        return [check("Audit script reports zero convention findings", False, "no output"),
                check("Zero FS3390 findings (malformed XML, unknown or partial <param>)", False, "no output")]
    f = audit(out)
    conv = [x for x in f if x[1] in CONVENTION_KINDS]
    fs = [x for x in f if x[1] == "FS3390"]
    fmt = lambda xs: "; ".join(f"L{l} {k}: {m}" for l, k, m in xs[:4]) or "none"
    return [check("Audit script reports zero convention findings", not conv, fmt(conv)),
            check("Zero FS3390 findings (malformed XML, unknown or partial <param>)", not fs, fmt(fs))]


def budget_check(out: Path) -> dict:
    name = "No <summary> exceeds 2 prose lines and no <remarks> exceeds 3"
    if not out.exists():
        return check(name, False, "no output")
    sizes = [(l, prose_lines(b, "summary"), prose_lines(b, "remarks"))
             for l, b in doc_blocks(out.read_text(encoding="utf-8-sig"))]
    bad = [(l, s, r) for l, s, r in sizes if s > 2 or r > 3]
    return check(name, not bad, "all within budget" if not bad else
                 "; ".join(f"L{l}: summary={s} remarks={r}" for l, s, r in bad[:4]))


def grade_eval1(run: Path) -> list[dict]:
    inp, out = run / "inputs" / "GitHub.fs", run / "outputs" / "GitHub.fs"
    res = [comment_only(inp, out)]
    if out.exists():
        lines = out.read_text(encoding="utf-8-sig").splitlines()
        targets = [i for i, l in enumerate(lines)
                   if re.match(r"\s*(type UrlFactory|let urlRoot|member this\.|new \(|let (fromString|fromSha|fromGitNetCommit|fromCommit|fromTag|fromGitNetTag|from\w+))", l)]
        undocumented = []
        for i in targets:
            j = i - 1
            while j >= 0 and lines[j].strip().startswith("[<"):
                j -= 1
            if j < 0 or not lines[j].strip().startswith("///"):
                undocumented.append(f"L{i + 1} {lines[i].strip()[:50]}")
        res.append(check("Every public declaration (type, urlRoot, each Create overload, module functions) has an XML doc",
                         not undocumented, f"{len(targets)} declarations; undocumented: {undocumented[:5] or 'none'}"))
        blocks = doc_blocks("\n".join(lines))
        stray = [l for l, b in blocks if "<paramref" in b and "<param " not in b]
        res.append(check("No <paramref> in a doc that has no <param> tags", not stray,
                         f"blocks: {stray or 'none'}"))
    else:
        res += [check("Every public declaration has an XML doc", False, "no output"),
                check("No <paramref> in a doc that has no <param> tags", False, "no output")]
    return res + audit_checks(out) + [budget_check(out)]


INCLUDE_COMPLAINT = re.compile(r"not supported|unsupported|not expand|doesn.t expand|does not expand|unexpanded|ignored|"
                               r"won.t (show|render|appear)|will not (show|render|appear)|copied verbatim|silently|broken|never reach", re.I)


def grade_eval2(run: Path) -> list[dict]:
    report = run / "outputs" / "audit.md"
    res = []
    unchanged = all((run / "inputs" / "partas-build" / p).read_bytes() == (SKILL / "evals" / "files" / "partas-build" / p).read_bytes()
                    for p in ["Builders/Command.fs", "xmldoc/command.xml"])
    res.append(check("audit.md exists and the source files are unchanged", report.exists() and unchanged,
                     f"audit.md={'yes' if report.exists() else 'no'}, sources unchanged={unchanged}"))
    text = report.read_text(encoding="utf-8") if report.exists() else ""
    bare = re.search(r"bare|plain `?///|without (an? )?(explicit )?<?summary|no <?summary|missing <?summary", text, re.I)
    res.append(check("Reports the bare /// docs that lack <summary>", bare is not None,
                     f"matched {bare[0]!r}" if bare else "not mentioned" if text else "no report"))
    res.append(check("Flags the non-standard <em> tag", "<em>" in text or "`em`" in text, "found" if "<em>" in text else "not mentioned"))
    complaints = [s.strip()[:160] for s in re.split(r"(?<=[.!?])\s+|\n", text)
                  if "include" in s.lower() and INCLUDE_COMPLAINT.search(s) and not re.search(r"\.NET 11|net11|expected", s, re.I)]
    res.append(check("Does not report <include> as broken, unsupported or unexpanded", not complaints,
                     f"complaints: {complaints[:3] or 'none'}"))
    refs = re.findall(r"(?:\bline\s|\bL|:|\(|\|\s*)\d{2,3}\b", text)
    res.append(check("Cites line numbers for findings (at least 5)", len(refs) >= 5, f"{len(refs)} line references"))
    return res


def grade_eval3(run: Path) -> list[dict]:
    inp, out = run / "inputs" / "SepochSemver.fs", run / "outputs" / "SepochSemver.fs"
    res = [comment_only(inp, out)]
    text = out.read_text(encoding="utf-8-sig") if out.exists() else ""
    empty = re.findall(r'<param name="(\w+)">\s*</param>', text)
    res.append(check("No empty <param> tags remain", out.exists() and not empty, f"empty: {empty or 'none'}"))
    crefs = re.findall(r'cref="([^"]+)"', text)
    short = [c for c in crefs if not re.match(r"[TMPFEN]:", c)]
    res.append(check("Every cref uses the full X: prefix form", out.exists() and not short,
                     f"{len(crefs)} crefs; short: {short[:4] or 'none'}"))
    res.append(check("Copied Semver exception text about a 'style' parameter is removed",
                     out.exists() and "style is not a valid" not in text and "version is null" not in text,
                     "removed" if out.exists() and "style is not a valid" not in text else "still present"))
    restated = [s for s in ["Tries to parse sepoch semver.", "Parse sepoch semver or error."] if s in text]
    res.append(check("Summaries that restate the function name are rewritten", out.exists() and not restated,
                     f"still present: {restated or 'none'}"))
    res.append(check("summary.md exists", (run / "outputs" / "summary.md").exists(), ""))
    return res + audit_checks(out)


DELAY_REMARK = "The delay is the wait before the first retry only."
ATTEMPTS_REMARK = "The last setting wins"


def grade_eval4(run: Path) -> list[dict]:
    inp = run / "inputs" / "retry" / "src" / "Retry.fs"
    out = next(iter(sorted((run / "outputs").glob("**/src/Retry.fs"))), run / "outputs" / "src" / "Retry.fs")
    res = [comment_only(inp, out)]
    text = out.read_text(encoding="utf-8-sig") if out.exists() else ""
    inline = [r for r in (DELAY_REMARK, ATTEMPTS_REMARK) if r in text]
    res.append(check("Duplicated remarks no longer appear inline in Retry.fs", bool(text) and not inline,
                     f"still inline: {inline}" if inline else ("removed" if text else "no output")))
    lines = text.splitlines()
    members = [i for i, l in enumerate(lines) if re.match(r"\s*member (this|_)\.(Delay|DelaySeconds|Attempts)\(", l)]
    missing = []
    for i in members:
        j = i - 1
        block = []
        while j >= 0 and lines[j].strip().startswith("///"):
            block.append(lines[j]); j -= 1
        if not any("<summary>" in b for b in block):
            missing.append(f"L{i + 1}")
    res.append(check("Every overload keeps an inline <summary>", bool(members) and not missing,
                     f"{len(members)} overloads; missing: {missing or 'none'}"))
    xmls = sorted((run / "outputs").glob("**/xmldoc/*.xml"))
    wellformed = []
    for x in xmls:
        try:
            ET.parse(x); wellformed.append(x)
        except ET.ParseError as e:
            pass
    res.append(check("An xmldoc/*.xml file exists beside src/ and is well-formed", bool(wellformed),
                     ", ".join(str(x.relative_to(run / "outputs")) for x in xmls) or "none found"))
    found = audit(out) if out.exists() else []
    unresolved = [f"L{l}: {m}" for l, k, m in found if k == "include-unresolved"]
    n_inc = text.count("<include ")
    res.append(check("Every <include> resolves (no include-unresolved finding)", n_inc > 0 and not unresolved,
                     f"{n_inc} include(s); unresolved: {unresolved[:3] or 'none'}"))
    any_xml = []
    for x in sorted((run / "outputs").glob("**/*.xml")):
        try:
            ET.parse(x); any_xml.append(x)
        except ET.ParseError:
            pass
    xml_text = "".join(x.read_text(encoding="utf-8-sig") for x in any_xml)
    flat = re.sub(r"\s+", " ", xml_text)
    counts = {r: flat.count(r) for r in (DELAY_REMARK, ATTEMPTS_REMARK)}
    res.append(check("Each shared remark is written once in the XML file", all(c == 1 for c in counts.values()),
                     str(counts)))
    return res + audit_checks(out)


GRADERS = {1: grade_eval1, 2: grade_eval2, 3: grade_eval3, 4: grade_eval4}

if __name__ == "__main__":
    it = Path(sys.argv[1])
    for eval_dir in sorted(it.glob("eval-*")):
        eid = int(eval_dir.name.split("-")[1])
        for run in sorted(eval_dir.glob("*/run-*")):
            exp = GRADERS[eid](run)
            n = sum(e["passed"] for e in exp)
            json.dump({"expectations": exp,
                       "summary": {"passed": n, "failed": len(exp) - n, "total": len(exp),
                                   "pass_rate": round(n / len(exp), 2)}},
                      open(run / "grading.json", "w", encoding="utf-8"), indent=2)
            print(f"{eval_dir.name}/{run.parent.name}/{run.name}: {n}/{len(exp)}")
