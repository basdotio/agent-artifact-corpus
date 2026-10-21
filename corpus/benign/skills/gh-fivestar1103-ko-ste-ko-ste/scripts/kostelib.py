"""ko-ste 공용 분석 모듈: 마크다운 정리, 문장 분리, 형태소 기반 지표, 표현 패턴.

측정(measure.py)과 점검(check.py)이 같은 정의를 쓰도록 여기에 모았다.
패턴은 '후보'를 찾을 뿐이다. 고칠지는 문맥으로 정한다(references/01-rules.md).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

# ---------------------------------------------------------------------------
# 1. 마크다운 정리

FENCE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE = re.compile(r"`[^`\n]+`")
LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
URL = re.compile(r"https?://\S+")
HTML_TAG = re.compile(r"</?[A-Za-z][^>]*>")
BOLD = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*|__(?=\S)(.+?)(?<=\S)__")
HANGUL = re.compile(r"[가-힣]")
LATIN = re.compile(r"[A-Za-z]")
CODE_TOKEN = "CODEX"  # 인라인 코드 자리표시자. Kiwi가 SL 한 덩어리로 읽는다.


@dataclass
class Unit:
    """문장 후보를 담는 산문 단위(문단 또는 목록 항목)."""

    text: str
    kind: str  # "para" | "item"
    raw: str


@dataclass
class DocStats:
    lines_total: int = 0  # 코드 블록 밖의 비어 있지 않은 줄
    lines_bold: int = 0
    bold_spans: int = 0
    lines_heading: int = 0
    lines_table: int = 0
    lines_list: int = 0
    emoji: int = 0
    units: list[Unit] = field(default_factory=list)


EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✅❌]")


def strip_blocks(md: str, exclude_blocks: list[str] | None = None) -> str:
    """front matter, import 줄, 지정한 JSX 블록과 ::: 블록을 지운다."""
    md = re.sub(r"\A---\n.*?\n---\n", "", md, flags=re.S)
    md = re.sub(r"^import .*$", "", md, flags=re.M)
    for name in exclude_blocks or []:
        if name == "details":
            md = re.sub(r"^:::\s*details.*?^:::\s*$", "", md, flags=re.S | re.M)
        else:
            md = re.sub(rf"<{name}[\s>].*?</{name}\s*>", "", md, flags=re.S)
    md = re.sub(r"^:::.*$", "", md, flags=re.M)
    return md


def parse_markdown(md: str, exclude_blocks: list[str] | None = None) -> DocStats:
    md = strip_blocks(md, exclude_blocks)
    st = DocStats()
    in_fence = False
    buf: list[str] = []

    def flush() -> None:
        if buf:
            raw = " ".join(s.strip() for s in buf)
            st.units.append(Unit(clean_inline(raw), "para", raw))
            buf.clear()

    for line in md.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            flush()
            continue
        if in_fence:
            continue
        s = line.strip()
        if not s:
            flush()
            continue
        st.lines_total += 1
        nb = len(BOLD.findall(s))
        st.bold_spans += nb
        st.lines_bold += 1 if nb else 0
        st.emoji += len(EMOJI.findall(s))
        if s.startswith("#"):
            st.lines_heading += 1
            flush()
            continue
        if s.startswith("|"):
            st.lines_table += 1
            flush()
            continue
        if s.startswith(">") or s.startswith("<") or s.startswith("!["):
            flush()  # 인용, HTML, 이미지는 제외
            continue
        m = re.match(r"^([-*+]|\d+[.)])\s+(.*)$", s)
        if m:
            flush()
            st.lines_list += 1
            st.units.append(Unit(clean_inline(m.group(2)), "item", m.group(2)))
            continue
        buf.append(s)
    flush()
    return st


def clean_inline(s: str) -> str:
    s = INLINE_CODE.sub(CODE_TOKEN, s)
    s = LINK.sub(r"\1", s)
    s = URL.sub(CODE_TOKEN, s)
    s = HTML_TAG.sub("", s)
    s = BOLD.sub(lambda m: m.group(1) or m.group(2), s)
    s = re.sub(r"(?<!\*)\*(?!\*)", "", s)
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------------------
# 2. 형태소 분석


@lru_cache(maxsize=1)
def kiwi():
    from kiwipiepy import Kiwi

    return Kiwi()


NOMINAL = {"NNG", "NNP", "NNB", "NR", "NP", "XSN", "XPN", "SN", "SL", "SH", "MM"}
HANGUL_NOUN = {"NNG", "NNP"}
# 부사처럼 쓰이는 시간·경우 명사. 명사 사슬과 '의' 사슬을 여기서 끊는다.
BREAK_NOUNS = {"동안", "경우", "때", "중", "후", "전", "시", "이후", "이전", "뒤", "다음", "사이", "이상", "이하", "미만", "초과", "등", "간", "내", "외"}
SENT_END_PUNCT = {"SF", "SE", "SS", "SP", "SW", "SO"}


def eojeols(sent: str) -> list[str]:
    return [w for w in sent.split() if re.search(r"[0-9A-Za-z가-힣]", w)]


def split_sentences(text: str) -> list[str]:
    return [s.text.strip() for s in kiwi().split_into_sents(text) if s.text.strip()]


def is_korean_sentence(sent: str, toks) -> bool:
    """한국어 서술문인가: 한글 비율, 어절 수, 종결어미로 판단한다."""
    letters = len(HANGUL.findall(sent)) + len(LATIN.findall(sent.replace(CODE_TOKEN, "")))
    if letters == 0 or len(HANGUL.findall(sent)) / letters < 0.5:
        return False
    if len(eojeols(sent)) < 3:
        return False
    core = [t for t in toks if t.tag not in SENT_END_PUNCT]
    return bool(core) and core[-1].tag == "EF"


def tokenize(sent: str):
    return kiwi().tokenize(sent)


def eojeol_index(sent: str, toks) -> list[int]:
    """형태소마다 몇 번째 어절에 속하는지 돌려준다."""
    starts = [m.start() for m in re.finditer(r"\S+", sent)]
    idx = []
    j = 0
    for t in toks:
        while j + 1 < len(starts) and starts[j + 1] <= t.start:
            j += 1
        idx.append(j)
    return idx


def ui_chain(toks) -> int:
    """한 명사구 안에서 '의'(JKG)가 몇 번 이어지는지 최댓값.

    '의' 사이에 명사만 오면 같은 명사구로 본다. 쉼표, 그리고 '동안', '경우'
    같은 부사성 명사가 오면 사슬을 끊는다.
    """
    best = cur = 0
    for t in toks:
        if t.tag == "JKG":
            cur += 1
            best = max(best, cur)
        elif t.form in BREAK_NOUNS or t.form == ",":
            cur = 0
        elif t.tag in NOMINAL or t.tag in {"SSO", "SSC"}:
            continue
        else:
            cur = 0
    return best


def noun_run(sent: str, toks) -> tuple[int, str]:
    """띄어 쓴 한글 명사만으로 이어진 어절 수의 최댓값.

    - 마지막 어절은 조사나 '이다'가 붙어도 된다.
    - 영문, 숫자, 코드 자리표시자가 든 어절은 셈에서 빼고 사슬을 끊는다
      (기술 용어와 코드 이름을 명사 나열로 오판하지 않으려고).
    - 붙여 쓴 복합어(어절 하나 안의 명사 여럿)는 1로 센다.
    """
    idx = eojeol_index(sent, toks)
    words = re.findall(r"\S+", sent)
    per: dict[int, list] = {}
    for t, i in zip(toks, idx):
        per.setdefault(i, []).append(t)
    best, cur, start, best_span = 0, 0, 0, ""
    for i in range(len(words)):
        ts = per.get(i, [])
        tags = [t.tag for t in ts if t.tag not in {"SF", "SP", "SS", "SSO", "SSC", "SW", "SO", "SE"}]
        pure = bool(tags) and all(tg in HANGUL_NOUN or tg == "XSN" for tg in tags) and tags[0] in HANGUL_NOUN
        tail = bool(tags) and tags[0] in HANGUL_NOUN and all(
            tg in HANGUL_NOUN or tg == "XSN" or tg.startswith("J") or tg in {"VCP", "EF", "EC", "ETM", "ETN"} for tg in tags
        )
        has_foreign = bool(re.search(r"[A-Za-z0-9]", words[i]))
        has_punct = bool(re.search(r"[^\w가-힣]", words[i]))
        is_break = any(t.form in BREAK_NOUNS for t in ts)
        if pure and not has_foreign and not has_punct and not is_break:
            if cur == 0:
                start = i
            cur += 1
            # 다음 어절이 조사를 단 명사면 사슬 끝으로 포함
            nxt = per.get(i + 1, [])
            ntags = [t.tag for t in nxt if t.tag not in {"SF", "SP", "SS", "SSO", "SSC", "SW", "SO", "SE"}]
            nword = words[i + 1] if i + 1 < len(words) else ""
            ntail = bool(ntags) and ntags[0] in HANGUL_NOUN and not any(t.form in BREAK_NOUNS for t in nxt) and not all(tg in HANGUL_NOUN or tg == "XSN" for tg in ntags) and all(
                tg in HANGUL_NOUN or tg == "XSN" or tg.startswith("J") or tg in {"VCP", "XSV", "XSA"} for tg in ntags
            )
            run = cur + (1 if ntail and not re.search(r"[A-Za-z0-9]", words[i + 1] if i + 1 < len(words) else "") else 0)
            if run > best:
                best = run
                best_span = " ".join(words[start : start + run])
        else:
            cur = 0
        _ = tail
    return best, best_span


AUX_AFTER = {"VX"}
# 조사처럼 쓰여 절을 만들지 않는 동사: 'N을 통해', 'N에 따라'
POSTP_VERBS = {"통하", "위하", "따르", "비하", "대하", "의하", "인하", "관하", "걸치", "향하", "불구하", "말미암", "즈음하", "앞서", "비롯하", "포함하", "제외하", "대비하"}


def clause_estimate(toks) -> dict:
    """연결어미로 이어진 절 수를 추정한다.

    연결어미(EC) 뒤에 보조 용언(VX)이 오면 '-고 있다', '-지 않다', '-어 주다'
    같은 한 서술어의 일부로 보고 절 경계로 세지 않는다.
    '-게 되다/하다', '-지 못하다'도 보조 구성으로 본다.
    관형절(ETM)과 명사절(ETN)은 따로 센다.
    """
    ec_total = ec_aux = 0
    etm = etn = 0
    for i, t in enumerate(toks):
        if t.tag == "EC":
            ec_total += 1
            prev = toks[i - 1] if i > 0 else None
            nxt = toks[i + 1] if i + 1 < len(toks) else None
            # 보조사(는, 도, 만) 하나는 건너뛰고 다음 용언을 본다: '-지는 않다', '-어도 좋다'
            nxt2 = toks[i + 2] if nxt is not None and nxt.tag == "JX" and i + 2 < len(toks) else nxt
            if prev is not None and prev.tag in {"VV", "VA"} and prev.form in POSTP_VERBS:
                ec_aux += 1  # '통해', '위해', '따라', '대해': 조사처럼 쓰는 동사
            elif t.form == "게" and prev is not None and prev.tag in {"VA", "XSA"}:
                ec_aux += 1  # 부사형 '-게': '자세하게', '어떻게'
            elif t.form in {"라고", "다고", "냐고", "자고"}:
                ec_aux += 1  # 인용
            elif nxt2 is None:
                continue
            elif nxt2.tag in AUX_AFTER:
                ec_aux += 1
            elif t.form == "지" and nxt2.form in {"않", "못", "말"}:
                ec_aux += 1
            elif t.form in {"게", "도록"} and nxt2.form in {"되", "하"}:
                ec_aux += 1
            elif t.form in {"면", "으면"} and nxt2.form in {"되", "안"}:
                ec_aux += 1  # '-면 되다'
            elif t.form in {"어도", "아도", "도"} and nxt2.form in {"되", "좋", "괜찮"}:
                ec_aux += 1  # '-어도 되다/좋다'
            elif t.form == "고" and nxt2.form == "하" and prev is not None and prev.tag in {"EF", "EP"}:
                ec_aux += 1  # 인용 '-다고 하다'
        elif t.tag == "ETM":
            etm += 1
        elif t.tag == "ETN":
            etn += 1
    # 문장 맨 끝 EC(예: '-요' 생략형)는 Kiwi가 EF로 준다. 끝의 EC는 없다고 본다.
    connective = ec_total - ec_aux
    return {"ec": ec_total, "ec_aux": ec_aux, "clauses": 1 + connective, "etm": etm, "etn": etn}


def comma_after_ec(sent: str, toks) -> int:
    n = 0
    for i, t in enumerate(toks[:-1]):
        if t.tag == "EC" and toks[i + 1].form == "," and toks[i + 1].start == t.start + t.len:
            n += 1
    return n


def kyungwoo(toks) -> int:
    """관형형 어미 뒤 '경우' (~할 경우)."""
    return sum(1 for i, t in enumerate(toks[1:], 1) if t.form == "경우" and toks[i - 1].tag == "ETM")


# ---------------------------------------------------------------------------
# 3. 표현 패턴 (표면 정규식). 목록 A는 두 모드 모두 고칠 후보, B는 엄격 모드에서만.

PATTERNS: dict[str, dict] = {
    # --- A: 뜻을 흐리거나 규범에 어긋나 읽기를 방해하는 표현의 후보
    "A.double_passive": {"list": "A", "rule": "LX-7", "re": r"(되어|보여|쓰여|열려|나뉘어|불려|잊혀|바뀌어|닫혀|읽혀|믿겨|씌어|짜여)(지[다고는면며며서]|진|졌|집|질)"},
    "A.vague_ref": {"list": "A", "rule": "AM-3", "re": r"(?:^|\s)(상기|위의|위에서|전술한|해당 사항|그 부분|이 부분|이와 같은|이러한 점)"},
    # --- B: 뜻은 통하지만 길거나 딱딱한 표현. 엄격 모드에서만 고친다. 문맥 판정 필요.
    "B.e_daehan": {"list": "B", "rule": "LX-4", "re": r"에 (대한|대해서?|대하여)"},
    "B.tonghae": {"list": "B", "rule": "LX-4", "re": r"[을를] (통해서?|통하여|통한)"},
    "B.inhae": {"list": "B", "rule": "LX-4", "re": r"로 (인해서?|인하여|인한)"},
    "B.e_isseo": {"list": "B", "rule": "LX-4", "re": r"에 있어(서)?(?:[^가-힣]|$)"},
    "B.gwanryeon": {"list": "B", "rule": "LX-4", "re": r"[와과] 관련(하여|해서?|된|한)"},
    "B.e_uihae": {"list": "B", "rule": "LX-4", "re": r"에 (의해서?|의하여|의한)"},
    "B.wihae": {"list": "B", "rule": "LX-4", "re": r"(?:[을를]|기) (위해서?|위하여|위한)"},
    "B.ham_e_ttara": {"list": "B", "rule": "LX-4", "re": r"함에 따라"},
    "B.gajigo_itda": {"list": "B", "rule": "LX-4", "re": r"[을를] 가지고 (있|있)"},
    "B.ganeung": {"list": "B", "rule": "LX-4", "re": r"것이 가능"},
    "B.piryoro": {"list": "B", "rule": "LX-4", "re": r"[을를] 필요로 (하|한|합)"},
    "B.nominal_verb": {"list": "B", "rule": "LX-3", "re": r"(진행|수행|실시|시행)(하|되|합|했|됩|됐|해|돼|한|된|할|될)"},
    "B.provide": {"list": "B", "rule": "LX-3", "re": r"제공(하|되|합|했|됩|됐|해|돼|한|된|할|될)"},
    "B.hanja": {"list": "B", "rule": "LX-5", "re": r"(소요|기재|위치하|상기|금번|익일|당해|기 ?발급|제반|상존|득하|도래)"},
    "B.hadorok_hada": {"list": "B", "rule": "RD-2", "re": r"도록 (하겠|하십시오|합니다|해 ?주시|하세요|할 것)"},
    "B.mit": {"list": "B", "rule": "LX-5", "re": r"(?:^|\s)및(?:\s|$)"},
    # --- AI 티 비교용 신호 (목록 A/B와 별개. 측정만 한다)
    "S.eval": {"list": "S", "rule": "RD-1", "re": r"(중요한|중요합니다|중요해요|핵심적|핵심은|효과적|강력한|강력하게|획기적|혁신적|완벽|최적의|간편|손쉽|깔끔|원활|매끄럽|탁월|뛰어난|훌륭|유용한|유용합니다|편리|안정적|다양한)"},
    "S.intensifier": {"list": "S", "rule": "RD-2", "re": r"(?:^|\s)(매우|정말|굉장히|아주|훨씬|상당히|대단히|확실히)(?:\s)"},
    "S.meta": {"list": "S", "rule": "RD-3", "re": r"(다음과 같|아래와 같|살펴보|알아보|정리하면|요약하면|결론적으로|참고로|앞서 (설명|말|언급)|한마디로|이 글에서는|이 문서에서는|간단히 말해|쉽게 말해|요컨대)"},
    "S.contrast": {"list": "S", "rule": "RD-4", "re": r"(단순히?[^.?!]{0,30}(이|가) 아니라|뿐만 아니라|그 이상|가 아니라 [^.?!]{0,30}입니다)"},
    "S.closing": {"list": "S", "rule": "RD-4", "re": r"(도움이 되(었|셨|길|면)|궁금한 점|궁금하신|필요하시면|원하시면|말씀해 주세요|알려 ?주세요|문의해 주세요|물어보세요)"},
    "S.important": {"list": "S", "rule": "RD-1", "re": r"것이 (중요|좋|핵심)"},
    "S.demonstrative": {"list": "S", "rule": "AM-3", "re": r"(?:^|\s)(이러한|이런|이를|이는|이것은|이로 인해|그러한|해당)(?:\s|$)"},
    "S.dash": {"list": "S", "rule": "FM-4", "re": r"\s[—–]\s|—"},
    "S.exclaim": {"list": "S", "rule": "FM-1", "re": r"!\s*$"},
}

COMPILED = {k: re.compile(v["re"]) for k, v in PATTERNS.items()}


def pattern_hits(sent: str) -> dict[str, int]:
    return {k: len(rx.findall(sent)) for k, rx in COMPILED.items() if rx.search(sent)}


IMPERATIVE_EF = {"세요", "으세요", "십시오", "으십시오", "시오", "으시오", "어라", "아라", "라", "으라", "자", "ㅂ시다", "읍시다", "어요_imp"}


def analyze_sentence(sent: str) -> dict | None:
    toks = tokenize(sent)
    if not is_korean_sentence(sent, toks):
        return None
    nr, span = noun_run(sent, toks)
    ce = clause_estimate(toks)
    hits = pattern_hits(sent)
    k = kyungwoo(toks)
    if k:
        hits["B.kyungwoo"] = k
    c = comma_after_ec(sent, toks)
    if c:
        hits["S.comma_after_ec"] = c
    core = [t for t in toks if t.tag not in SENT_END_PUNCT]
    ef = core[-1].form if core else ""
    return {
        "sent": sent,
        "mood": "imp" if ef in IMPERATIVE_EF else ("q" if sent.rstrip().endswith("?") else "decl"),
        "eojeol": len(eojeols(sent)),
        "ui": ui_chain(toks),
        "noun_run": nr,
        "noun_span": span,
        **ce,
        "hits": hits,
    }


# 문맥 판단이 필요한 모호성 후보 (측정 대상 아님)
PATTERNS_EXTRA = {
    "AM-1": r"((모든|모두|전부|다) [^.?!]{0,30}(지 않|지 못|안 |못 )|만 [^.?!]{0,15}(지 않|지 못))",
    "AM-2": r"(ㄹ|을|할|될|볼|줄|쓸|갈|올|알|열|널|걸|팔) 수 있",
}
