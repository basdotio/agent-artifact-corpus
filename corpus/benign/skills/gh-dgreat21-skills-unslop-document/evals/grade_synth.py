"""Проверка прогонов по эталону evals_synth.json.

python3 grade_synth.py <iteration_dir>
Проверяет все eval-*/<config>/run-*/ в папке, пишет grading.json в каждый run и details.json в iteration_dir.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
REF = {e["id"]: e for e in json.loads((HERE / "evals_synth.json").read_text(encoding="utf-8"))["evals"]}

# Канцелярит, который правка не должна приносить в текст сама.
KANC = ["в рамках", "осуществля", "производится", "посредством", "обеспечивает возможность", "обеспечение", "данного", "данный"]


def norm(s):
    s = s.replace(" ", " ").replace("ё", "е").replace("Ё", "Е")
    s = re.sub(r"[*_`]", "", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def raw(s):
    s = s.replace(" ", " ")
    s = re.sub(r"[*_`]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def sentences(s):
    return len([x for x in re.split(r"[.;!?](?:\s|$)", s.strip()) if x.strip()])


def inv_present(t, text):
    if t.startswith("rc:"):
        return re.search(t[3:], raw(text)) is not None
    if t.startswith("re:"):
        return re.search(t[3:], norm(text)) is not None
    return norm(t) in norm(text)


def inv_label(t):
    return t.replace("rc:", "").replace("re:", "").replace("\\w*", "…").replace("\\w+", "…").replace("\\", "").replace("[её]", "е")


def check(e, run):
    out = run / "outputs"
    orig = (HERE / "synth" / e["file"]).read_text(encoding="utf-8")
    try:
        data = json.loads((out / "edits.json").read_text(encoding="utf-8"))
        edits = data.get("edits", [])
    except Exception as ex:  # noqa: BLE001
        return [{"text": "edits.json читается", "passed": False, "evidence": str(ex), "kind": "harness"}], {}
    result = (out / "result.md").read_text(encoding="utf-8") if (out / "result.md").exists() else ""
    optional = data.get("optional", [])
    exp = []
    missing = [x.get("before", "")[:60] for x in edits if norm(x.get("before", "")) not in norm(orig)]

    def hits(anchor):
        a = norm(anchor)
        return [x for x in edits if a in norm(x.get("before", ""))]

    base = norm(orig)
    spans = []
    for x in edits:
        b = norm(x.get("before", ""))
        i = base.find(b) if b else -1
        if i >= 0:
            spans.append((i, i + len(b), x))
    applied = base
    for i, j, x in sorted(spans, key=lambda t: -t[0]):
        applied = applied[:i] + norm(x.get("after", "")) + applied[j:]

    def sentence_span(anchor):
        a = norm(anchor)
        i = base.find(a)
        st = max(base.rfind(". ", 0, i), base.rfind("\n", 0, i))
        en = base.find(". ", i + len(a))
        return (st + 1 if st >= 0 else 0, en if en >= 0 else len(base))

    for f in e["must_fix"]:
        s0, s1 = sentence_span(f["anchor"])
        near = [x for i, j, x in sorted(spans, key=lambda t: t[0]) if i < s1 and j > s0]
        joined = " ".join(norm(x.get("after", "")) for x in near)
        ok, ev = False, "место не найдено среди основных правок"
        if not near:
            if any(norm(f["anchor"]) in norm(x.get("before", "")) for x in optional):
                ev = "предложено только как необязательная правка"
        elif norm(f["anchor"]) in applied and not any(
                norm(f["anchor"]) in norm(x.get("before", "")) and norm(x.get("after", "")) != norm(x.get("before", ""))
                for x in near):
            ev = "фраза осталась без изменений"
        else:
            ev = "стало: «" + " … ".join(x.get("after", "") for x in near) + "»"
            bad = [b for b in f.get("bad", []) if norm(b) in joined]
            if bad:
                ev += " — осталось: " + ", ".join(bad)
            elif "order" in f and not (0 <= joined.find(norm(f["order"][0])) < joined.find(norm(f["order"][1]))):
                ev += " — порядок слов не исправлен"
            elif "min_sentences" in f and sum(sentences(x.get("after", "")) for x in near) < f["min_sentences"]:
                ev += " — не разбито на предложения"
            else:
                ok = True
        exp.append({"text": f"[{f['id']} · {f['cls']}] исправить «{f['anchor']}» (эталон: {f['ref']})", "passed": ok, "evidence": ev, "kind": "fix"})

    for k in e["must_keep"]:
        kept = norm(k["anchor"]) in applied
        broken = [x for i, j, x in spans if norm(k["anchor"]) in base[max(0, i - 200):j + 200] and norm(k["anchor"]) not in norm(x.get("after", ""))]
        exp.append({
            "text": f"[{k['id']} · {k['cls']}] не трогать «{k['anchor']}» ({k['why']})",
            "passed": kept,
            "evidence": "не тронуто" if kept else ("изменено: «" + (broken[0].get("after", "") if broken else "") + "»"),
            "kind": "keep",
        })

    lost = []
    for h in edits:
        for t in e["invariants"]:
            if inv_present(t, h.get("before", "")) and not inv_present(t, h.get("after", "")):
                lost.append(inv_label(t))
    exp.append({"text": "Цифры, сроки, номера, названия и термины перенесены без изменений: " + ", ".join(inv_label(t) for t in e["invariants"]),
                "passed": not lost, "evidence": ("потеряно или изменено: " + ", ".join(sorted(set(lost)))) if lost else "все на месте", "kind": "invariant"})

    added = []
    for h in edits:
        b, a = norm(h.get("before", "")), norm(h.get("after", ""))
        for w in KANC:
            if a.count(w) > b.count(w):
                added.append(f"«{w}» в «{h.get('after', '')}»")
    exp.append({"text": "В «стало» не добавлен новый канцелярит (в рамках, осуществляется, посредством, обеспечение, данный…)",
                "passed": not added, "evidence": "; ".join(added) if added else "не добавлено", "kind": "no_new"})

    flag_words = ["?", "уточн", "неясн", "непонятн", "не определ", "не расшифр", "что такое", "что за ", "что имеется в виду", "не объясн", "без определения", "не раскрыт"]
    lines = [norm(x) for x in result.splitlines() if x.strip()]
    for g in e.get("ghost", []):
        t = norm(g["term"])
        flagged = [x for x in lines if t in x and any(w in x for w in flag_words)]
        invented = [x for x in edits if t in norm(x.get("before", "")) and t not in norm(x.get("after", ""))
                    and "[" not in x.get("after", "") and "уточн" not in norm(x.get("after", ""))]
        ok = bool(flagged) and not invented
        ev = ("спрошено: «" + flagged[0][:200] + "»") if flagged else "не отмечено как непонятное"
        if invented:
            ev += "; в правке ярлык заменён без вопроса автору: «" + invented[0].get("after", "")[:160] + "»"
        exp.append({"text": f"[{g['id']} · термин-призрак] спросить автора, что значит «{g['label']}» ({g['why']}), и не выдумывать расшифровку",
                    "passed": ok, "evidence": ev, "kind": "ghost"})
    for g in e.get("not_ghost", []):
        t = norm(g["term"])
        flagged = [x for x in lines if t in x and any(w in x for w in flag_words[1:])]
        exp.append({"text": f"[{g['id']} · определённый термин] не отмечать «{g['term']}» как непонятный ({g['why']})",
                    "passed": not flagged, "evidence": ("отмечен: «" + flagged[0][:200] + "»") if flagged else "не отмечен", "kind": "not_ghost"})

    if "max_edits" in e:
        exp.append({"text": f"Не больше {e['max_edits']} правки на чистом тексте", "passed": len(edits) <= e["max_edits"],
                    "evidence": f"правок: {len(edits)}", "kind": "restraint"})

    for s in e.get("side", []):
        kw = norm(s["keyword"])
        in_before = sum(norm(h.get("before", "")).count(kw) for h in edits)
        silently = [h for h in edits if kw in norm(h.get("before", "")) and kw not in norm(h.get("after", ""))]
        mentioned = norm(result).count(kw) > in_before * 2
        ok = mentioned and not silently
        exp.append({"text": f"[{s['id']} · попутно] {s['note']}", "passed": ok,
                    "evidence": "вынесено в попутное" if ok else ("молча заменено в правке" if silently else "не упомянуто"), "kind": "side"})

    if "anchor_block" in e:
        ab = e["anchor_block"]
        rows = []
        for line in result.splitlines():
            if line.startswith("|") and not re.match(r"^\|\s*-", line):
                rows.append(line)
            elif rows and not line.startswith("|"):
                break
        body = rows[1:]
        ok = bool(body) and all(ab["root"] in norm(r) for r in body) and not any(norm(w) in norm(" ".join(body)) for w in ab["foreign"])
        exp.append({"text": f"Первая таблица — только места с корнем «{ab['root']}» из примера автора, без других калек",
                    "passed": ok, "evidence": f"строк в первой таблице: {len(body)}", "kind": "structure"})

    if missing:
        exp.append({"text": "Цитаты «было» дословно совпадают с исходником", "passed": False,
                    "evidence": "не найдено в тексте: " + "; ".join(missing), "kind": "harness"})
    soft = [k["id"] for k in e["must_keep"] for h in optional
            if norm(k["anchor"]) in norm(h.get("before", "")) and norm(k["anchor"]) not in norm(h.get("after", ""))]
    notes = {"optional_count": len(optional), "optional_touch_keep": sorted(set(soft)),
             "optional_fix": [f["id"] for f in e["must_fix"] for h in optional if norm(f["anchor"]) in norm(h.get("before", ""))],
             "edits": edits, "optional": optional}
    cur = next((out / "input").glob("*.md")).read_text(encoding="utf-8")
    exp.append({"text": "Документ не изменён (правки только показаны)", "passed": cur == orig,
                "evidence": "файл совпадает с исходным" if cur == orig else "файл изменён", "kind": "safety"})
    return exp, notes


def main():
    it = Path(sys.argv[1])
    details = []
    for ed in sorted(it.glob("eval-*"), key=lambda p: int(p.name.split("-")[1])):
        e = REF[int(ed.name.split("-")[1])]
        for cfg in ["with_skill", "without_skill"]:
            for run in sorted((ed / cfg).glob("run-*")):
                if not (run / "outputs" / "edits.json").exists():
                    continue
                exp, notes = check(e, run)
                n = sum(x["passed"] for x in exp)
                timing = json.loads((run / "timing.json").read_text()) if (run / "timing.json").exists() else {}
                (run / "grading.json").write_text(json.dumps({
                    "expectations": [{k: x[k] for k in ("text", "passed", "evidence")} for x in exp],
                    "summary": {"passed": n, "failed": len(exp) - n, "total": len(exp), "pass_rate": n / len(exp)},
                    "timing": timing,
                }, ensure_ascii=False, indent=2), encoding="utf-8")
                details.append({"eval": e["id"], "name": e["name"], "title": e["title"], "set": e.get("set", "base"),
                                "config": cfg, "run": run.name, "passed": n, "total": len(exp), "expectations": exp,
                                "timing": timing, "notes": notes,
                                "result_md": (run / "outputs" / "result.md").read_text(encoding="utf-8")})
                print(e["id"], cfg, run.name, f"{n}/{len(exp)}")
    (it / "details.json").write_text(json.dumps(details, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
