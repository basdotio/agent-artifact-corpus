"""ko-ste 점검 도구.

1) 후보 표시: 모드 기준을 넘은 문장과 목록 A/B 후보를 보여 준다.
       uv run --no-project --with kiwipiepy skills/ko-ste/scripts/check.py draft.md --mode strict
       uv run --no-project --with kiwipiepy skills/ko-ste/scripts/check.py draft.md --mode 80

2) 원문 대조: 다듬은 글이 원문의 보존 요소를 잃거나 더했는지 본다.
       uv run --no-project --with kiwipiepy skills/ko-ste/scripts/check.py --compare original.md edited.md

후보는 '고칠 수도 있는 곳'이다. 고칠지는 references/01-rules.md의 문맥 기준으로 정한다.
대조 결과의 차이도 오류라고 단정하지 않는다. 바뀐 이유를 규칙으로 댈 수 있는지 확인한다.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import kostelib as K  # noqa: E402

MODES = {
    "strict": {"imp_len": 14, "decl_len": 17, "decl_hard": 17, "clauses": 2, "imp_clauses": 1, "ui": 1, "noun_run": 3, "lists": {"A", "B"}},
    "80": {"imp_len": 17, "decl_len": 17, "decl_hard": 25, "clauses": 3, "imp_clauses": 2, "ui": 2, "noun_run": 4, "lists": {"A"}},
}

# --- 보존 요소 추출 (MP-2 ~ MP-5)
EXTRACT = {
    "fenced_code": re.compile(r"(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$"),
    "code": re.compile(r"`[^`\n]+`"),
    "url": re.compile(r"https?://[^\s)>\]]+"),
    "path": re.compile(r"(?<![\w/\\])(?:[A-Za-z]:[\\/]|(?:\.{0,2}/|~/)?)(?:[\w.-]+[\\/])+[\w.-]+"),
    "number": re.compile(r"\d[\d,]*(?:\.\d+)?\s?(?:%|ms|s|초|분|시간|일|주|개월|년|원|억|만|천|개|건|명|회|번|MB|GB|KB|TB|어절|단계|자리|장|곳)?"),
}
MARKERS = {
    "scope": r"(만(?=[ 을를이가은는의에도]|$)|까지|부터|일부|등(?=[ 을를이가은는의에도,.]|$)|이상|이하|초과|미만|제외|단,|모든|각 |약 |여 곳|경우|-면|으면|면\b)",
    "hedge": r"(수 있|수도 있|것 같|보입니다|보인다|보여요|가능성|아마|추정|듯|지도 모|예정|계획)",
    "must": r"(해야|하여야|어야|아야|반드시|꼭|필수|할 것(?=[.\s]|$)|하십시오|하세요|마십시오|마세요|금지|안 됩니다|안 된다|안 돼요)",
    "permit": r"(해도 된|해도 됩|어도 된|아도 된|어도 됩|아도 됩|도 괜찮)",
    "negation": r"(않|못|없|아니|안 |말고|마세요|마십시오|금지)",
}


def sentences_of(md: str):
    st = K.parse_markdown(md)
    for u in st.units:
        for s in K.split_sentences(u.text):
            yield u, s


def check(md: str, mode: str) -> list[str]:
    cfg = MODES[mode]
    out = []
    for u, s in sentences_of(md):
        r = K.analyze_sentence(s)
        if r is None:
            continue
        flags = []
        is_imp = r["mood"] == "imp"
        if is_imp and r["eojeol"] > cfg["imp_len"]:
            flags.append(f"SE-2 지시문 {r['eojeol']}어절>{cfg['imp_len']} (동작 수를 확인)")
        if is_imp and r["clauses"] > cfg["imp_clauses"]:
            flags.append(f"ST-3 지시문 연결 절 {r['clauses']} (조건절이면 그대로)")
        if not is_imp:
            other = r["clauses"] > cfg["clauses"] or r["ui"] > cfg["ui"] or r["noun_run"] > cfg["noun_run"] or r["etm"] >= 3
            if r["eojeol"] > cfg["decl_hard"]:
                flags.append(f"SE-2 설명문 {r['eojeol']}어절>{cfg['decl_hard']}")
            elif r["eojeol"] > cfg["decl_len"] and other:
                flags.append(f"SE-2 설명문 {r['eojeol']}어절>{cfg['decl_len']} + 다른 신호")
            if r["clauses"] > cfg["clauses"]:
                flags.append(f"SE-1 연결 절 {r['clauses']}>{cfg['clauses']}")
        if r["ui"] > cfg["ui"]:
            flags.append(f"MO-2 '의' {r['ui']}>{cfg['ui']}")
        if r["noun_run"] > cfg["noun_run"]:
            flags.append(f"MO-3 명사 연속 {r['noun_run']}>{cfg['noun_run']}: {r['noun_span']} (고정 용어면 하나로 센다)")
        if r["etm"] >= 3:
            flags.append(f"MO-1 관형형 어미 {r['etm']}개 (겹친 관형절인지 확인)")
        for key, n in r["hits"].items():
            meta = K.PATTERNS.get(key, {"list": "B" if key == "B.kyungwoo" else "S", "rule": "LX-4" if key == "B.kyungwoo" else ""})
            if meta["list"] in cfg["lists"]:
                flags.append(f"{meta['rule']} 목록{meta['list']} {key}")
        if re.search(K.PATTERNS_EXTRA["AM-1"], s):
            flags.append("AM-1 부정 범위 후보")
        if is_imp and re.search(K.PATTERNS_EXTRA["AM-2"], s):
            flags.append("AM-2 지시문의 '수 있다'")
        if flags:
            out.append(f"- {s}\n    " + "\n    ".join(flags))
    return out


def extract(md: str) -> dict[str, Counter]:
    res = {}
    for k, rx in EXTRACT.items():
        res[k] = Counter(m.group(0).strip() for m in rx.finditer(md))
    plain = K.INLINE_CODE.sub(" ", md)
    for k, pat in MARKERS.items():
        res[k] = Counter(m.group(0) for m in re.finditer(pat, plain))
    efs = Counter()
    for _, s in sentences_of(md):
        toks = K.tokenize(s)
        core = [t for t in toks if t.tag not in K.SENT_END_PUNCT]
        if core and core[-1].tag == "EF":
            f = core[-1].form
            style = "합쇼체" if re.search(r"(ㅂ니다|습니다|ㅂ니까|습니까|십시오|시오)$", f) else "해요체" if f.endswith(("요", "죠")) else "해라체" if f in {"다", "는다", "ㄴ다", "자", "라", "어라", "아라", "냐", "니"} else "기타"
            efs[style] += 1
    res["style"] = efs
    return res


def compare(a: str, b: str) -> list[str]:
    ea, eb = extract(a), extract(b)
    lines = []
    for k in ("fenced_code", "code", "url", "path", "number"):
        lost = ea[k] - eb[k]
        added = eb[k] - ea[k]
        if lost:
            lines.append(f"MP-5 {k} 사라짐: {dict(lost)}")
        if added:
            lines.append(f"MP-1 {k} 새로 생김: {dict(added)}")
    for k, rule in (("scope", "MP-2"), ("hedge", "MP-3"), ("must", "MP-4"), ("permit", "MP-4"), ("negation", "AM-1")):
        na, nb = sum(ea[k].values()), sum(eb[k].values())
        if ea[k] != eb[k]:
            lines.append(f"{rule} {k} 표지 {na}→{nb}: 원문 {dict(ea[k])} / 결과 {dict(eb[k])}")
    sa, sb = ea["style"], eb["style"]
    if sa and sb and sa.most_common(1)[0][0] != sb.most_common(1)[0][0]:
        lines.append(f"MP-6 주된 문체 바뀜: {dict(sa)} → {dict(sb)}")
    return lines or ["보존 요소 차이 없음 (의미 보존을 증명하지는 않는다. 문맥으로 다시 확인한다.)"]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--mode", choices=list(MODES), default="80")
    ap.add_argument("--compare", action="store_true", help="files: 원문 결과")
    args = ap.parse_args()
    if args.compare:
        a, b = (Path(f).read_text(encoding="utf-8") for f in args.files[:2])
        print("\n".join(compare(a, b)))
        return
    for f in args.files:
        lines = check(Path(f).read_text(encoding="utf-8"), args.mode)
        print(f"# {f} ({args.mode}) 후보 {len(lines)}문장")
        print("\n".join(lines))


if __name__ == "__main__":
    main()
