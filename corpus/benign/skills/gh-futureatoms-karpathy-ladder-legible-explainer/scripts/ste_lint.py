#!/usr/bin/env python3
"""Check text against the core ASD-STE100 writing rules and the house style.

This is a heuristic linter. It catches the rules that a script can see without
a part-of-speech tagger: sentence and paragraph length, verb forms that STE
does not approve (progressive, perfect, other -ing forms, passive voice),
common unapproved words and phrasal verbs, more than one instruction in a
sentence, semicolons, and the house style rules (no dashes as punctuation,
no "caveat", no headcount openers, no "X, not Y" framing). The STE dictionary
(asd-ste100.org) is the authority on words: a hit here means "look again",
and a clean run does not prove full STE conformance.

Input formats: plain text, Markdown, HTML and SVG (chosen by file extension,
or with --format; stdin defaults to Markdown). Text you quote on purpose as a
non-STE example can be excluded:
  HTML / SVG : put data-ste="ignore" on the element
  Markdown   : wrap it in <!-- ste-ignore-start --> ... <!-- ste-ignore-end -->
Code (fenced, inline, <code>, <pre>, <kbd>, <samp>) is always excluded.

Modes:
  80      (default) "80% of the way to STE": the grammar is kept, the word list
          is relaxed. Fails on any error: a sentence more than 3 words over its
          limit (or more than 1 in 10 sentences over at all), a paragraph over 6
          sentences, progressive or perfect verbs, passive voice in an
          instruction or with a named agent, semicolons, dashes, house-rule
          breaks. Word-level findings (unapproved words, phrasal verbs, other
          -ing forms, check/test as verbs, two instructions) are warnings; it
          passes when at least 80% of the sentences have no warning.
  strict  Passes only with zero findings of any kind.

Usage:
  ste_lint.py FILE|- [--mode 80|strict] [--format text|md|html|svg] [--allow w1,w2] [--json]
  ste_lint.py --self-test
Exit code: 0 pass, 1 fail, 2 usage or read error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from pathlib import Path

PROCEDURAL_LIMIT = 20
DESCRIPTIVE_LIMIT = 25
PARAGRAPH_LIMIT = 6
OVERRUN_80 = 3            # words a sentence may run over its limit in 80 mode
OVERRUN_SHARE_80 = 0.10   # share of sentences that may run over at all in 80 mode

# Common words that STE does not approve, with the approved word to use.
# Checked against the STEMG FAQ and an Issue 9 dictionary copy (2026-10-03).
# A short working subset for this tool, not the STE dictionary.
# Multi-word phrases are matched first.
UNAPPROVED: dict[str, str] = {
    "it is imperative that": "must",
    "in order to": "to",
    "prior to": "before",
    "in the event of": "if there is",
    "in the event that": "if",
    "a number of": "some, many",
    "due to": "because of",
    "at this point in time": "now",
    "accomplish": "do, complete",
    "additional": "more",
    "advise": "tell",
    "allow": "let",
    "ascertain": "find, make sure",
    "assist": "help",
    "attempt": "try",
    "avoid": "prevent, do not",
    "begin": "start",
    "choose": "select",
    "commence": "start",
    "demonstrate": "show",
    "determine": "find, calculate",
    "eliminate": "remove",
    "endeavour": "try",
    "endeavor": "try",
    "ensure": "make sure",
    "facilitate": "help, make easier",
    "illustrate": "show",
    "indicate": "show",
    "initiate": "start",
    "inspect": "examine",
    "leverage": "use",
    "locate": "find",
    "maintain": "keep",
    "modify": "change",
    "numerous": "many",
    "obtain": "get",
    "often": "frequently",
    "perform": "do",
    "permit": "let",
    "purchase": "buy",
    "replenish": "fill",
    "retain": "keep",
    "terminate": "stop",
    "utilize": "use",
    "utilise": "use",
    "verify": "make sure, do a check",
    "via": "through",
    "whether": "if",
}

# Phrasal verbs (STE section 9). Replace with one approved verb.
PHRASAL: dict[str, str] = {
    "set up": "install, prepare, make",
    "carry out": "do",
    "shut down": "stop",
    "find out": "find",
    "figure out": "find",
    "point out": "show, tell",
    "roll out": "release in steps",
    "look into": "examine",
    "come up with": "make",
    "go through": "examine",
    "fill in": "write",
    "fill out": "write",
    "pick up": "get",
    "back up": "make a copy of",
}

# Imperative verbs common in technical instructions. Used to tell a
# procedural sentence (limit 20) from a descriptive one (limit 25).
IMPERATIVES = set(
    """add adjust align apply attach bend call change check choose clean click close
    compare configure connect copy cut decrease delete disconnect do download drain
    drop enter examine fill find fit flush get give go hold identify increase
    install keep let lift look loosen lower make mark measure merge monitor move
    open operate paste prepare pull push put read record refer release remove
    repeat replace reset restart return run save see select send set show start
    stop supply tag tell test tighten tilt try turn type unplug update upload use
    wait write""".split()
)
SEQUENCE_WORDS = set("then first next now again also finally second third last".split())

# Words ending in -ing that are not verb forms (nouns, approved adjectives,
# prepositions), and common software technical nouns. Plurals are handled.
ING_OK = set(
    """anything bearing bring building ceiling clothing coupling during everything
    evening fitting heading housing king landing lining missing morning nothing
    opening padding remaining ring seating setting sing something spring string
    swing thing timing warning wing wiring ping sling sting bling
    caching logging routing hashing streaming scheduling rendering networking
    billing pricing encoding mapping binding polling sharding indexing spacing
    tracing profiling testing debugging versioning buffering batching casing
    offering pairing meaning writing reading drawing understanding training
    recording marking finding rating wording thinking feeling lighting
    painting filling holding learning misleading interesting confusing surprising
    outstanding pending existing following leading matching corresponding
    underlying""".split()
)

IRREGULAR_PARTICIPLES = set(
    """been begun bent broken brought built bought caught chosen come cut done drawn
    driven eaten fallen felt found forgotten frozen given gone grown held hidden
    hit hung kept known laid led left lent lost made meant met paid put read
    ridden risen run said seen sent set shaken shown shut sold spent split spread
    stood stolen struck sworn taken taught thrown told torn understood woken worn
    won written""".split()
)
NOT_PARTICIPLES = set("bed breed feed hundred indeed need red seed speed shed embed".split())

# Past participles that describe a state after "is" in an instruction
# ("Make sure that the cable is connected"). STE approves these as adjectives.
STATIVE = set(
    """closed open opened full empty clean dry wet loose tight ready off on
    connected disconnected installed attached aligned tightened locked unlocked
    damaged worn broken seated secured stopped removed engaged disengaged
    enabled disabled set correct cool hot cold safe""".split()
)

ADVERBS = r"(?:(?:not|already|also|just|now|never|still|always|usually|again|\w+ly)\s+){0,2}"
BE_FORMS = r"(?:am|is|are|was|were|be|been|being)"
ABBREVIATIONS = ["e.g.", "i.e.", "etc.", "vs.", "fig.", "no.", "approx.", "dr.", "mr.", "ms.", "st.", "a.m.", "p.m."]
DETERMINERS = set("the a an all this that these those it its each one two three your our their".split())
UNITS = set(
    """mm cm m km in ft s ms us ns min h hr hrs d kg g mg lb l ml v mv a ma w kw hz khz mhz ghz
    b kb mb gb tb kib mib gib tib px pt em rem % °c °f c f psi bar kpa mpa nm rpm fps bps kbps mbps gbps""".split()
)
NUMBER_WORDS = r"(?:two|three|four|five|six|seven|eight|nine|ten|\d+|a couple of|a few|several|a handful of)"
COUNT_NOUNS = r"(?:things|points|options|reasons|asks|steps|ways|concerns|issues|questions|changes|items|takeaways|lessons|ideas|parts|facts|rules)"

WORD_RE = re.compile(r"[A-Za-z0-9°%][A-Za-z0-9'’\-\.°%]*[A-Za-z0-9%]|[A-Za-z0-9%]")


@dataclass
class Finding:
    rule: str
    severity: str  # "error" or "warning"
    message: str
    text: str
    block: int


@dataclass
class Block:
    text: str
    kind: str  # "paragraph", "item", "heading", "cell", "label"
    index: int = 0


@dataclass
class Report:
    mode: str
    blocks: int = 0
    sentences: int = 0
    clean_sentences: int = 0
    conformance: float = 1.0
    passed: bool = True
    findings: list[Finding] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- extraction

BLOCK_TAGS = {
    "p": "paragraph", "li": "item", "td": "cell", "th": "cell", "dt": "item", "dd": "item",
    "h1": "heading", "h2": "heading", "h3": "heading", "h4": "heading", "h5": "heading",
    "h6": "heading", "figcaption": "paragraph", "caption": "label", "blockquote": "paragraph",
    "div": "paragraph", "section": "paragraph", "article": "paragraph", "header": "paragraph",
    "footer": "paragraph", "aside": "paragraph", "main": "paragraph", "nav": "label",
    "label": "label", "button": "label", "summary": "label", "text": "label", "title": "label",
    "body": "paragraph", "table": "label", "tr": "label", "ul": "label", "ol": "label",
    "dl": "label", "figure": "paragraph", "small": "label",
}
SKIP_TAGS = {"script", "style", "code", "pre", "kbd", "samp", "del", "s", "head", "noscript", "template"}
VOID_TAGS = {"br", "img", "hr", "input", "meta", "link", "source", "col", "wbr", "path", "rect", "circle",
             "line", "polyline", "polygon", "ellipse", "use", "stop"}


class _Extractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[Block] = []
        self.buf: list[str] = []
        self.kind_stack: list[str] = []
        self.skip_depth = 0
        self.tag_stack: list[tuple[str, bool]] = []  # (tag, opened_skip)

    def _flush(self) -> None:
        text = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        self.buf = []
        if text:
            kind = self.kind_stack[-1] if self.kind_stack else "paragraph"
            self.blocks.append(Block(text, kind))

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs_d = {k.lower(): (v or "") for k, v in attrs}
        if tag in VOID_TAGS:
            if tag == "br" and not self.skip_depth:
                self._flush()
            return
        opens_skip = tag in SKIP_TAGS or attrs_d.get("data-ste", "").lower() == "ignore"
        self.tag_stack.append((tag, opens_skip))
        if opens_skip:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag == "tspan" and any(a in attrs_d for a in ("x", "y", "dy")):
            self._flush()  # a positioned tspan starts a new visual line
        kind = BLOCK_TAGS.get(tag)
        if kind is not None:
            self._flush()
            self.kind_stack.append(kind)
        else:
            self.buf.append(" ")  # tag boundary is a word boundary for inline tags

    def handle_startendtag(self, tag, attrs):
        if tag.lower() == "br" and not self.skip_depth:
            self._flush()

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in VOID_TAGS:
            return
        if not any(t == tag for t, _ in self.tag_stack):
            return  # stray end tag: ignore it so it cannot end an ignored region early
        while self.tag_stack:
            t, opened_skip = self.tag_stack.pop()
            if opened_skip:
                self.skip_depth -= 1
            elif not self.skip_depth:
                if BLOCK_TAGS.get(t) is not None:
                    self._flush()
                    if self.kind_stack:
                        self.kind_stack.pop()
                else:
                    self.buf.append(" ")
            if t == tag:
                break

    def handle_data(self, data):
        if not self.skip_depth:
            self.buf.append(data)

    def close(self):
        super().close()
        self._flush()


def extract_html(source: str) -> list[Block]:
    parser = _Extractor()
    parser.feed(source)
    parser.close()
    return parser.blocks


TABLE_DELIM = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")


def _split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line)]


def extract_markdown(source: str) -> list[Block]:
    source = re.sub(r"\A---\n.*?\n---\n", "\n", source, flags=re.S)  # YAML front matter
    source = re.sub(r"<!--\s*ste-ignore-start\s*-->.*?<!--\s*ste-ignore-end\s*-->", "\n\n", source, flags=re.S)
    source = re.sub(r"<!--.*?-->", "", source, flags=re.S)
    source = re.sub(r"^(```|~~~)[^\n]*\n.*?(^\1[^\n]*$|\Z)", "\n", source, flags=re.S | re.M)
    lines = source.splitlines()
    table_rows: set[int] = set()
    for i in range(len(lines) - 1):
        if "|" in lines[i] and TABLE_DELIM.match(lines[i + 1]):
            j = i
            while j < len(lines) and lines[j].strip() and ("|" in lines[j]):
                table_rows.add(j)
                j += 1
    blocks: list[Block] = []
    para: list[str] = []

    def flush():
        if para:
            blocks.append(Block(" ".join(para).strip(), "paragraph"))
            para.clear()

    for n, raw in enumerate(lines):
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        if n in table_rows:
            flush()
            if TABLE_DELIM.match(stripped):
                continue
            for cell in _split_row(stripped):
                if cell:
                    blocks.append(Block(cell, "cell"))
            continue
        if re.match(r"^#{1,6}\s", stripped):
            flush()
            blocks.append(Block(re.sub(r"^#{1,6}\s+", "", stripped), "heading"))
            continue
        m = re.match(r"^([-*+]|\d+[.)])\s+(.*)", stripped)
        if m:
            flush()
            blocks.append(Block(m.group(2), "item"))
            continue
        if stripped.startswith(">"):
            stripped = stripped.lstrip("> ")
        if blocks and blocks[-1].kind == "item" and raw.startswith(("  ", "\t")) and not para:
            blocks[-1].text += " " + stripped
            continue
        para.append(stripped)
    flush()
    for b in blocks:
        b.text = clean_inline_markdown(b.text)
    return [b for b in blocks if b.text]


def clean_inline_markdown(text: str) -> str:
    text = re.sub(r"`[^`]*`", " CODE ", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"(\*\*|__|\*|_)(\S.*?\S|\S)\1", r"\2", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_text(source: str) -> list[Block]:
    blocks = []
    for p in re.split(r"\n\s*\n", source):
        lines = [ln.strip() for ln in p.splitlines() if ln.strip()]
        if lines and all(re.match(r"^([-*+]|\d+[.)])\s+", ln) for ln in lines):
            blocks += [Block(re.sub(r"^([-*+]|\d+[.)])\s+", "", ln), "item") for ln in lines]
        elif lines:
            blocks.append(Block(" ".join(lines), "paragraph"))
    return blocks


# ---------------------------------------------------------------- analysis

def split_sentences(text: str) -> list[str]:
    protected = text
    for abbr in ABBREVIATIONS:
        protected = re.sub(r"(?<![A-Za-z])" + re.escape(abbr), lambda m: m.group(0).replace(".", "\u2024"), protected, flags=re.I)
    protected = re.sub(r"(\d)\.(\d)", "\\1\u2024\\2", protected)
    parts = re.split(r"(?<=[.!?])[\"'”’)\]]*\s+(?=[\"'“‘(\[]?[A-Z0-9])|(?<=[a-z0-9][.!?])(?=[A-Z])", protected)
    return [p.replace("\u2024", ".").strip() for p in parts if p and p.strip()]


def words(sentence: str) -> list[str]:
    return WORD_RE.findall(sentence)


def count_words(sentence: str) -> int:
    """STE count: a number and its unit count as one word; a hyphenated word is one word."""
    ws = words(sentence)
    n = 0
    i = 0
    while i < len(ws):
        if re.fullmatch(r"[\d.,]+", ws[i]) and i + 1 < len(ws) and ws[i + 1].lower() in UNITS:
            i += 2
        else:
            i += 1
        n += 1
    return n


def _lead(ws: list[str]) -> list[str]:
    """Drop leading sequence words: "Then remove ..." -> "remove ..."."""
    i = 0
    while i < len(ws) and ws[i] in SEQUENCE_WORDS:
        i += 1
    return ws[i:]


def is_procedural(sentence: str) -> bool:
    if re.match(r"^\s*note\s*:", sentence, re.I):
        return False
    if re.match(r"^\s*(warning|caution)\s*:", sentence, re.I):
        return True
    ws = _lead([w.lower() for w in words(sentence)])
    if not ws:
        return False
    if ws[0] in {"if", "when", "before", "after", "while", "until"} and "," in sentence:
        ws = _lead([w.lower() for w in words(sentence.split(",", 1)[1])])
        if not ws:
            return False
    if ws[0] == "do" and len(ws) > 1 and ws[1] == "not":
        return True
    if ws[0] not in IMPERATIVES:
        return False
    # "Return values are stored ..." and "Open source software is ..." are descriptions.
    head = ws[1:4]
    if any(re.fullmatch(BE_FORMS + "|has|have", w) for w in head) and not any(w in DETERMINERS for w in ws[1:3]):
        return False
    return True


def _is_participle(word: str) -> bool:
    w = word.lower()
    if w in NOT_PARTICIPLES:
        return False
    return w in IRREGULAR_PARTICIPLES or (w.endswith("ed") and len(w) > 4)


def _phrase_pattern(phrase: str) -> str:
    """Regex for a phrase and its inflected forms (ensure, ensures, ensured, ensuring)."""
    head, _, last = phrase.rpartition(" ")
    prefix = re.escape(head + " ") if head else ""
    if last.endswith("e"):
        body = re.escape(last[:-1]) + r"(?:e|es|ed|ing)"
    elif last.endswith("y") and len(last) > 3:
        body = re.escape(last[:-1]) + r"(?:y|ies|ied|ying)"
    else:
        body = re.escape(last) + r"(?:s|es|ed|ing|ly|ted|ting|ning)?"
    return r"(?<![a-z\-])" + prefix + body + r"(?![a-z\-])"


def _phrasal_pattern(phrase: str) -> str:
    verb, _, rest = phrase.partition(" ")
    forms = {verb, verb + "s", verb + "ing", verb + "ed", verb + "ting", verb + "ped", verb + "ned"}
    irregular = {"set": {"set"}, "carry": {"carried", "carries"}, "shut": {"shut"}, "find": {"found"},
                 "come": {"came"}, "go": {"went", "gone", "goes"}, "back": {"backed"}}
    forms |= irregular.get(verb, set())
    return r"(?<![a-z\-])(?:" + "|".join(sorted(map(re.escape, forms), key=len, reverse=True)) + r")\s+" + re.escape(rest) + r"(?![a-z\-])"


def _ing_ok(word: str, allow: set[str]) -> bool:
    w = word.lower().strip("'’")
    base = w[:-1] if w.endswith("s") and w[:-1].endswith("ing") else w
    return base in ING_OK or base in allow or len(base) <= 4


def check_sentence(sentence: str, block_idx: int, kind: str, mode: str, allow: set[str]) -> list[Finding]:
    out: list[Finding] = []
    soft = "warning" if mode == "80" else "error"
    lower = " " + re.sub(r"\s+", " ", sentence.lower()) + " "
    n = count_words(sentence)
    procedural = is_procedural(sentence)
    snippet = sentence if len(sentence) < 160 else sentence[:157] + "..."

    def add(rule, severity, message):
        out.append(Finding(rule, severity, message, snippet, block_idx))

    if re.match(r"^\s*(sources?|references?|see also)\s*:", sentence, re.I):
        return out  # a list of sources is a reference line, not a sentence
    if kind not in {"heading", "label", "cell"} or n > 12:
        limit = PROCEDURAL_LIMIT if procedural else DESCRIPTIVE_LIMIT
        if n > limit:
            add("sentence-length", "error",
                f"{n} words, limit {limit} for {'procedural' if procedural else 'descriptive'} text")

    spans: list[tuple[int, int]] = []
    for phrase in sorted(UNAPPROVED, key=len, reverse=True):
        for m in re.finditer(_phrase_pattern(phrase), lower):
            if any(a <= m.start() < b for a, b in spans) or m.group(0).strip() in allow:
                continue
            spans.append((m.start(), m.end()))
            add("unapproved-word", soft, f'"{m.group(0).strip()}" is not approved, use "{UNAPPROVED[phrase]}"')
    for phrase, alt in PHRASAL.items():
        for m in re.finditer(_phrasal_pattern(phrase), lower):
            add("phrasal-verb", soft, f'phrasal verb "{m.group(0).strip()}", use "{alt}"')

    # check / test are approved only as nouns ("do a check", "do a test").
    ws_l = _lead([w.lower() for w in words(sentence)])
    if ws_l and ws_l[0] in {"check", "test"} and procedural:
        add("noun-only-word", soft, f'"{ws_l[0]}" is approved only as a noun, write "do a {ws_l[0]} of" or "make sure that"')
    for m in re.finditer(r"\b(to|must|can|will|should|do not|don't|and|then)\s+(check|test)(?:s|ed|ing)?\s+(?:the|a|an|that|if|this|these|all|each|your)\b", lower):
        add("noun-only-word", soft, f'"{m.group(2)}" is approved only as a noun, write "do a {m.group(2)}" or "make sure that"')

    progressive_spans = []
    for m in re.finditer(r"\b" + BE_FORMS + r"\s+" + ADVERBS + r"(\w+ing)\b", lower):
        word = m.group(1)
        if not _ing_ok(word, allow):
            progressive_spans.append(m.span(1))
            add("progressive-ing", "error", f'progressive form "{m.group(0).strip()}", use the simple present or past')
    # Other -ing verb forms: a gerund subject, -ing after a preposition, a participle clause.
    det = r"(?:the|a|an|this|that|these|those|it|its|them|your|our|their|all|each|any|some|one|two|three|\d+)"
    ing_patterns = [
        r"^\s*([a-z]{3,}ing)\s+" + det + r"\b",
        r"\b(?:by|before|after|when|while|for|without|of|in|on|from|through|instead of|upon|besides)\s+([a-z]{3,}ing)\b",
        r",\s+([a-z]{3,}ing)\s+" + det + r"\b",
    ]
    seen_ing: set[int] = set()
    for pat in ing_patterns:
        for m in re.finditer(pat, lower):
            if m.start(1) in seen_ing or any(a <= m.start(1) < b for a, b in progressive_spans) or _ing_ok(m.group(1), allow):
                continue
            seen_ing.add(m.start(1))
            add("ing-form", soft, f'"-ing" verb form "{m.group(1)}": use a different construction unless it is a technical noun')

    for m in re.finditer(r"\b(has|have|had)\s+" + ADVERBS + r"(\w+)\b", lower):
        if _is_participle(m.group(1 + 1)):
            add("perfect-tense", "error", f'perfect form "{m.group(0).strip()}", use the simple past or present')

    passive_reported = False
    for m in re.finditer(r"\b" + BE_FORMS + r"\s+" + ADVERBS + r"(\w+)\s+by\s+(?:the|a|an|our|your|their|its|\w+)\b", lower):
        if _is_participle(m.group(1)):
            add("passive-voice", "error", f'passive with a named agent "{m.group(0).strip()}", make the agent the subject')
            passive_reported = True
    if not passive_reported:
        m = re.match(r"^\s*(?:the|a|an|this|that|these|those|all|each)?\s*[\w\-]+(?:\s+[\w\-]+){0,3}?\s+(?:must|should|shall|has to|have to)\s+be\s+(\w+)\b", lower)
        if m and _is_participle(m.group(1)):
            add("passive-voice", "error", f'instruction in the passive "{m.group(0).strip()}", write it as a command')
            passive_reported = True
    if procedural and not passive_reported:
        main = lower
        if re.match(r"^\s*(if|when|before|after|while|until)\b", main) and "," in main:
            main = " " + main.split(",", 1)[1]
        main = re.sub(r"\b(make sure|check|examine|see|find out|tell|monitor)( that| if| whether)?\b.*", " ", main)
        for m in re.finditer(r"\b" + BE_FORMS + r"\s+" + ADVERBS + r"(\w+)\b", main):
            word = m.group(1)
            if _is_participle(word) and word not in STATIVE:
                add("passive-voice", "error", f'passive "{m.group(0).strip()}" in an instruction, say who does it')
                break

    if procedural:
        ws = [w.lower() for w in words(sentence)]
        for i, w in enumerate(ws[1:-1], start=1):
            if w in {"and", "then"} and ws[i + 1] in IMPERATIVES and i + 2 < len(ws) and ws[i + 2] in DETERMINERS:
                add("one-instruction", soft, "more than one instruction, split it unless the actions are simultaneous")
                break

    if ";" in sentence:
        add("semicolon", "error", "semicolon: STE does not use it, write two sentences")
    if "\u2014" in sentence or " -- " in sentence or " \u2013 " in sentence:
        add("dash", "error", "dash in running text, use a comma, colon or a new sentence")

    # House style rules, errors in both modes.
    if re.search(r"\bcaveats?\b", lower):
        add("house-caveat", "error", 'the word "caveat" is banned, state the limitation as a sentence')
    if re.match(r"^\s*(?:(?:there are|here are|i have|we have|you have)\s+)?" + NUMBER_WORDS + r"\s+(?:\w+\s+)?" + COUNT_NOUNS + r"\b", lower) and \
            (sentence.rstrip().endswith(":") or len(words(sentence)) <= 8 or re.search(r"\b(to|worth|that)\b", lower)):
        add("house-headcount", "error", "headcount opener, name the subject instead (\"What to check:\")")
    if re.search(r",\s+not\s+(?:a |an |the )?[\w\-\"“`]+", lower) or re.search(r"\bnot\s+[\w\-]+,\s+but\b", lower):
        add("house-x-not-y", "error", '"X, not Y" framing, state what is true as its own sentence')
    return out


def lint_blocks(blocks: list[Block], mode: str, allow: set[str] | None = None) -> Report:
    allow = allow or set()
    report = Report(mode=mode, blocks=len(blocks))
    overruns: list[int] = []
    counted = 0
    for i, block in enumerate(blocks):
        block.index = i
        sentences = split_sentences(block.text)
        if block.kind == "paragraph" and len(sentences) > PARAGRAPH_LIMIT:
            report.findings.append(Finding("paragraph-length", "error",
                                           f"{len(sentences)} sentences, limit {PARAGRAPH_LIMIT} for each paragraph",
                                           block.text[:120] + ("..." if len(block.text) > 120 else ""), i))
        for s in sentences:
            if not words(s):
                continue
            report.sentences += 1
            found = check_sentence(s, i, block.kind, mode, allow)
            if block.kind != "heading":
                counted += 1
                if not found:
                    report.clean_sentences += 1
            for f in found:
                if f.rule == "sentence-length":
                    n, limit = map(int, re.findall(r"\d+", f.message)[:2])
                    overruns.append(n - limit)
            report.findings.extend(found)

    report.conformance = round(report.clean_sentences / counted, 3) if counted else 1.0
    if mode == "strict":
        report.passed = not report.findings
        if report.findings:
            report.reasons.append(f"{len(report.findings)} findings in strict mode")
        return report

    # 80 mode: grammar is kept, vocabulary is relaxed.
    for f in report.findings:
        if f.rule == "sentence-length":
            n, limit = map(int, re.findall(r"\d+", f.message)[:2])
            if n - limit <= OVERRUN_80:
                f.severity = "warning"
    if overruns and counted and len(overruns) / counted > OVERRUN_SHARE_80:
        for f in report.findings:
            if f.rule == "sentence-length":
                f.severity = "error"
        report.reasons.append(f"{len(overruns)} of {counted} sentences run over their limit (80 mode allows 1 in 10)")
    errors = [f for f in report.findings if f.severity == "error"]
    if errors:
        rules = sorted({f.rule for f in errors})
        report.reasons.append(f"{len(errors)} errors: {', '.join(rules)}")
    if report.conformance < 0.8:
        report.reasons.append(f"only {report.conformance:.0%} of sentences are free of warnings (80 mode needs 80%)")
    report.passed = not report.reasons
    return report


def lint_source(source: str, fmt: str, mode: str = "80", allow: set[str] | None = None) -> Report:
    if fmt in {"html", "svg"}:
        blocks = extract_html(source)
    elif fmt == "md":
        blocks = extract_markdown(source)
    else:
        blocks = extract_text(source)
    return lint_blocks(blocks, mode, allow)


def detect_format(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {".html": "html", ".htm": "html", ".svg": "svg", ".md": "md", ".markdown": "md"}.get(ext, "text")


def print_report(report: Report, path: str) -> None:
    status = "PASS" if report.passed else "FAIL"
    print(f"{status}  {path}  mode={report.mode}  sentences={report.sentences}  "
          f"clean={report.clean_sentences}  warning-free share={report.conformance:.0%}")
    for reason in report.reasons:
        print(f"  reason: {reason}")
    by_rule: dict[str, int] = {}
    for f in report.findings:
        by_rule[f.rule] = by_rule.get(f.rule, 0) + 1
    if by_rule:
        print("  findings: " + ", ".join(f"{k}={v}" for k, v in sorted(by_rule.items())))
    ordered = sorted(report.findings, key=lambda f: f.severity != "error")
    for f in ordered[:60]:
        print(f"  [{f.severity}] {f.rule}: {f.message}\n      block {f.block}: {f.text}")
    if len(report.findings) > 60:
        print(f"  ... {len(report.findings) - 60} more (use --json for all)")
    if report.passed and report.findings:
        print("  PASS means the floor is met. Fix every finding that is not a false alarm.")


# ---------------------------------------------------------------- self-test

def self_test() -> int:
    S, E = "strict", "80"
    cases = [
        # (text, fmt, mode, expected_pass, rules that must appear)
        ("It is imperative that the operator ensures the hydraulic reservoir is replenished prior to commencing operation.",
         "text", S, False, {"unapproved-word"}),
        ("Make sure that the hydraulic reservoir is full before you start the operation.", "text", S, True, set()),
        ("WARNING: Do not touch the brake unit until it is cool. Hot parts can cause injury.", "text", S, True, set()),
        ("The pump supplies fuel to the engine when the switch is on.", "text", S, True, set()),
        ("The cost decreases by approximately 30%.", "text", S, True, set()),
        ("Begin the procedure.", "text", S, False, {"unapproved-word"}),
        ("The valve is closing.", "text", S, False, {"progressive-ing"}),
        ("The pump is not running.", "text", S, False, {"progressive-ing"}),
        ("The valve has closed.", "text", S, False, {"perfect-tense"}),
        ("The valve has already closed.", "text", S, False, {"perfect-tense"}),
        ("The valve must be closed by the operator.", "text", S, False, {"passive-voice"}),
        ("The damaged panel must be removed.", "text", S, False, {"passive-voice"}),
        ("Make sure that the valve is replaced by the technician.", "text", S, False, {"passive-voice"}),
        ("Make sure that the cable is connected.", "text", S, True, set()),
        ("If the seal is damaged, replace the seal.", "text", S, True, set()),
        ("Return values are stored in the register.", "text", S, True, set()),
        ("Remove the cap and examine the seal.", "text", S, False, {"one-instruction"}),
        ("Then remove the cap and examine the seal.", "text", S, False, {"one-instruction"}),
        ("Check the oil level.", "text", S, False, {"noun-only-word"}),
        ("Before starting the pump, close the valve.", "text", S, False, {"ing-form"}),
        ("Set up the server; then roll out the change.", "text", S, False, {"semicolon", "phrasal-verb"}),
        ("Turn the knob, then push the lever to the stop position and hold the lever there until the green light comes on in the cockpit.",
         "text", S, False, {"sentence-length"}),
        ("Make sure that the distance between the two green marks on the pipe is 10 mm before the first system run.",
         "text", S, True, set()),
        ("Run the test. Then stop the pump.", "text", S, True, set()),
        ("The page loads fast \u2014 most of the time.", "text", E, False, {"dash"}),
        ("Use no-store, not no-cache, for private data.", "text", E, False, {"house-x-not-y"}),
        ("There are three things to know.", "text", E, False, {"house-headcount"}),
        ("The caveat is the TTL.", "text", E, False, {"house-caveat"}),
        ("<p>Use the valve.</p><p data-ste='ignore'>It is imperative that you utilize the valve.</p>", "html", S, True, set()),
        ("<div data-ste='ignore'><span>x</span></span>Utilize it.</div><p>Use the valve.</p>", "html", S, True, set()),
        ("<p><b>Note</b>ensure that the valve is closed.</p>", "html", S, False, {"unapproved-word"}),
        ("Use the valve.\n\n<!-- ste-ignore-start -->\nUtilize the valve.\n<!-- ste-ignore-end -->\n\n`ensure()` is a function name.",
         "md", S, True, set()),
        ("Term | Meaning\n--- | ---\nTTL | The time that a copy stays fresh.\nETag | The version tag of a response.", "md", S, True, set()),
        ("<svg><text>Approved verb</text><text data-ste='ignore'>Not \u201creplenished\u201d</text></svg>", "svg", S, True, set()),
        ("<svg><text><tspan x='0' y='20'>Utilize</tspan><tspan x='0' dy='20'>the pump.</tspan></text></svg>", "svg", S, False, {"unapproved-word"}),
        ("e.g. the value is 2.5 mm. It is fine.", "text", S, True, set()),
    ]
    failures = 0
    for i, (text, fmt, mode, want_pass, want_rules) in enumerate(cases):
        r = lint_source(text, fmt, mode)
        rules = {f.rule for f in r.findings}
        if r.passed != want_pass or not want_rules <= rules:
            failures += 1
            print(f"case {i} FAILED: passed={r.passed} want={want_pass} rules={sorted(rules)} want>={sorted(want_rules)}\n  {text}")
    checks = [
        (count_words("Make sure that the hydraulic reservoir is full before you start the operation."), 13, "word count"),
        (count_words("Set the gap to 10 mm."), 5, "number and unit count as one word"),
        (len(split_sentences("Run the test. Then use the first. Edit the config. Check the items.")), 4, "abbreviation boundary"),
        (len(split_sentences("A fresh copy goes out.A stale copy goes back.")), 2, "glued sentences"),
        (len(extract_html("<li>Line one is here.<small>Line two is here.</small></li>")), 2, "small is its own line"),
    ]
    for got, want, name in checks:
        if got != want:
            failures += 1
            print(f"{name} FAILED: {got} != {want}")
    r = lint_source(" ".join(["Use the valve to stop the flow."] * 4 + ["Utilize the pump."]), "text", E)
    if not r.passed:
        failures += 1
        print("80 mode vocabulary tolerance FAILED:", r.reasons)
    r = lint_source(" ".join(["Use the valve to stop the flow."] * 4 + ["The pump is running."]), "text", E)
    if r.passed:
        failures += 1
        print("80 mode must fail a progressive verb")
    print("self-test:", "OK" if not failures else f"{failures} failure(s)")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?", help="file to check, or - for stdin")
    ap.add_argument("--mode", choices=["80", "strict"], default="80")
    ap.add_argument("--format", choices=["text", "md", "html", "svg"])
    ap.add_argument("--allow", default="", help="comma-separated words to accept (technical nouns of the subject)")
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.file:
        ap.print_usage()
        return 2
    try:
        source = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"cannot read {args.file}: {e}", file=sys.stderr)
        return 2
    fmt = args.format or ("md" if args.file == "-" else detect_format(args.file))
    allow = {w.strip().lower() for w in args.allow.split(",") if w.strip()}
    report = lint_source(source, fmt, args.mode, allow)
    if args.json:
        print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    else:
        print_report(report, args.file)
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
