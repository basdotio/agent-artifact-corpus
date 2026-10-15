#!/usr/bin/env python3
"""Check Markdown and text files against the controlled-language rules.

This script is part of the ``controlled-language`` agent skill. It finds the
problems that a program can find without understanding the text:

- long sentences (S2) and long paragraphs (D2),
- semicolons (S5) and double negatives (S6),
- passive voice (V1), perfect and continuous verb forms (V2),
  and phrasal verbs (V3),
- "-ing" words (W6), US and UK spelling (W8), and abbreviations that have
  no definition (W9),
- words from the word list (``references/word-choices.md``) and the project
  ``avoid_words`` and ``preferred_terms`` (W2, W5, W7, V5, SF3, T1),
- instructions and safety text in notes (P5, SF2), and safety instructions
  that do not start with a command (SF1).

The rule IDs and the strength of each rule at each level come from
``references/rules.md``. The script reads the word list each time it runs, so
the word list is the single source of truth for the words to avoid. The
configuration file is described in ``references/configuration.md``.

Languages: English text gets all the checks above. Text in other languages
gets the checks that do not need English words: S2, D2, S5, and the project
``avoid_words`` and ``preferred_terms``. If the language has a language file
(``references/languages/<code>.md``), the script also uses the word table of
that file and its localized signal words (SF2 in notes). The script finds the
language of each file: ``--lang``, the front matter, the configuration, and
then a simple detection by script and frequent words (see
``detect_language_text``).

The script uses only the Python standard library (Python 3.8 or later). If
PyYAML is installed, the script uses it to read the configuration file. If
not, it uses a small built-in reader for the YAML subset of the
configuration format.

Severity model:

- ``violation``: the rule is "must" at the active level, and the script
  finds the problem reliably.
- ``warning``: the rule is "must", but the result depends on the meaning, so
  a person must examine it.
- ``suggestion``: the rule is "prefer" at the active level.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

try:  # PyYAML is optional.
    import yaml as _pyyaml  # type: ignore
except ImportError:  # pragma: no cover - depends on the environment
    _pyyaml = None

VERSION = "1.0"
CONFIG_NAME = ".controlled-language.yml"
DEFAULT_WORD_LIST = Path(__file__).resolve().parent.parent / "references" / "word-choices.md"
DEFAULT_LANGUAGES_DIR = Path(__file__).resolve().parent.parent / "references" / "languages"
TEXT_EXTENSIONS = (".md", ".mdx", ".markdown", ".txt")
SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__", ".tox"}
DEFAULT_LEVEL = 2

VIOLATION, WARNING, SUGGESTION = "violation", "warning", "suggestion"
ENGLISH, OTHER, AUTO = "en", "other", "auto"
PROCEDURAL, DESCRIPTIVE = "procedural", "descriptive"

# ---------------------------------------------------------------------------
# Rule matrix
# ---------------------------------------------------------------------------

MUST, PREFER, OFF = "must", "prefer", "-"
MUST_PREFER = "must/prefer"  # V1 at Level 1: "must" in procedures, "prefer" in descriptions.
ALL_LANGUAGES, ENGLISH_ONLY = "yes", "english only"
_A, _E = ALL_LANGUAGES, ENGLISH_ONLY

# Strength of each rule at Level 1, Level 2, and Level 3, and if the rule
# applies to all languages or only to English. KEEP THIS TABLE IN SYNC WITH
# THE "Rule matrix" IN references/rules.md. A unit test compares the two
# tables. Text in other languages uses the same strength at each level for
# the rules that apply to all languages.
RULE_MATRIX: Dict[str, Tuple[str, str, str, str]] = {
    "W1": (PREFER, MUST, MUST, _A),
    "W2": (PREFER, MUST, MUST, _A),
    "W3": (MUST, MUST, MUST, _A),
    "W4": (OFF, PREFER, MUST, _E),
    "W5": (OFF, PREFER, MUST, _E),
    "W6": (OFF, PREFER, MUST, _E),
    "W7": (MUST, MUST, MUST, _A),
    "W8": (MUST, MUST, MUST, _A),
    "W9": (MUST, MUST, MUST, _A),
    "T1": (MUST, MUST, MUST, _A),
    "T2": (PREFER, MUST, MUST, _A),
    "T3": (OFF, PREFER, MUST, _E),
    "N1": (MUST, MUST, MUST, _A),
    "N2": (PREFER, MUST, MUST, _E),
    "V1": (MUST_PREFER, MUST, MUST, _A),
    "V2": (OFF, PREFER, MUST, _E),
    "V3": (PREFER, MUST, MUST, _E),
    "V4": (PREFER, MUST, MUST, _A),
    "V5": (PREFER, MUST, MUST, _A),
    "S1": (MUST, MUST, MUST, _A),
    "S2": (MUST, MUST, MUST, _A),
    "S3": (PREFER, MUST, MUST, _A),
    "S4": (MUST, MUST, MUST, _A),
    "S5": (PREFER, MUST, MUST, _A),
    "S6": (PREFER, MUST, MUST, _A),
    "P1": (MUST, MUST, MUST, _A),
    "P2": (PREFER, MUST, MUST, _A),
    "P3": (MUST, MUST, MUST, _A),
    "P4": (MUST, MUST, MUST, _A),
    "P5": (PREFER, MUST, MUST, _A),
    "D1": (MUST, MUST, MUST, _A),
    "D2": (MUST, MUST, MUST, _A),
    "D3": (PREFER, MUST, MUST, _A),
    "SF1": (MUST, MUST, MUST, _A),
    "SF2": (MUST, MUST, MUST, _A),
    "SF3": (MUST, MUST, MUST, _A),
    "PU1": (MUST, MUST, MUST, _A),
    "PU2": (PREFER, MUST, MUST, _A),
    "PU3": (PREFER, MUST, MUST, _A),
}

# Limits from rules.md: S2 (procedural, descriptive) and D2 (sentences). The
# limits are the same for all languages.
S2_LIMITS = {1: (25, 30), 2: (20, 25), 3: (20, 25)}
D2_LIMITS = {1: 8, 2: 6, 3: 6}
# Languages that do not use spaces between words. The script cannot count
# their words, so it does not check S2 for them.
NO_SPACE_LANGUAGES = {"zh", "ja", "th", "lo", "km", "my"}

# Rules that the script checks with its own code. The word list adds the
# rules that its "Note" column names (for example W7 and V5).
BUILT_IN_CHECKS = {
    "S2", "D2", "S5", "S6", "V1", "V2", "V3", "W2", "W6", "W8", "W9", "T1",
    "P5", "SF1", "SF2",
}
# PU1 is the word-count convention that S2 uses. It is not a check.
NOT_A_CHECK = {"PU1"}

# ---------------------------------------------------------------------------
# Built-in word lists
# ---------------------------------------------------------------------------

def _words(text: str) -> Set[str]:
    return set(text.split())


# Verbs that start an instruction. A sentence that starts with one of them
# (after an optional condition) is procedural.
IMPERATIVE_VERBS = _words("""
    accept access activate add adjust allow answer apply approve archive ask assign
    attach authenticate avoid back be browse build calculate call cancel change
    check choose clean clear click clone close collapse combine commit compare
    compile complete configure confirm connect consider contact continue convert
    copy count create cut decide describe explain flag join mention prefer quote
    rewrite say separate shorten simplify split think translate approve assign
    bump comment fork highlight paste pin post rebase reject squash stamp tag
    unpin accomplish achieve attempt begin commence demonstrate display indicate
    initiate leverage terminate utilize
    deactivate debug decrease define delete deploy deselect detach disable
    disconnect dismiss do double-click download drag drop duplicate edit eject
    empty enable ensure enter erase examine exit expand export extract fill
    filter find fix flush follow force format generate get give go grant hold
    identify ignore import include increase insert inspect install keep kill
    launch leave let limit link list load locate lock log look make mark merge
    migrate modify monitor mount move name navigate note obtain open override
    paste pause perform pick place plug point populate press prevent preview
    print provide publish pull purge push put read rebuild reboot record recover
    redeploy refer refresh register reinstall release reload remember remove
    rename reopen repeat replace reply report request reset resize resolve
    restart restore resume retry return revert review revoke right-click rotate
    run save scan schedule scroll search see select send set share shut sign
    skip sort specify start stop store submit subscribe supply swap switch sync
    tap tell test toggle track transfer trigger try turn type uncheck uninstall
    unlock unmount unpack unplug unzip update upgrade upload use validate verify
    view visit wait watch wrap write zoom
""")
# A sentence that starts with one of these words can have a condition first:
# "If the build fails, run ...".
CLAUSE_OPENERS = _words("""
    if when whenever before after until unless once while to for in on at from
    during with without as because where by then next first finally here
    optionally otherwise alternatively
""")
# Words that can come before the verb of an instruction: "Then run ...".
LEADING_ADVERBS = _words("""
    then next first second third finally now also optionally again please
    simply just always carefully manually
""")
# If one of these words follows a possible verb, the verb is a noun:
# "Use of the API is ...", "Update notes are ...".
SUBJECT_FOLLOWERS = _words("""
    is are was were has have had can could will would should may might must
    does did of 's isn't aren't wasn't weren't won't can't cannot
""")
SUBJECT_PRONOUNS = _words("i you he she it we they there")
DETERMINERS = _words("""
    the a an this that these those each every any no your our my its their his
    her some another same which whose
""")

BE_WORDS = _words("""
    am is are was were be been being isn't aren't wasn't weren't it's that's
    there's what's here's who's which's they're you're we're i'm
""")
HAVE_WORDS = _words("""
    has have had having hasn't haven't hadn't i've you've we've they've who've
""")
ADVERBS = _words("""
    not also then now always never still only often usually already just even
    currently first later again sometimes all both
""")

# Past participles that do not end in "-ed".
IRREGULAR_PARTICIPLES = _words("""
    arisen awoken been beaten become begun bent bet bid bitten bled blown born
    borne bought bound bred broken brought built burnt burst caught chosen clung
    come cost crept cut dealt done drawn dreamt driven drunk dug eaten fallen fed
    felt fled flown forbidden forecast foreseen forgiven forgotten frozen gone
    got gotten grown hung heard hidden hit held hurt kept known laid led lent
    let lit lost made meant met mislaid misled mistaken misunderstood overcome
    overdone overheard overridden overrun overseen overtaken overthrown
    overwritten paid proven put quit read rebuilt redone remade repaid rerun
    reset resent retold rewritten ridden risen rung run said seen sought sold
    sent set sewn shaken shed shone shot shown shrunk shut sung sunk sat slept
    slid slung slit sown spoken sped spelt spent spilt spun split spoilt spread
    sprung stood stolen stuck stung struck strung sworn swept swollen swum swung
    taken taught torn told thought thrown thrust understood undergone
    undertaken undone unwound upheld upset woken worn woven wept won withdrawn
    withheld withstood written
""")
# Words that end in "-ed" but are not past participles.
NOT_PARTICIPLES = _words("""
    bed red shred embed hundred sacred naked wicked kindred rugged ragged
    crooked jagged wretched beloved
""")
# Participles that are usually adjectives after "be" or "have". The script
# does not report them as passive voice or as a perfect tense.
ADJECTIVE_PARTICIPLES = _words("""
    based supposed interested located limited advanced detailed experienced
    complicated sophisticated outdated dedicated tired excited pleased
    satisfied concerned related aged learned blessed accustomed skilled
    talented renowned versed qualified
""")
# Participles that show a state ("The file is closed"). rules.md (V2) permits
# the past participle as an adjective, so the script does not report them,
# unless "by" follows ("is closed by the service").
STATIVE_PARTICIPLES = _words("""
    closed opened enabled disabled installed connected disconnected locked
    selected deselected checked expired finished completed done gone
    deprecated approved supported
""")

# Words that end in "-ing" but are not verb forms, or are established nouns.
# W6 does not report them. Keep this list short and documented.
ING_EXCEPTIONS = _words("""
    during something nothing anything everything thing things string strings
    spring springs ring rings king kings sing wing wings sting bring swing cling
    fling sling ceiling ceilings morning mornings evening evenings sibling
    siblings darling pudding inning awning herring shilling viking
    warning warnings setting settings heading headings meaning meanings padding
    ping logging routing spelling wording pricing billing
""")
# "-ing" words that are usually adjectives after "be" ("is missing"). V2 does
# not report them as a continuous tense. W6 still applies.
ADJECTIVE_ING = _words("""
    interesting confusing misleading missing pending outstanding existing
    remaining upcoming ongoing incoming outgoing willing amazing boring
    exciting surprising challenging demanding promising appealing compelling
    convincing disappointing encouraging frustrating overwhelming worrying
    annoying alarming refreshing rewarding charming
""")

# Phrasal verbs (V3) as (verb, particle). "make sure" is approved, so it is
# not in this list.
PHRASAL_VERBS: Tuple[Tuple[str, str], ...] = (
    ("set", "up"), ("turn", "on"), ("turn", "off"), ("find", "out"),
    ("carry", "out"), ("look", "into"), ("fill", "in"), ("fill", "out"),
    ("log", "in"), ("log", "out"), ("back", "up"), ("point", "out"),
    ("figure", "out"), ("go", "ahead"), ("come", "up"), ("end", "up"),
    ("pick", "up"), ("shut", "down"), ("start", "up"), ("spin", "up"),
    ("check", "out"), ("look", "up"), ("sort", "out"), ("run", "into"),
    ("hand", "over"), ("give", "up"), ("put", "in"), ("take", "out"),
    ("set", "off"), ("bring", "up"), ("roll", "back"), ("wrap", "up"),
)
# Phrasal verbs that are often literal when a pronoun separates the verb and
# the particle ("put it in the list"). The script finds only the adjacent form.
PHRASAL_NO_SEPARATION = {("put", "in"), ("take", "out"), ("hand", "over")}
# Inflected forms of the verbs above. "logs" is not included because it is
# usually the plural noun ("the logs in /var/log").
VERB_FORMS: Dict[str, Tuple[str, ...]] = {
    "set": ("set", "sets", "setting"),
    "find": ("find", "finds", "found", "finding"),
    "carry": ("carry", "carries", "carried", "carrying"),
    "log": ("log", "logged", "logging"),
    "figure": ("figure", "figures", "figured", "figuring"),
    "go": ("go", "goes", "went", "gone", "going"),
    "come": ("come", "comes", "came", "coming"),
    "shut": ("shut", "shuts", "shutting"),
    "spin": ("spin", "spins", "spun", "spinning"),
    "run": ("run", "runs", "ran", "running"),
    "give": ("give", "gives", "gave", "given", "giving"),
    "put": ("put", "puts", "putting"),
    "take": ("take", "takes", "took", "taken", "taking"),
    "bring": ("bring", "brings", "brought", "bringing"),
    "wrap": ("wrap", "wraps", "wrapped", "wrapping"),
}
# One-word replacements. The first part is a copy of the V3 table in
# rules.md (a unit test compares them). KEEP IT IN SYNC WITH rules.md.
PHRASAL_SUGGESTIONS: Dict[str, str] = {
    "set up": "install, configure, make",
    "turn on": "start, enable",
    "turn off": "stop, disable",
    "find out": "find, learn",
    "carry out": "do",
    "look into": "examine",
    "fill in": "complete, write",
    "log in": "sign in (if the UI uses it)",
    "back up": "make a backup (of)",
    "point out": "show",
    # Not in the rules.md table:
    "log out": "sign out (if the UI uses it)",
    "shut down": "stop",
    "start up": "start",
    "fill out": "complete",
    "figure out": "find, learn",
    "look up": "find",
}

# Double negatives (S6): "not" + one of these words.
DOUBLE_NEGATIVE_WORDS = _words("""
    uncommon unlike unusual unlikely unknown unimportant unreasonable
    unhelpful unnecessary infrequent insignificant inconsiderable impossible
    improbable incorrect without
""")

# Abbreviations that all readers know (W9 does not report them).
KNOWN_ABBREVIATIONS = _words("""
    API URL URI CLI UI UX ID HTTP HTTPS JSON YAML XML HTML CSS PDF CPU GPU RAM
    OS SDK SQL DNS IP TCP UDP SSH SSL TLS USB FAQ OK PC AI LLM MB GB KB TB US
    UK EU README TODO WARNING CAUTION NOTE IMPORTANT TIP DANGER AM PM UTC CSV
    PNG JPG JPEG GIF SVG ZIP MD NPM GIT ASCII
""")

# US and UK spelling pairs (W8) as (US, UK, both_directions). With
# both_directions=False, the script reports only the UK form, because the US
# form is also correct in UK English ("program" for software).
_SPELLING_PAIRS: Tuple[Tuple[str, str, bool], ...] = (
    ("color", "colour", True), ("behavior", "behaviour", True),
    ("favor", "favour", True), ("favorite", "favourite", True),
    ("honor", "honour", True), ("labor", "labour", True),
    ("neighbor", "neighbour", True), ("flavor", "flavour", True),
    ("humor", "humour", True), ("rumor", "rumour", True),
    ("endeavor", "endeavour", True), ("center", "centre", True),
    ("fiber", "fibre", True), ("liter", "litre", True),
    ("theater", "theatre", True), ("meter", "metre", False),
    ("organize", "organise", True), ("organization", "organisation", True),
    ("analyze", "analyse", True), ("recognize", "recognise", True),
    ("realize", "realise", True), ("customize", "customise", True),
    ("customization", "customisation", True), ("initialize", "initialise", True),
    ("initialization", "initialisation", True), ("optimize", "optimise", True),
    ("optimization", "optimisation", True), ("synchronize", "synchronise", True),
    ("synchronization", "synchronisation", True), ("authorize", "authorise", True),
    ("authorization", "authorisation", True), ("finalize", "finalise", True),
    ("prioritize", "prioritise", True), ("minimize", "minimise", True),
    ("maximize", "maximise", True), ("normalize", "normalise", True),
    ("serialize", "serialise", True), ("summarize", "summarise", True),
    ("visualize", "visualise", True), ("standardize", "standardise", True),
    ("categorize", "categorise", True), ("localize", "localise", True),
    ("localization", "localisation", True), ("utilize", "utilise", True),
    ("emphasize", "emphasise", True), ("sanitize", "sanitise", True),
    ("catalog", "catalogue", True), ("analog", "analogue", False),
    ("defense", "defence", True), ("offense", "offence", True),
    ("gray", "grey", True), ("program", "programme", False),
    ("judgment", "judgement", True), ("acknowledgment", "acknowledgement", True),
    ("aging", "ageing", True), ("enrollment", "enrolment", True),
    ("installment", "instalment", True),
)
# Inflected pairs that need the double "l" in UK English.
_SPELLING_FIXED: Tuple[Tuple[str, str], ...] = (
    ("canceled", "cancelled"), ("canceling", "cancelling"),
    ("labeled", "labelled"), ("labeling", "labelling"),
    ("modeled", "modelled"), ("modeling", "modelling"),
    ("traveled", "travelled"), ("traveling", "travelling"),
    ("signaled", "signalled"), ("signaling", "signalling"),
    ("fulfill", "fulfil"), ("fulfills", "fulfils"), ("fulfillment", "fulfilment"),
)
# Forms that are correct in both variants for another word.
_SPELLING_AMBIGUOUS = {"analyses"}

# Units that make one word with the number before them (PU1): "30 seconds".
UNITS = _words("""
    % percent ms s sec secs second seconds min mins minute minutes h hr hrs
    hour hours day days week weeks month months year years b byte bytes kb mb
    gb tb pb kib mib gib tib bit bits kbps mbps gbps hz khz mhz ghz px pt em rem
    dpi mm cm m km ft kg mg lb lbs v w kw mah rpm fps ns
""")

# Words that show a safety risk (SF2).
RISK_WORDS_RE = re.compile(r"\b(?:warnings?|danger|dangerous|caution|risks?|risky)\b", re.I)

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class UsageError(Exception):
    """The command line, a path, or an input file is not correct (exit 2)."""


class ConfigError(UsageError):
    """The configuration file is not correct."""


class WordListError(UsageError):
    """The word list is not correct."""


# ---------------------------------------------------------------------------
# YAML subset reader
# ---------------------------------------------------------------------------


@dataclass
class _YamlLine:
    number: int
    indent: int
    content: str


_YAML_KEY_RE = re.compile(
    r"""^(?P<key>"(?:[^"\\]|\\.)*"|'(?:[^']|'')*'|[^\s"'#\[\]{},&*!|>%@`-][^:]*?)"""
    r"""\s*:(?:\s+(?P<rest>.*)|$)"""
)
_YAML_BOOL = {
    "yes": True, "true": True, "on": True,
    "no": False, "false": False, "off": False,
}
_YAML_INT_RE = re.compile(r"[-+]?(?:0|[1-9][0-9_]*)")
_YAML_FLOAT_RE = re.compile(r"[-+]?(?:[0-9][0-9_]*)?\.[0-9_]*(?:[eE][-+][0-9]+)?")


def _strip_yaml_comment(line: str) -> str:
    """Remove a comment that starts with "#" outside of quotes."""
    quote = ""
    escaped = False
    for index, char in enumerate(line):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\" and quote == '"':
                escaped = True
            elif char == quote:
                quote = ""
        elif char in "\"'" and (index == 0 or line[index - 1] in " \t[{,:-"):
            quote = char
        elif char == "#" and (index == 0 or line[index - 1] in " \t"):
            return line[:index].rstrip()
    return line.rstrip()


def _yaml_lines(text: str) -> List[_YamlLine]:
    result = []
    for number, raw in enumerate(text.splitlines(), 1):
        content = _strip_yaml_comment(raw)
        if not content.strip() or content.strip() in ("---", "..."):
            continue
        leading = content[: len(content) - len(content.lstrip())]
        if "\t" in leading:
            raise ConfigError(f"line {number}: use spaces, not tabs, for indentation")
        result.append(_YamlLine(number, len(leading), content.strip()))
    return result


def _is_yaml_item(content: str) -> bool:
    return content == "-" or content.startswith("- ")


def _split_flow(text: str, number: int) -> List[str]:
    """Split the inside of an inline list or mapping on top-level commas."""
    parts, buffer, depth, quote = [], [], 0, ""
    for char in text:
        if quote:
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char in "[{":
            depth += 1
        elif char in "]}":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append("".join(buffer))
            buffer = []
            continue
        buffer.append(char)
    if quote or depth:
        raise ConfigError(f"line {number}: the inline list is not closed")
    parts.append("".join(buffer))
    return [part.strip() for part in parts if part.strip()]


def _unquote_double(body: str) -> str:
    escapes = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "/": "/"}
    return re.sub(r"\\(.)", lambda m: escapes.get(m.group(1), "\\" + m.group(1)), body)


def _yaml_scalar(text: str, number: int) -> Any:
    text = text.strip()
    if not text:
        return None
    if text[0] == "[":
        if not text.endswith("]"):
            raise ConfigError(f"line {number}: an inline list must end with ']'")
        return [_yaml_scalar(part, number) for part in _split_flow(text[1:-1], number)]
    if text[0] == "{":
        if not text.endswith("}"):
            raise ConfigError(f"line {number}: an inline mapping must end with '}}'")
        mapping = {}
        for part in _split_flow(text[1:-1], number):
            match = _YAML_KEY_RE.match(part)
            if not match:
                raise ConfigError(f"line {number}: expected 'key: value' in '{part}'")
            mapping[_yaml_key(match.group("key"))] = _yaml_scalar(match.group("rest") or "", number)
        return mapping
    if text[0] == '"':
        match = re.fullmatch(r'"((?:[^"\\]|\\.)*)"', text)
        if not match:
            raise ConfigError(f"line {number}: the quoted string is not closed")
        return _unquote_double(match.group(1))
    if text[0] == "'":
        match = re.fullmatch(r"'((?:[^']|'')*)'", text)
        if not match:
            raise ConfigError(f"line {number}: the quoted string is not closed")
        return match.group(1).replace("''", "'")
    return _yaml_plain(text)


def _yaml_plain(text: str) -> Any:
    if text in ("~", "null", "Null", "NULL"):
        return None
    if text.lower() in _YAML_BOOL and text in (text.lower(), text.capitalize(), text.upper()):
        return _YAML_BOOL[text.lower()]
    if _YAML_INT_RE.fullmatch(text):
        return int(text.replace("_", ""))
    if _YAML_FLOAT_RE.fullmatch(text) and re.search(r"\d", text):
        return float(text.replace("_", ""))
    return text


def _yaml_key(raw: str) -> str:
    value = _yaml_scalar(raw, 0)
    return str(value) if not isinstance(value, str) else value


class _YamlParser:
    """Recursive reader for block mappings and block lists."""

    def __init__(self, lines: List[_YamlLine]) -> None:
        self.lines = lines
        self.pos = 0

    def parse_block(self, indent: int) -> Any:
        if _is_yaml_item(self.lines[self.pos].content):
            return self.parse_list(indent)
        return self.parse_mapping(indent)

    def parse_mapping(self, indent: int) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        while self.pos < len(self.lines):
            line = self.lines[self.pos]
            if line.indent < indent or (line.indent == indent and _is_yaml_item(line.content)):
                break
            if line.indent > indent:
                raise ConfigError(f"line {line.number}: unexpected indentation")
            match = _YAML_KEY_RE.match(line.content)
            if not match:
                raise ConfigError(f"line {line.number}: expected 'key: value'")
            key = _yaml_key(match.group("key"))
            rest = match.group("rest")
            self.pos += 1
            if rest:
                result[key] = _yaml_scalar(rest, line.number)
            else:
                result[key] = self._nested_value(indent)
        return result

    def _nested_value(self, indent: int) -> Any:
        if self.pos >= len(self.lines):
            return None
        following = self.lines[self.pos]
        if following.indent > indent:
            return self.parse_block(following.indent)
        if following.indent == indent and _is_yaml_item(following.content):
            return self.parse_list(indent)
        return None

    def parse_list(self, indent: int) -> List[Any]:
        items: List[Any] = []
        while self.pos < len(self.lines):
            line = self.lines[self.pos]
            if line.indent != indent or not _is_yaml_item(line.content):
                if line.indent > indent:
                    raise ConfigError(f"line {line.number}: unexpected indentation")
                break
            body = line.content[1:]
            content = body.lstrip()
            column = indent + 1 + len(body) - len(content)
            if not content:
                self.pos += 1
                following = self.lines[self.pos] if self.pos < len(self.lines) else None
                items.append(
                    self.parse_block(following.indent)
                    if following is not None and following.indent > indent
                    else None
                )
            elif _is_yaml_item(content) or _YAML_KEY_RE.match(content):
                # "- key: value": the mapping starts at the column of the key.
                self.lines[self.pos] = _YamlLine(line.number, column, content)
                items.append(self.parse_block(column))
            else:
                items.append(_yaml_scalar(content, line.number))
                self.pos += 1
        return items


def load_yaml_subset(text: str) -> Any:
    """Read the YAML subset of the configuration format.

    The subset has comments, scalars (strings, numbers, booleans), nested
    mappings, block lists, lists of mappings, and inline lists.
    """
    lines = _yaml_lines(text)
    if not lines:
        return None
    parser = _YamlParser(lines)
    value = parser.parse_block(lines[0].indent)
    if parser.pos < len(lines):
        raise ConfigError(f"line {lines[parser.pos].number}: unexpected indentation")
    return value


def load_yaml(text: str) -> Any:
    """Read YAML with PyYAML if it is installed, or with the subset reader."""
    if _pyyaml is not None:
        try:
            return _pyyaml.safe_load(text)
        except _pyyaml.YAMLError as error:  # pragma: no cover - depends on PyYAML
            raise ConfigError(str(error)) from error
    return load_yaml_subset(text)


# ---------------------------------------------------------------------------
# Language codes
# ---------------------------------------------------------------------------

_LANGUAGE_CODE_RE = re.compile(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{1,8})*")


def normalize_language(value: str) -> Optional[str]:
    """Return a normalized language code, "auto", "other", or None.

    The code is BCP 47-like: "ru", "de", "pt-BR", "zh-Hant". The primary
    subtag is in lowercase, a region is in capital letters, and a script has
    a capital first letter. "_" is the same as "-".
    """
    text = value.strip().replace("_", "-")
    if text.lower() in (AUTO, OTHER):
        return text.lower()
    if not _LANGUAGE_CODE_RE.fullmatch(text):
        return None
    parts = text.split("-")
    out = [parts[0].lower()]
    for part in parts[1:]:
        if len(part) == 2 and part.isalpha():
            out.append(part.upper())
        elif len(part) == 4 and part.isalpha():
            out.append(part.title())
        else:
            out.append(part.lower())
    return "-".join(out)


def primary_subtag(code: str) -> str:
    return code.split("-", 1)[0].lower()


def is_english(code: str) -> bool:
    """True for "en" and for a regional variant such as "en-GB"."""
    return primary_subtag(code) == ENGLISH


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class Config:
    """The project configuration (.controlled-language.yml)."""

    path: Optional[Path] = None
    level: Optional[int] = None
    spelling: str = "us"
    include: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)
    overrides: List[Tuple[str, int]] = field(default_factory=list)
    technical_nouns: List[str] = field(default_factory=list)
    technical_verbs: List[str] = field(default_factory=list)
    preferred_terms: List[Tuple[str, List[str]]] = field(default_factory=list)
    avoid_words: List[Tuple[str, Optional[str]]] = field(default_factory=list)
    keep_verbatim: List[str] = field(default_factory=list)
    language: str = AUTO
    non_english: str = "apply"

    @property
    def base_dir(self) -> Optional[Path]:
        return self.path.resolve().parent if self.path else None


def _parse_level(value: Any, where: str) -> int:
    if isinstance(value, bool) or str(value).strip() not in ("1", "2", "3"):
        raise ConfigError(f"{where} must be 1, 2, or 3")
    return int(str(value).strip())


def _string_list(value: Any, where: str) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list) or not all(isinstance(item, (str, int, float)) for item in value):
        raise ConfigError(f"{where} must be a list of strings")
    return [str(item) for item in value]


def _mapping_list(value: Any, where: str) -> List[Dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ConfigError(f"{where} must be a list of mappings")
    return value


def config_from_mapping(data: Any, path: Optional[Path] = None) -> Config:
    """Make a Config from the data of a configuration file."""
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ConfigError("the configuration must be a mapping of keys and values")
    config = Config(path=path)
    if data.get("level") is not None:
        config.level = _parse_level(data["level"], "level")
    config.spelling = str(data.get("spelling") or "us").strip().lower()
    if config.spelling not in ("us", "uk"):
        raise ConfigError("spelling must be us or uk")
    config.include = _string_list(data.get("include"), "include")
    config.exclude = _string_list(data.get("exclude"), "exclude")
    for item in _mapping_list(data.get("overrides"), "overrides"):
        if "path" not in item or "level" not in item:
            raise ConfigError("each item in overrides must have path and level")
        config.overrides.append((str(item["path"]), _parse_level(item["level"], "overrides level")))
    glossary = data.get("glossary") or {}
    if not isinstance(glossary, dict):
        raise ConfigError("glossary must be a mapping")
    config.technical_nouns = _string_list(glossary.get("technical_nouns"), "technical_nouns")
    config.technical_verbs = _string_list(glossary.get("technical_verbs"), "technical_verbs")
    for item in _mapping_list(glossary.get("preferred_terms"), "preferred_terms"):
        if "use" not in item:
            raise ConfigError("each item in preferred_terms must have use")
        config.preferred_terms.append((str(item["use"]), _string_list(item.get("not"), "not")))
    for item in data.get("avoid_words") or []:
        if isinstance(item, str):
            config.avoid_words.append((item, None))
        elif isinstance(item, dict) and "word" in item:
            use = item.get("use")
            config.avoid_words.append((str(item["word"]), None if use is None else str(use)))
        else:
            raise ConfigError("each item in avoid_words must have word and use")
    config.keep_verbatim = _string_list(data.get("keep_verbatim"), "keep_verbatim")
    language = data.get("language")
    if language is False:  # YAML 1.1 reads "no" (Norwegian) as false.
        language = "no"
    if language is not None:
        code = normalize_language(str(language)) if not isinstance(language, bool) else None
        if code is None:
            raise ConfigError("language must be auto or a language code, for example en, ru, or pt-BR")
        config.language = code
    non_english = data.get("non_english", "apply")
    if non_english is False:  # YAML 1.1 reads "off" as false.
        non_english = "off"
    config.non_english = str(non_english).strip().lower()
    if config.non_english == "neutral":  # The old name of "apply".
        config.non_english = "apply"
    if config.non_english not in ("apply", "off"):
        raise ConfigError("non_english must be apply or off")
    return config


def load_config(path: Path) -> Config:
    """Read and validate a configuration file."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as error:
        raise ConfigError(f"cannot read {path}: {error.strerror}") from error
    try:
        return config_from_mapping(load_yaml(text), path)
    except ConfigError as error:
        raise ConfigError(f"{path}: {error}") from error


def find_config(start: Path) -> Optional[Path]:
    """Find .controlled-language.yml in the start folder or a parent folder."""
    folder = start.resolve()
    for candidate in [folder, *folder.parents]:
        path = candidate / CONFIG_NAME
        if path.is_file():
            return path
    return None


# ---------------------------------------------------------------------------
# Glob patterns
# ---------------------------------------------------------------------------


def glob_to_regex(pattern: str) -> "re.Pattern[str]":
    """Convert a glob pattern to a regular expression. "**" matches folders."""
    out, index = [], 0
    while index < len(pattern):
        char = pattern[index]
        if pattern.startswith("**/", index):
            out.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            out.append(".*")
            index += 2
        elif char == "*":
            out.append("[^/]*")
            index += 1
        elif char == "?":
            out.append("[^/]")
            index += 1
        elif char == "[" and "]" in pattern[index + 1:]:
            end = pattern.index("]", index + 1)
            body = pattern[index + 1:end]
            if body.startswith("!"):
                body = "^" + body[1:]
            out.append("[" + body.replace("\\", "\\\\") + "]")
            index = end + 1
        else:
            out.append(re.escape(char))
            index += 1
    return re.compile("".join(out) + r"\Z")


def path_matches(relative: str, pattern: str) -> bool:
    """Match a relative path (with "/") against a glob pattern.

    A pattern without "/" also matches the file name in any folder, as in
    .gitignore. A pattern that ends with "/" matches all files in the folder.
    """
    pattern = pattern.strip()
    if pattern.startswith("./"):
        pattern = pattern[2:]
    anchored = pattern.startswith("/")
    pattern = pattern.lstrip("/")
    if pattern.endswith("/"):
        pattern += "**"
    regex = glob_to_regex(pattern)
    if regex.match(relative):
        return True
    return "/" not in pattern and not anchored and bool(regex.match(relative.rsplit("/", 1)[-1]))


def relative_to_config(path: Optional[Path], config: Config) -> Optional[str]:
    """Return the path relative to the folder of the config file, or None."""
    if path is None or config.base_dir is None:
        return None
    try:
        relative = os.path.relpath(str(path.resolve()), str(config.base_dir))
    except ValueError:  # Another drive on Windows.
        return None
    relative = relative.replace(os.sep, "/")
    return None if relative == ".." or relative.startswith("../") else relative


# ---------------------------------------------------------------------------
# Word list
# ---------------------------------------------------------------------------

WORD_TABLE_HEADER = ("avoid", "use instead", "from level", "lint", "note")


@dataclass
class WordChoice:
    """One row of the word list."""

    phrases: List[str]
    use: str
    from_level: int
    lint: bool
    note: str
    rule: str
    inflect: bool = True  # Add the English -s, -ed, -ing forms to single words.

    @property
    def conditional(self) -> bool:
        """True if the note limits the row ("Only as a verb", "Keep ... if")."""
        return bool(re.search(r"\b(?:Only|Keep)\b", self.note))

    @property
    def verb_only(self) -> bool:
        return "only as a verb" in self.note.lower()


def split_table_row(row: str) -> List[str]:
    """Split a Markdown table row into cells. Pipes in code do not split."""
    text = row.strip()
    cells, buffer, in_code, index = [], [], False, 0
    while index < len(text):
        char = text[index]
        if char == "\\" and text[index + 1:index + 2] == "|":
            buffer.append("|")
            index += 2
            continue
        if char == "`":
            in_code = not in_code
        if char == "|" and not in_code:
            cells.append("".join(buffer))
            buffer = []
        else:
            buffer.append(char)
        index += 1
    cells.append("".join(buffer))
    if text.startswith("|"):
        cells = cells[1:]
    if text.endswith("|") and cells:
        cells = cells[:-1]
    return [cell.strip() for cell in cells]


def is_table_separator(line: str) -> bool:
    text = line.strip()
    return "|" in text and "-" in text and set(text) <= set("|:- \t")


def _clean_phrase(phrase: str) -> str:
    """Remove quotes, backticks, and bold marks around an Avoid item.

    A single "*" at the end stays: it makes the item a prefix ("осуществ*").
    """
    text = phrase.strip().strip("`\"“”").strip()
    if text.startswith("**") and text.endswith("**"):
        text = text.strip("*").strip()
    elif text.endswith("*") and not text.endswith("**") and not text.startswith("*"):
        text = text.rstrip("*").strip("`\"“”").strip() + "*"
    else:
        text = text.strip("*").strip()
    return text if text != "*" else ""


def split_avoid_cell(cell: str) -> List[str]:
    """Split the Avoid cell on commas. A phrase in double quotes is one item.

    '"в связи с тем, что", в связи с тем что' gives two items.
    """
    items: List[str] = []
    index = 0
    while index < len(cell):
        while index < len(cell) and cell[index] in " \t,":
            index += 1
        if index >= len(cell):
            break
        char = cell[index]
        closing = {'"': '"', "“": "”"}.get(char)
        if closing and closing in cell[index + 1:]:
            end = cell.index(closing, index + 1)
            items.append(cell[index + 1:end])
            comma = cell.find(",", end + 1)
            index = len(cell) if comma < 0 else comma + 1
            continue
        comma = cell.find(",", index)
        end = len(cell) if comma < 0 else comma
        items.append(cell[index:end])
        index = end + 1
    return [phrase for phrase in (_clean_phrase(item) for item in items) if phrase]


def _find_table(lines: Sequence[str], match_header: Any, start: int = 0, stop: Optional[int] = None) -> Optional[int]:
    """Return the index of the first table row after the header, or None."""
    for index in range(start, len(lines) if stop is None else stop):
        line = lines[index]
        if line.strip().startswith("|") and match_header(tuple(cell.lower() for cell in split_table_row(line))):
            return index + 1
    return None


_RULE_ID_RE = re.compile(r"\bRule\s+([A-Z]{1,3}\d+)\b")


def parse_word_choices(text: str, english: bool = True, required: bool = True) -> List[WordChoice]:
    """Read a word table. Return all rows (also Lint = no).

    The table has the columns Avoid | Use instead | From level | Lint | Note.
    The rule ID comes from "Rule XX" in the note. Without it, the English list
    uses W5 for From level 3 and W2 for the other rows. A language file uses
    W2. Only the English list gets the English inflections.
    """
    lines = text.splitlines()
    start = _find_table(lines, lambda cells: cells == WORD_TABLE_HEADER)
    if start is None:
        if not required:
            return []
        raise WordListError(
            "the word list has no table with the columns Avoid | Use instead | From level | Lint | Note"
        )
    rows = []
    for number, line in enumerate(lines[start:], start + 1):
        if not line.strip().startswith("|"):
            break
        if is_table_separator(line):
            continue
        cells = split_table_row(line)
        if len(cells) != 5:
            raise WordListError(f"line {number}: the row must have 5 columns")
        avoid, use, from_level, lint, note = cells
        if from_level not in ("1", "2", "3"):
            raise WordListError(f"line {number}: 'From level' must be 1, 2, or 3")
        if lint.lower() not in ("yes", "no"):
            raise WordListError(f"line {number}: 'Lint' must be yes or no")
        level = int(from_level)
        rule_match = _RULE_ID_RE.search(note)
        if english:
            rule = "W5" if level == 3 else (rule_match.group(1) if rule_match else "W2")
            if rule not in RULE_MATRIX:
                raise WordListError(f"line {number}: unknown rule {rule}")
        else:
            rule = rule_match.group(1) if rule_match else "W2"
        phrases = split_avoid_cell(avoid)
        rows.append(WordChoice(phrases, use, level, lint.lower() == "yes", note, rule, inflect=english))
    return rows


def load_word_choices(path: Path) -> List[WordChoice]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as error:
        raise WordListError(f"cannot read the word list {path}: {error.strerror}") from error
    try:
        return parse_word_choices(text)
    except WordListError as error:
        raise WordListError(f"{path}: {error}") from error


# ---------------------------------------------------------------------------
# Language files (references/languages/<code>.md)
# ---------------------------------------------------------------------------

_LABEL_KIND_OF_SIGNAL = {"note": "note", "warning": "warning", "danger": "warning", "caution": "caution"}


def _section(lines: Sequence[str], title: str) -> Tuple[int, int]:
    """Return the (start, end) line indexes of a "## title" section."""
    start = next(
        (i + 1 for i, line in enumerate(lines) if re.match(r"^##\s+%s\s*$" % re.escape(title), line.strip(), re.I)),
        None,
    )
    if start is None:
        return 0, 0
    end = next((i for i in range(start, len(lines)) if re.match(r"^#{1,2}\s", lines[i])), len(lines))
    return start, end


def _table_rows(lines: Sequence[str], start: int) -> List[List[str]]:
    rows = []
    for line in lines[start:]:
        if not line.strip().startswith("|"):
            break
        if not is_table_separator(line):
            rows.append(split_table_row(line))
    return rows


def parse_signal_words(text: str) -> Dict[str, List[str]]:
    """Read the "## Signal words" table: English | <Language>.

    Return the localized words for each English signal word, for example
    {"warning": ["ВНИМАНИЕ"], "note": ["ПРИМЕЧАНИЕ"]}. A cell can give more
    than one word, separated by a comma or "/".
    """
    lines = text.splitlines()
    start, end = _section(lines, "Signal words")
    first = _find_table(lines, lambda cells: len(cells) >= 2 and cells[0] == "english", start, end)
    result: Dict[str, List[str]] = {}
    if first is None:
        return result
    for cells in _table_rows(lines, first):
        if len(cells) < 2:
            continue
        kind = cells[0].strip("*` ").lower()
        if kind not in _LABEL_KIND_OF_SIGNAL:
            continue
        words = [w.strip("*` ") for w in re.split(r"[,/]", cells[1])]
        words = [w for w in words if w and not w.startswith("<")]
        if words:
            result.setdefault(kind, []).extend(words)
    return result


def parse_language_rules(text: str) -> Dict[str, Tuple[str, str, str]]:
    """Read the "## Rules" table: ID | Rule | L1 | L2 | L3 | Universal rule.

    Return the strength of each language rule at each level.
    """
    lines = text.splitlines()

    def header(cells: Tuple[str, ...]) -> bool:
        return bool(cells) and cells[0] == "id" and all(level in cells for level in ("l1", "l2", "l3"))

    first = _find_table(lines, header)
    if first is None:
        return {}
    head = [cell.lower() for cell in split_table_row(lines[first - 1])]
    columns = [head.index(level) for level in ("l1", "l2", "l3")]
    result: Dict[str, Tuple[str, str, str]] = {}
    for cells in _table_rows(lines, first):
        if len(cells) <= max(columns) or not re.fullmatch(r"[A-Z]{1,3}\d+", cells[0].strip("` ")):
            continue
        values = []
        for column in columns:
            value = re.sub(r"\s*\(.*?\)", "", cells[column].strip().lower())
            value = {"—": OFF, "–": OFF, "-": OFF, "": OFF}.get(value, value)
            values.append(value if value in (MUST, PREFER, OFF) else PREFER)
        result[cells[0].strip("` ")] = (values[0], values[1], values[2])
    return result


def find_language_file(code: str, folder: Optional[Path]) -> Optional[Path]:
    """Find <code>.md in the folder. "pt-BR" also tries "pt.md".

    Files that start with "_" (for example _template.md) are not languages.
    """
    if folder is None or code in (AUTO, OTHER) or is_english(code):
        return None
    for name in dict.fromkeys((code, code.lower(), primary_subtag(code))):
        if name.startswith("_"):
            continue
        path = folder / f"{name}.md"
        if path.is_file():
            return path
    return None


@dataclass
class LanguageRules:
    """The rules of one language file."""

    code: str
    path: Path
    word_choices: List[WordChoice]
    strengths: Dict[str, Tuple[str, str, str]]
    signal_words: Dict[str, List[str]]

    @property
    def name(self) -> str:
        return self.path.name

    @classmethod
    def load(cls, code: str, path: Path) -> "LanguageRules":
        try:
            text = path.read_text(encoding="utf-8-sig")
        except OSError as error:
            raise WordListError(f"cannot read the language file {path}: {error.strerror}") from error
        try:
            choices = parse_word_choices(text, english=False, required=False)
        except WordListError as error:
            raise WordListError(f"{path}: {error}") from error
        return cls(code, path, choices, parse_language_rules(text), parse_signal_words(text))

    def label_regex(self) -> Optional["re.Pattern[str]"]:
        """A regex for a localized label at the start of a block."""
        words = sorted({w for ws in self.signal_words.values() for w in ws}, key=len, reverse=True)
        if not words:
            return None
        alt = "|".join(re.escape(word) for word in words)
        return re.compile(
            r"^\s*(?:(?P<b>\*\*|__)(?P<bold>%s)\s*[:.!]?\s*(?P=b)\s*[:.!—–]?"
            r"|(?P<plain>%s)\s*[:!.—–])\s*" % (alt, alt),
            re.I,
        )

    def label_kinds(self) -> Dict[str, str]:
        return {
            word.lower(): _LABEL_KIND_OF_SIGNAL[kind]
            for kind, words in self.signal_words.items() for word in words
        }

    def risk_regexes(self) -> List["re.Pattern[str]"]:
        """Regexes for a safety signal word in a note (SF2).

        The word must be in capital letters ("ВНИМАНИЕ") or have ":" or "!"
        after it ("Внимание!"). Then the common word «внимание» in "pay
        attention" does not match.
        """
        words = [w for kind in ("warning", "caution", "danger") for w in self.signal_words.get(kind, [])]
        if not words:
            return []
        alt_upper = "|".join(re.escape(word.upper()) for word in words)
        alt = "|".join(re.escape(word) for word in words)
        return [
            re.compile(r"(?<![\w-])(?:%s)(?![\w-])" % alt_upper),
            re.compile(r"(?<![\w-])(?:%s)\s*[:!]" % alt, re.I),
        ]


def inflection_list(word: str) -> List[str]:
    """Return the base, -s, -ed, and -ing forms of a word, in this order.

    A word that ends in consonant + vowel + consonant also gets the forms
    with a double consonant ("permitted", "beginning").
    """
    base = word.lower()
    if base.endswith("e"):
        return [base, base + "s", base + "d", base[:-1] + "ing"]
    if re.search(r"[^aeiou]y$", base):
        return [base, base[:-1] + "ies", base[:-1] + "ied", base + "ing"]
    if re.search(r"(?:s|x|z|ch|sh)$", base):
        return [base, base + "es", base + "ed", base + "ing"]
    forms = [base, base + "s", base + "ed", base + "ing"]
    if re.search(r"[^aeiou][aeiou][^aeiouwxy]$", base):
        forms += [base + base[-1] + "ed", base + base[-1] + "ing"]
    return forms


def inflections(word: str) -> Set[str]:
    """Return simple inflected forms of a word: -s, -es, -ed, -ing."""
    return set(inflection_list(word))


# Between two words of a phrase: white space, or a comma. The comma is
# optional in both directions: "в связи с тем, что" = "в связи с тем что".
_PHRASE_GAP = r"(?:\s*,\s*|\s+)"


def phrase_regex(phrases: Iterable[str], inflect: bool = True, suffix: str = "") -> str:
    """Make a regular expression that matches the phrases as whole words.

    A word that ends with "*" matches all words that start with it. With
    inflect=True, a single English word also matches its -s, -ed, and -ing
    forms.
    """
    bodies = set()
    for phrase in phrases:
        words = [word for word in re.split(r"\s*,\s*|\s+", phrase.strip()) if word]
        if not words:
            continue
        if inflect and len(words) == 1 and re.fullmatch(r"[a-z]+", words[0]):
            bodies |= {re.escape(form) for form in inflections(words[0])}
        else:
            parts = [
                re.escape(word[:-1]) + r"\w*" if len(word) > 1 and word.endswith("*") else re.escape(word)
                for word in words
            ]
            bodies.add(_PHRASE_GAP.join(parts) + suffix)
    ordered = sorted(bodies, key=len, reverse=True)
    return r"(?<![\w-])(?:" + "|".join(ordered) + r")(?![\w-])"


# ---------------------------------------------------------------------------
# Markdown blocks
# ---------------------------------------------------------------------------


@dataclass
class Block:
    """A unit of prose: a paragraph, a heading, a list item, or a table cell."""

    kind: str  # "paragraph", "heading", "item", or "cell"
    level: int
    lines: List[Tuple[int, str]] = field(default_factory=list)
    ordered: bool = False
    first_of_item: bool = True
    label: Optional[str] = None  # "note", "warning", "caution", or "other"

    @property
    def line(self) -> int:
        return self.lines[0][0] if self.lines else 0


_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
_ATX_RE = re.compile(r"^\s{0,3}#{1,6}(?:\s+(.*))?$")
_HR_RE = re.compile(r"^\s{0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$")
_SETEXT_RE = re.compile(r"^\s{0,3}(?:=+|-+)\s*$")
_LIST_RE = re.compile(r"^(\s*)([-*+]|\d{1,9}[.)])(?:\s+|$)")
_TASK_RE = re.compile(r"^\[[ xX]\]\s+")
_QUOTE_RE = re.compile(r"^\s{0,3}>\s?")
_LINK_DEF_RE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*\S")
_HTML_SKIP_RE = re.compile(r"^\s*<(pre|script|style|textarea)\b", re.I)
_MARKER_RE = re.compile(r"^\s*controlled-language\s*:\s*(off|on|level\s*([123]))\s*$", re.I)
_LABEL_RE = re.compile(
    r"^\s*(?:\[!(?P<alert>NOTE|TIP|IMPORTANT|WARNING|CAUTION|DANGER)\]"
    r"|(?P<b>\*\*|__)(?P<bold>note|warning|caution|danger)\s*:?\s*(?P=b)\s*:?"
    r"|(?P<plain>note|warning|caution|danger)\s*:)\s*",
    re.I,
)
_RUN_IN_HEADING_RE = re.compile(r"^(\*\*|__)([^*_\n]{1,60}?[.:])\1\s+(?=\S)")
_LABEL_KINDS = {"note": "note", "warning": "warning", "danger": "warning", "caution": "caution"}
_CODE_SPAN_RE = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)", re.S)


def split_label(content: str) -> Tuple[Optional[str], str]:
    """Find a note or safety label at the start of a block.

    Return the kind of label and the text after it. A label that a lowercase
    word follows is a mention, not a label ("**WARNING**: a risk to people").
    """
    match = _LABEL_RE.match(content)
    if not match:
        return None, content
    rest = content[match.end():]
    if rest[:1].islower():
        return None, content
    word = (match.group("alert") or match.group("bold") or match.group("plain")).lower()
    return _LABEL_KINDS.get(word, "other"), rest


def split_front_matter(lines: Sequence[str]) -> Tuple[List[str], int]:
    """Return the front matter lines and the index of the first body line."""
    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() in ("---", "..."):
                return list(lines[1:index]), index + 1
    return [], 0


def front_matter_level(lines: Sequence[str]) -> Optional[int]:
    """Read "controlled-language: N" or "controlled-language:\\n  level: N"."""
    for index, line in enumerate(lines):
        match = re.match(r"^controlled-language\s*:(.*)$", line)
        if not match:
            continue
        value = _strip_yaml_comment(match.group(1)).strip().strip("\"'")
        if value:
            if value.startswith("{"):
                inline = re.search(r"[{,]\s*level\s*:\s*[\"']?(\w+)", value)
                value = inline.group(1) if inline else ""
            return int(value) if value in ("1", "2", "3") else None
        for sub in lines[index + 1:]:
            if not sub.strip():
                continue
            if not sub[:1].isspace():
                break
            nested = re.match(r"^\s+level\s*:\s*[\"']?(\w+)[\"']?\s*(?:#.*)?$", sub)
            if nested:
                return int(nested.group(1)) if nested.group(1) in ("1", "2", "3") else None
        return None
    return None


def front_matter_language(lines: Sequence[str]) -> Optional[str]:
    """Read the language of the document from the front matter.

    The forms are "lang: ru", "language: ru", and "language: ru" under
    "controlled-language:" (also inline: "controlled-language: {language: ru}").
    The value under "controlled-language" wins. "auto" and values that are
    not language codes are ignored.
    """
    top: Optional[str] = None
    nested: Optional[str] = None
    for index, line in enumerate(lines):
        match = re.match(r"^(?:lang|language)\s*:(.*)$", line)
        if match and top is None:
            top = normalize_language(_strip_yaml_comment(match.group(1)).strip().strip("\"'"))
            continue
        match = re.match(r"^controlled-language\s*:(.*)$", line)
        if not match:
            continue
        value = _strip_yaml_comment(match.group(1)).strip()
        if value.startswith("{"):
            inline = re.search(r"[{,]\s*(?:lang|language)\s*:\s*[\"']?([\w-]+)", value)
            nested = normalize_language(inline.group(1)) if inline else None
            continue
        for sub in lines[index + 1:]:
            if not sub.strip():
                continue
            if not sub[:1].isspace():
                break
            sub_match = re.match(r"^\s+(?:lang|language)\s*:\s*[\"']?([\w-]+)[\"']?\s*(?:#.*)?$", sub)
            if sub_match:
                nested = normalize_language(sub_match.group(1))
                break
    for value in (nested, top):
        if value is not None and value != AUTO:
            return value
    return None


LabelSplitter = Any  # Callable[[str], Tuple[Optional[str], str]]


def localized_label_splitter(regex: "re.Pattern[str]", kinds: Dict[str, str]) -> LabelSplitter:
    """Make a label splitter that also finds localized labels ("ПРИМЕЧАНИЕ:")."""

    def split(content: str) -> Tuple[Optional[str], str]:
        label, rest = split_label(content)
        if label is not None:
            return label, rest
        match = regex.match(content)
        if not match:
            return None, content
        word = (match.group("bold") or match.group("plain")).lower()
        return kinds.get(word, "other"), content[match.end():]

    return split


class BlockParser:
    """Split Markdown into prose blocks. Keep the original line numbers.

    The parser skips fenced and indented code, HTML comments, front matter,
    link definitions, and the text between "off" and "on" markers. It reads
    the level markers.
    """

    def __init__(self, level: int, lock_level: bool = False, label_splitter: Optional[LabelSplitter] = None) -> None:
        self.level = level
        self.lock_level = lock_level
        self.split_label = label_splitter or split_label
        self.blocks: List[Block] = []
        self.open: Optional[Block] = None
        self.list_indent: Optional[int] = None
        self.list_ordered = False
        self.fence: Optional[Tuple[str, int]] = None
        self.comment: Optional[List[str]] = None
        self.html_skip: Optional[str] = None
        self.indented_code = False
        self.in_table = False
        self.in_quote = False
        self.off = False

    def parse(self, lines: Sequence[str], first_line: int = 1) -> List[Block]:
        for offset, raw in enumerate(lines):
            self._line(first_line + offset, raw.expandtabs(4))
        self._close_all()
        return self.blocks

    # -- line handling ------------------------------------------------------

    def _line(self, number: int, line: str) -> None:
        if self.comment is not None:
            end = line.find("-->")
            if end < 0:
                self.comment.append(line)
                return
            self.comment.append(line[:end])
            self._marker(" ".join(self.comment))
            self.comment = None
            line = line[end + 3:]
        line = self._strip_quote(line)
        if self.fence is not None:
            closing = re.match(r"^\s*(`{3,}|~{3,})\s*$", line)
            if closing and closing.group(1)[0] == self.fence[0] and len(closing.group(1)) >= self.fence[1]:
                self.fence = None
            return
        if self.html_skip is not None:
            if re.search(r"</%s\s*>" % self.html_skip, line, re.I):
                self.html_skip = None
            return
        fence = _FENCE_RE.match(line)
        if fence:
            self._close_text()
            self.fence = (fence.group(1)[0], len(fence.group(1)))
            return
        line = self._strip_comments(line)
        if self.off:
            self._close_all()
            return
        if not line.strip():
            self._blank()
            return
        self._content_line(number, line)

    def _strip_quote(self, line: str) -> str:
        quoted = False
        match = _QUOTE_RE.match(line)
        while match:
            quoted = True
            line = line[match.end():]
            match = _QUOTE_RE.match(line)
        if quoted != self.in_quote and self.fence is None:
            self._close_text()
            self.in_quote = quoted
        return line

    def _strip_comments(self, line: str) -> str:
        if "<!--" not in line:
            return line
        code = [(m.start(), m.end()) for m in _CODE_SPAN_RE.finditer(line)]
        out, pos = [], 0
        while True:
            start = line.find("<!--", pos)
            while start >= 0 and any(a <= start < b for a, b in code):
                start = line.find("<!--", start + 4)
            if start < 0:
                out.append(line[pos:])
                break
            out.append(line[pos:start])
            end = line.find("-->", start + 4)
            if end < 0:
                self.comment = [line[start + 4:]]
                break
            self._marker(line[start + 4:end])
            pos = end + 3
        return "".join(out)

    def _marker(self, content: str) -> None:
        match = _MARKER_RE.match(content)
        if not match:
            return
        value = match.group(1).lower()
        if value == "off":
            self.off = True
        elif value == "on":
            self.off = False
        elif not self.lock_level:
            self.level = int(match.group(2))

    def _content_line(self, number: int, line: str) -> None:
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if self.indented_code:
            if indent >= 4:
                return
            self.indented_code = False
        if indent >= 4 and self.open is None and self.list_indent is None:
            self.indented_code = True
            return
        skip = _HTML_SKIP_RE.match(line)
        if skip:
            self._close_text()
            if not re.search(r"</%s\s*>" % skip.group(1), line, re.I):
                self.html_skip = skip.group(1).lower()
            return
        if _LINK_DEF_RE.match(line):
            self._close_text()
            return
        if self._heading(number, line):
            return
        if self._table(number, stripped):
            return
        item = _LIST_RE.match(line)
        if item:
            self._list_item(number, line, item)
            return
        if self.open is not None:
            self.open.lines.append((number, stripped))
        elif self.list_indent is not None and indent >= 2:
            self._open_block(Block("item", self.level, ordered=self.list_ordered, first_of_item=False), number, stripped)
        else:
            self.list_indent = None
            self._open_block(Block("paragraph", self.level), number, stripped)

    def _heading(self, number: int, line: str) -> bool:
        atx = _ATX_RE.match(line)
        if atx:
            self._close_all()
            text = re.sub(r"\s+#+\s*$", "", atx.group(1) or "").strip()
            if text:
                self.blocks.append(Block("heading", self.level, [(number, text)]))
            return True
        if self.open is not None and self.open.kind == "paragraph" and _SETEXT_RE.match(line):
            self.open.kind = "heading"
            self._close_all()
            return True
        if _HR_RE.match(line):
            self._close_all()
            return True
        return False

    def _table(self, number: int, stripped: str) -> bool:
        if is_table_separator(stripped):
            header = None
            if self.open is not None and self.open.kind == "paragraph" and "|" in self.open.lines[-1][1]:
                header = self.open.lines.pop()
            self._close_text()
            if header is not None:
                self._add_cells(*header)
            self.in_table = True
            return True
        if stripped.startswith("|") or (self.in_table and "|" in stripped):
            self._close_text()
            self.in_table = True
            self._add_cells(number, stripped)
            return True
        self.in_table = False
        return False

    def _list_item(self, number: int, line: str, item: "re.Match[str]") -> None:
        self._close_text()
        marker = item.group(2)
        content = line[item.end():]
        self.list_indent = item.end() if content.strip() else len(item.group(1)) + len(marker) + 1
        self.list_ordered = marker[0].isdigit()
        block = Block("item", self.level, ordered=self.list_ordered)
        self._open_block(block, number, _TASK_RE.sub("", content.strip()))

    # -- block handling -----------------------------------------------------

    def _open_block(self, block: Block, number: int, content: str) -> None:
        block.label, content = self.split_label(content)
        if block.label is None:
            run_in = _RUN_IN_HEADING_RE.match(content)
            if run_in and len(run_in.group(2).split()) <= 6:
                # "**Translations.** English is ...": the bold part is a heading.
                self.blocks.append(Block("heading", self.level, [(number, run_in.group(2))]))
                content = content[run_in.end():]
        block.lines.append((number, content))
        self.open = block

    def _add_cells(self, number: int, row: str) -> None:
        for cell in split_table_row(row):
            if cell.strip():
                self.blocks.append(Block("cell", self.level, [(number, cell.strip())]))

    def _close_text(self) -> None:
        if self.open is not None and any(text.strip() for _, text in self.open.lines):
            self.blocks.append(self.open)
        self.open = None

    def _blank(self) -> None:
        self._close_text()
        self.in_table = False

    def _close_all(self) -> None:
        self._close_text()
        self.list_indent = None
        self.in_table = False


# ---------------------------------------------------------------------------
# Inline Markdown: placeholders and protected spans
# ---------------------------------------------------------------------------

PH_BASE = 0xF0000  # Placeholders are characters in a private-use plane.
PH_RE = re.compile("[\U000F0000-\U000FFFFD]")
LABEL_OPEN, LABEL_CLOSE = "", ""
LABEL, TERM = "label", "term"  # Kinds of protected spans.

_AUTOLINK_RE = re.compile(r"<(?:https?|ftp|mailto):[^\s<>]+>", re.I)
_ESCAPE_RE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!|<>~])")
_IMAGE_RE = re.compile(r"!\[([^\[\]]*)\]\((?:[^()\n]|\([^()\n]*\))*\)")
_LINK_RE = re.compile(r"\[([^\[\]]*)\]\(((?:[^()\n]|\([^()\n]*\))*)\)")
_REF_LINK_RE = re.compile(r"\[([^\[\]]+)\]\[[^\[\]]*\]")
_FOOTNOTE_RE = re.compile(r"\[\^[^\]\s]+\]")
_HTML_TAG_RE = re.compile(r"</?([A-Za-z][A-Za-z0-9-]*)(?:\s[^<>]*)?/?>")
_BOLD_RE = re.compile(r"(?<![\w*\\/])(\*\*|__)(?=\S)(.+?)(?<=\S)\1(?![\w*])", re.S)
_ITALIC_STAR_RE = re.compile(r"(?<![\w*\\/])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![\w*])", re.S)
_ITALIC_UNDERSCORE_RE = re.compile(r"(?<![\w\\])_(?=[^\s_])(.+?)(?<=[^\s_])_(?!\w)", re.S)
_STRIKE_RE = re.compile(r"~~(?=\S)(.+?)(?<=\S)~~", re.S)
_URL_RE = re.compile(r"\b(?:https?|ftp)://[^\s<>\"'`]+|\bwww\.[^\s<>\"'`]+", re.I)
_EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
_PATH_RE = re.compile(r"(?<![\w.~$%{}@+=#:\\/-])[\w.~$%{}@+=#:-]*[/\\][\w.~$%{}@+=#:/\\*-]*")
_DOTTED_RE = re.compile(r"(?<![\w.@-])(?=[\w-]*[A-Za-z])[\w-]+(?:\.[\w-]+)+")
_IDENT_RE = re.compile(r"(?<![\w.-])(?=\w*[A-Za-z])\w*_\w*")
_QUOTED_RE = re.compile(r"[\"“«„]([^\"“”«»„]{1,80}?)[\"”»“]")
HTML_TAGS = _words("""
    a abbr article aside b big blockquote br button caption center cite code
    col dd del details dfn div dl dt em figcaption figure font footer h1 h2 h3
    h4 h5 h6 header hr i img input ins kbd label li main mark nav ol p picture
    q s samp section small source span strong sub summary sup table tbody td
    tfoot th thead tr tt u ul var video wbr
""")


@dataclass
class Prose:
    """The plain text of a block, with placeholders and protected spans.

    Code, URLs, paths, and e-mail addresses become placeholder characters.
    Each placeholder counts as one word and word rules do not apply to it.
    UI labels, short quotations, and glossary terms are protected spans.
    """

    text: str
    originals: List[str]
    spans: List[Tuple[int, int, str]]
    first_line: int

    def line_at(self, offset: int) -> int:
        return self.first_line + self.text.count("\n", 0, offset)

    def restore(self, start: int, end: int) -> str:
        """Return the text with the original code, URLs, and paths."""
        part = PH_RE.sub(lambda m: self.originals[ord(m.group()) - PH_BASE], self.text[start:end])
        return re.sub(r"\s+", " ", part)

    def protected(self, start: int, end: int, kinds: Tuple[str, ...] = (LABEL, TERM)) -> bool:
        return any(a < end and start < b for a, b, kind in self.spans if kind in kinds)

    def span_at(self, offset: int) -> Optional[int]:
        for index, (a, b, _) in enumerate(self.spans):
            if a <= offset < b:
                return index
        return None


def _trim_trailing(token: str, chars: str = ".,;:!?)]}'\"*") -> Tuple[str, str]:
    end = len(token)
    while end > 0 and token[end - 1] in chars:
        if token[end - 1] == ")" and token[:end].count("(") >= token[:end].count(")"):
            break
        end -= 1
    return token[:end], token[end:]


def _is_ui_label(content: str) -> bool:
    """Bold text with 1 to 5 words that starts with a capital letter."""
    words = [m.group() for m in TOKEN_RE.finditer(content)]
    first = content.lstrip()[:1]
    return (
        1 <= len(words) <= 5
        and (first.isupper() or first.isdigit())
        and not re.search(r"[.!?;]", content)
    )


class InlineCleaner:
    """Convert the Markdown of a block to plain text for the checks."""

    def __init__(self, glossary_regex: Optional["re.Pattern[str]"] = None) -> None:
        self.glossary_regex = glossary_regex

    def clean(self, lines: Sequence[Tuple[int, str]]) -> Prose:
        originals: List[str] = []

        def placeholder(original: str, text: Optional[str] = None) -> str:
            originals.append(original)
            source = original if text is None else text
            return chr(PH_BASE + len(originals) - 1) + "\n" * source.count("\n")

        def keep_lines(match: "re.Match[str]", replacement: str) -> str:
            missing = match.group(0).count("\n") - replacement.count("\n")
            return replacement + "\n" * max(missing, 0)

        def html_tag(match: "re.Match[str]") -> str:
            if match.group(1).lower() in HTML_TAGS:
                return keep_lines(match, "")
            return placeholder(match.group(0))

        def link(match: "re.Match[str]") -> str:
            label, target = match.group(1).strip(), match.group(2).strip().split(" ")[0]
            if label and label in (target, target.rstrip("/").rsplit("/", 1)[-1]):
                return placeholder(label)  # A file name or a URL: "[NOTICE](NOTICE)".
            return keep_lines(match, match.group(1))

        def bold(match: "re.Match[str]") -> str:
            content = match.group(2)
            return LABEL_OPEN + content + LABEL_CLOSE if _is_ui_label(content) else content

        def trimmed(match: "re.Match[str]", chars: str = ".,;:!?)]}'\"*") -> str:
            token, tail = _trim_trailing(match.group(0), chars)
            return (placeholder(token) if token else "") + tail

        def path(match: "re.Match[str]") -> str:
            if not re.search(r"[A-Za-z0-9]", match.group(0)):
                return match.group(0)
            return trimmed(match, ".,;:!?)]}'\"")

        def dotted(match: "re.Match[str]") -> str:
            parts = match.group(0).split(".")
            if all(len(part) <= 1 for part in parts):  # "e.g", "i.e", "a.m"
                return match.group(0)
            return placeholder(match.group(0))

        text = "\n".join(content for _, content in lines)
        text = _CODE_SPAN_RE.sub(lambda m: placeholder(m.group(0)), text)
        text = _AUTOLINK_RE.sub(lambda m: placeholder(m.group(0)), text)
        text = _ESCAPE_RE.sub(lambda m: m.group(1), text)
        text = _IMAGE_RE.sub(lambda m: keep_lines(m, m.group(1)), text)
        text = _LINK_RE.sub(link, text)
        text = _REF_LINK_RE.sub(lambda m: keep_lines(m, m.group(1)), text)
        text = _FOOTNOTE_RE.sub("", text)
        text = _HTML_TAG_RE.sub(html_tag, text)
        text = html.unescape(text)
        text = _BOLD_RE.sub(bold, text)
        text = _ITALIC_STAR_RE.sub(lambda m: m.group(1), text)
        text = _ITALIC_UNDERSCORE_RE.sub(lambda m: m.group(1), text)
        text = _STRIKE_RE.sub(lambda m: m.group(1), text)
        text = _URL_RE.sub(trimmed, text)
        text = _EMAIL_RE.sub(lambda m: placeholder(m.group(0)), text)
        text = _PATH_RE.sub(path, text)
        text = _DOTTED_RE.sub(dotted, text)
        text = _IDENT_RE.sub(lambda m: placeholder(m.group(0)), text)
        text, spans = self._label_spans(text)
        spans += self._quoted_spans(text, spans)
        spans += self._glossary_spans(text, spans)
        spans.sort()
        first_line = lines[0][0] if lines else 0
        return Prose(text, originals, spans, first_line)

    @staticmethod
    def _label_spans(text: str) -> Tuple[str, List[Tuple[int, int, str]]]:
        out: List[str] = []
        spans: List[Tuple[int, int, str]] = []
        start = None
        length = 0
        for char in text:
            if char == LABEL_OPEN:
                start = length
            elif char == LABEL_CLOSE:
                if start is not None:
                    spans.append((start, length, LABEL))
                start = None
            else:
                out.append(char)
                length += 1
        return "".join(out), spans

    @staticmethod
    def _quoted_spans(text: str, existing: List[Tuple[int, int, str]]) -> List[Tuple[int, int, str]]:
        """Short quotations are mentions or UI labels: '"should"', '"Save"'."""
        spans = []
        for match in _QUOTED_RE.finditer(text):
            content = match.group(1)
            words = TOKEN_RE.findall(content)
            if not 1 <= len(words) <= 4 or re.search(r"[!?;]", content):
                continue
            if re.search(r"\.(?:\s|$)", content) and len(words) > 1:
                continue
            if not any(a < match.end() and match.start() < b for a, b, _ in existing):
                spans.append((match.start(), match.end(), LABEL))
        return spans

    def _glossary_spans(self, text: str, existing: List[Tuple[int, int, str]]) -> List[Tuple[int, int, str]]:
        if self.glossary_regex is None:
            return []
        spans = []
        for match in self.glossary_regex.finditer(text):
            if not any(a < match.end() and match.start() < b for a, b, _ in existing):
                spans.append((match.start(), match.end(), TERM))
        return spans


# ---------------------------------------------------------------------------
# Sentences, tokens, and word count
# ---------------------------------------------------------------------------

TOKEN_RE = re.compile(
    r"(?P<ph>[\U000F0000-\U000FFFFD])"
    r"|(?P<num>\d+(?:[.,:]\d+)*%?)(?![^\W\d_])"
    r"|(?P<word>[^\W_](?:[^\W_]|['’](?=[^\W\d_])|-(?=[^\W_]))*)"
)
_SENTENCE_END_RE = re.compile(r"[.!?…]+[\"'”’)\]]*(?=\s|$)|[。！？]+")
_NO_SPLIT_AFTER = {"e.g", "i.e", "vs", "cf", "approx", "mr", "mrs", "ms", "dr", "jr", "sr", "st", "al", "inc", "ltd"}
_NO_SPLIT_BEFORE_NUMBER = {"no", "nos", "fig", "figs", "p", "pp", "vol", "ch", "sec", "eq"}


@dataclass
class Token:
    text: str
    start: int
    end: int
    kind: str  # "ph", "num", or "word"

    @property
    def norm(self) -> str:
        return self.text.lower().replace("’", "'")


def tokenize(text: str, start: int = 0, end: Optional[int] = None) -> List[Token]:
    end = len(text) if end is None else end
    return [Token(m.group(), m.start(), m.end(), m.lastgroup or "word") for m in TOKEN_RE.finditer(text, start, end)]


def _starts_sentence(char: str) -> bool:
    return char.isupper() or char.isdigit() or char in "\"'“‘*`([" or bool(PH_RE.match(char))


def split_sentences(text: str) -> List[Tuple[int, int]]:
    """Split text into sentences. Return (start, end) offsets.

    A sentence ends at ".", "!", or "?" before white space and a capital
    letter, a digit, a quote, or a placeholder, or at the end of the text.
    Decimals, versions, and abbreviations such as "e.g." do not end a
    sentence.
    """
    bounds = []
    start = 0
    for match in _SENTENCE_END_RE.finditer(text):
        punctuation = match.group()
        if punctuation[0] not in "。！？":
            rest = text[match.end():].lstrip()
            following = rest[:1]
            if following and not _starts_sentence(following):
                continue
            if punctuation.rstrip("\"'”’)]") == ".":
                before = re.search(r"([A-Za-z][A-Za-z.]*)$", text[max(0, match.start() - 20):match.start()])
                word = before.group(1).lower() if before else ""
                if word in _NO_SPLIT_AFTER:
                    continue
                if word in _NO_SPLIT_BEFORE_NUMBER and following.isdigit():
                    continue
        bounds.append((start, match.end()))
        start = match.end()
    bounds.append((start, len(text)))
    result = []
    for a, b in bounds:
        while a < b and text[a].isspace():
            a += 1
        while b > a and text[b - 1].isspace():
            b -= 1
        if a < b:
            result.append((a, b))
    return result


def count_words(prose: Prose, start: int, end: int, english: bool = True) -> int:
    """Count words with the PU1 conventions.

    A placeholder, a protected span (UI label, glossary term), a hyphenated
    word, and a number with its unit each count as one word.
    """
    if english:
        tokens = [(t.start, t.text, t.kind) for t in tokenize(prose.text, start, end)]
    else:
        tokens = [
            (m.start(), m.group(), "word")
            for m in re.finditer(r"\S+", prose.text[start:end])
            if re.search(r"[^\W_]", m.group()) or PH_RE.search(m.group())
        ]
        tokens = [(start + offset, text, kind) for offset, text, kind in tokens]
    count, seen_spans, index = 0, set(), 0
    while index < len(tokens):
        offset, text, kind = tokens[index]
        span = prose.span_at(offset)
        if span is not None:
            if span not in seen_spans:
                seen_spans.add(span)
                count += 1
            index += 1
            continue
        count += 1
        is_number = kind == "num" or re.fullmatch(r"\d+(?:[.,:]\d+)*%?", text) is not None
        if is_number and index + 1 < len(tokens):
            following = tokens[index + 1][1].lower().strip(".,;:")
            between = prose.text[offset + len(text):tokens[index + 1][0]]
            if following in UNITS and not between.strip():
                index += 1
        index += 1
    return count


def _skip_leading_adverbs(tokens: List[Token], index: int) -> int:
    while index < len(tokens) and tokens[index].norm in LEADING_ADVERBS:
        index += 1
    return index


def _instruction_at(text: str, tokens: List[Token], index: int) -> bool:
    if index >= len(tokens) or tokens[index].kind != "word":
        return False
    word = tokens[index].norm
    following = tokens[index + 1].norm if index + 1 < len(tokens) else ""
    if word in ("never", "don't") or (word == "do" and following == "not"):
        return True
    if word not in IMPERATIVE_VERBS:
        return False
    if text[tokens[index].end:tokens[index].end + 1] == ":":  # A label: "Use: ..."
        return False
    if following in SUBJECT_FOLLOWERS:
        return False
    third = tokens[index + 2].norm if index + 2 < len(tokens) else ""
    if third in SUBJECT_FOLLOWERS and following not in DETERMINERS:
        return False
    return True


def starts_with_instruction(text: str) -> bool:
    """True if the text starts with an instruction.

    The instruction can start with a verb ("Open the file"), with "Do not" or
    "Never", or with a condition before the verb ("If it fails, run ...").
    """
    tokens = tokenize(text)[:40]
    if not tokens:
        return False
    if _instruction_at(text, tokens, _skip_leading_adverbs(tokens, 0)):
        return True
    if tokens[0].norm not in CLAUSE_OPENERS:
        return False
    # Look after each of the first three commas: "At Level 3, when X, use Y".
    comma = text.find(",")
    for _ in range(3):
        if comma < 0:
            break
        index = _skip_leading_adverbs(tokens, next((i for i, t in enumerate(tokens) if t.start > comma), len(tokens)))
        if _instruction_at(text, tokens, index):
            return True
        if index >= len(tokens) or tokens[index].norm in DETERMINERS | SUBJECT_PRONOUNS:
            break  # The main clause starts here, and it is not an instruction.
        comma = text.find(",", comma + 1)
    return False


def is_participle(word: str) -> bool:
    if word in IRREGULAR_PARTICIPLES:
        return True
    return (
        len(word) >= 4
        and word.endswith("ed")
        and not word.endswith("eed")
        and word not in NOT_PARTICIPLES
        and word.isalpha()
    )


def _is_adverb(token: Token) -> bool:
    word = token.norm
    return token.kind == "word" and (word in ADVERBS or (word.endswith("ly") and len(word) > 4))


def _adjacent(text: str, left: Token, right: Token) -> bool:
    return not text[left.end:right.start].strip()


def _after_adverbs(text: str, tokens: List[Token], index: int) -> Optional[int]:
    """Return the index of the word after "be"/"have" and up to 2 adverbs."""
    position = index + 1
    skipped = 0
    while (
        position < len(tokens)
        and skipped < 2
        and _adjacent(text, tokens[position - 1], tokens[position])
        and _is_adverb(tokens[position])
    ):
        position += 1
        skipped += 1
    if position >= len(tokens) or not _adjacent(text, tokens[position - 1], tokens[position]):
        return None
    return position


# ---------------------------------------------------------------------------
# Findings and reports
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    line: int
    rule: str
    severity: str
    message: str
    excerpt: str
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "line": self.line,
            "rule": self.rule,
            "severity": self.severity,
            "message": self.message,
            "excerpt": self.excerpt,
            "suggestion": self.suggestion,
        }


@dataclass
class FileReport:
    path: str
    level: int
    level_source: str
    language: str = ENGLISH
    skipped: bool = False
    findings: List[Finding] = field(default_factory=list)
    language_rules: Optional[str] = None  # The name of the language file, or None.
    sentences: int = 0
    procedural: int = 0
    descriptive: int = 0
    paragraphs: int = 0

    def count(self, severity: str) -> int:
        return sum(1 for finding in self.findings if finding.severity == severity)

    def language_label(self) -> str:
        """For example "ru (language rules: ru.md)"."""
        if is_english(self.language):
            return self.language
        if self.language_rules:
            detail = f"language rules: {self.language_rules}"
        else:
            detail = "universal rules only: no language file"
        if primary_subtag(self.language) in NO_SPACE_LANGUAGES:
            detail += "; S2 not checked: no spaces between words"
        return f"{self.language} ({detail})"

    def stats(self) -> Dict[str, Any]:
        violations = self.count(VIOLATION)
        return {
            "sentences": self.sentences,
            "procedural": self.procedural,
            "descriptive": self.descriptive,
            "paragraphs": self.paragraphs,
            "violations": violations,
            "warnings": self.count(WARNING),
            "suggestions": self.count(SUGGESTION),
            "violations_per_100_sentences": per_100(violations, self.sentences),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "level": self.level,
            "level_source": self.level_source,
            "language": self.language,
            "language_rules": self.language_rules,
            "skipped": self.skipped,
            "stats": self.stats(),
            "findings": [finding.to_dict() for finding in self.findings],
        }


def per_100(violations: int, sentences: int) -> float:
    return round(violations * 100.0 / sentences, 1) if sentences else 0.0


def make_excerpt(left: str, middle: str, right: str, width: int = 80) -> str:
    """Make an excerpt of at most `width` characters around `middle`."""
    left, right = left.lstrip(), right.rstrip()
    if len(middle) >= width:
        return middle[: width - 1] + "…"
    budget = width - len(middle)
    if len(left) + len(right) <= budget:
        return left + middle + right
    take_right = min(len(right), budget // 2)
    take_left = min(len(left), budget - take_right)
    take_right = min(len(right), budget - take_left)
    if take_left < len(left):
        left = "…" + left[len(left) - take_left + 1:] if take_left > 0 else ""
    if take_right < len(right):
        right = right[: take_right - 1] + "…" if take_right > 0 else ""
    return left + middle + right


def severity_for(
    rule: str, level: int, language: str = ENGLISH, reliable: bool = True, procedural: bool = True
) -> Optional[str]:
    """Return the severity of a finding, or None if the rule is off.

    "must" gives a violation (or a warning if the detection is not
    reliable). "prefer" gives a suggestion. A rule for English only is off
    for text in other languages.
    """
    row = RULE_MATRIX[rule]
    if not is_english(language) and row[3] == ENGLISH_ONLY:
        return None
    strength = row[level - 1]
    if strength == MUST_PREFER:
        strength = MUST if procedural else PREFER
    if strength == OFF:
        return None
    if strength == PREFER:
        return SUGGESTION
    return VIOLATION if reliable else WARNING


def resolve_level(
    cli_level: Optional[int], front_matter: Optional[int], config: Config, relative_path: Optional[str]
) -> Tuple[int, str]:
    """Select the level: CLI > front matter > override > config > 2."""
    if cli_level is not None:
        return cli_level, "cli"
    if front_matter is not None:
        return front_matter, "front-matter"
    if relative_path is not None:
        for pattern, level in config.overrides:
            if path_matches(relative_path, pattern):
                return level, "override"
    if config.level is not None:
        return config.level, "config"
    return DEFAULT_LEVEL, "default"


# Language detection -------------------------------------------------------
#
# The detection is simple, and it can be wrong. --lang, the front matter, and
# the configuration override it.
#
# 1. Count the letters of each script. If at least 50% of the letters are
#    ASCII Latin letters (or the most frequent other script is Latin with
#    accents), the text is in a Latin script: go to step 3.
# 2. Use the most frequent script: Cyrillic (uk if the text has the
#    Ukrainian letters і ї є ґ more often than the Russian letters ы э ъ ё,
#    be if it has ў, else ru), Greek (el), Han (zh, or ja if at least 5% of
#    these letters are Hiragana or Katakana), Hangul (ko), Arabic (ar),
#    Hebrew (he), Thai (th). Another script gives "other".
# 3. Count frequent function words (and some letters with accents) of en,
#    de, fr, es, pt, it, nl, and pl. Another language wins only if its score
#    is at least 2 and more than 1.5 times the English score. Else the text
#    is English.

_SCRIPT_RANGES: Tuple[Tuple[int, int, str], ...] = (
    (0x00C0, 0x024F, "latin"), (0x0370, 0x03FF, "greek"), (0x0400, 0x052F, "cyrillic"),
    (0x0590, 0x05FF, "hebrew"), (0x0600, 0x06FF, "arabic"), (0x0750, 0x077F, "arabic"),
    (0x08A0, 0x08FF, "arabic"), (0x0E00, 0x0E7F, "thai"), (0x1100, 0x11FF, "hangul"),
    (0x1C80, 0x1C8F, "cyrillic"), (0x1E00, 0x1EFF, "latin"), (0x1F00, 0x1FFF, "greek"),
    (0x2DE0, 0x2DFF, "cyrillic"), (0x3040, 0x309F, "kana"), (0x30A0, 0x30FF, "kana"),
    (0x3130, 0x318F, "hangul"), (0x31F0, 0x31FF, "kana"), (0x3400, 0x4DBF, "han"),
    (0x4E00, 0x9FFF, "han"), (0xA640, 0xA69F, "cyrillic"), (0xAC00, 0xD7AF, "hangul"),
    (0xF900, 0xFAFF, "han"), (0xFB1D, 0xFB4F, "hebrew"), (0xFB50, 0xFDFF, "arabic"),
    (0xFE70, 0xFEFF, "arabic"), (0xFF66, 0xFF9F, "kana"), (0x20000, 0x2FFFF, "han"),
)
_SCRIPT_LANGUAGE = {
    "greek": "el", "hangul": "ko", "arabic": "ar", "hebrew": "he", "thai": "th",
}

# 20-30 frequent function words for each language. Words that are frequent
# in English ("a", "in", "is", "of", "to") are only in the English list.
_STOP_WORDS: Dict[str, Set[str]] = {
    "en": _words("""
        the a an and of to is are in that it for with this you on be by not or
        from as can when if your have will which do
    """),
    "de": _words("""
        der die das und ist nicht ein eine einen mit sie zu den auf für von dem
        des sich auch wird werden oder bei wenn nach im kann sind aus ihre
    """),
    "fr": _words("""
        le la les des du de et est une un que qui dans pour pas sur avec ce
        cette sont vous nous il elle au aux par ou ne se
    """),
    "es": _words("""
        el la los las de del y en que es un una por para con se lo al su sus
        como más pero este esta son está puede si
    """),
    "pt": _words("""
        o os de do da dos das e em um uma que não para com por se na nos nas
        é ao mais como você são está pode
    """),
    "it": _words("""
        il lo la gli le di del della e è che un una per con non si sono da al
        alla come più questo questa anche ma se
    """),
    "nl": _words("""
        de het een en van dat op te voor met niet zijn er die aan ook als bij
        om door naar wordt worden je u kan uw
    """),
    "pl": _words("""
        w z na się nie że jest o jak od po przez dla są za tak ale czy lub
        oraz może tym być który która które
    """),
}
_LANGUAGE_ORDER = ("en", "de", "fr", "es", "pt", "it", "nl", "pl")
# Letters with accents that are typical of a language (0.5 points each).
_DIACRITICS: Dict[str, str] = {
    "de": "äöüß", "fr": "àâçéèêëîïôùûœ", "es": "áéíñóúü¿¡", "pt": "àáâãçéêíóôõú",
    "it": "àèéìíòóù", "pl": "ąćęłńóśźż", "nl": "", "en": "",
}


def _script_of(char: str) -> str:
    code = ord(char)
    if code < 0x80:
        return "ascii"
    for low, high, script in _SCRIPT_RANGES:
        if low <= code <= high:
            return script
    return "other"


def _cyrillic_language(text: str, letters: int) -> str:
    if sum(text.count(char) for char in "ўЎ") * 500 >= letters > 0:
        return "be"
    ukrainian = sum(text.count(char) for char in "іїєґІЇЄҐ")
    russian = sum(text.count(char) for char in "ыэъёЫЭЪЁ")
    if ukrainian > russian and ukrainian * 100 >= letters:
        return "uk"
    return "ru"


def _latin_language(text: str) -> str:
    lower = text.lower()
    counts: Dict[str, int] = {}
    for word in re.findall(r"[^\W\d_]+", lower):
        counts[word] = counts.get(word, 0) + 1
    scores = {}
    for code in _LANGUAGE_ORDER:
        score = float(sum(counts.get(word, 0) for word in _STOP_WORDS[code]))
        score += 0.5 * sum(lower.count(char) for char in _DIACRITICS[code])
        scores[code] = score
    best = max(_LANGUAGE_ORDER[1:], key=lambda code: scores[code])  # The first in the order wins a tie.
    if scores[best] >= 2 and scores[best] > 1.5 * scores[ENGLISH]:
        return best
    return ENGLISH


def detect_language_text(text: str) -> str:
    """Return the language code of a text. See the notes above."""
    counts: Dict[str, int] = {}
    for char in text:
        if char.isalpha():
            script = _script_of(char)
            counts[script] = counts.get(script, 0) + 1
    letters = sum(counts.values())
    if not letters:
        return ENGLISH
    if counts.get("ascii", 0) * 2 < letters:
        groups = {name: count for name, count in counts.items() if name not in ("ascii", "han", "kana")}
        han, kana = counts.get("han", 0), counts.get("kana", 0)
        groups["cjk"] = han + kana
        script = max(sorted(groups), key=lambda name: groups[name])
        if script == "cyrillic":
            return _cyrillic_language(text, groups[script])
        if script == "cjk":
            return "ja" if kana * 20 >= han + kana else "zh"
        if script in _SCRIPT_LANGUAGE:
            return _SCRIPT_LANGUAGE[script]
        if script != "latin":
            return OTHER
    return _latin_language(text)


def resolve_language(cli: Optional[str], front_matter: Optional[str], config: Config) -> Optional[str]:
    """Select the language: --lang > front matter > config. None means auto."""
    for value in (cli, front_matter, config.language):
        if value is not None and value != AUTO:
            return value
    return None


def detect_language(proses: Iterable[Prose]) -> str:
    """Return the language code of the prose of a document."""
    return detect_language_text("\n".join(prose.text for prose in proses))


# ---------------------------------------------------------------------------
# Checker
# ---------------------------------------------------------------------------


@dataclass
class _Rule:
    """A compiled phrase rule from the word list or the configuration."""

    regex: "re.Pattern[str]"
    rule: str
    source: str  # "choice", "avoid", or "term"
    suggestion: Optional[str]
    choice: Optional[WordChoice] = None
    lowercase: bool = True  # True if the phrases have no capital letters.
    term: str = ""


@dataclass
class _Sentence:
    start: int
    end: int
    kind: Optional[str]  # PROCEDURAL, DESCRIPTIVE, or None (heading, cell)
    tokens: List[Token]


@dataclass
class _Language:
    """A language file with its compiled rules."""

    rules: LanguageRules
    choice_rules: List[_Rule]
    label_splitter: Optional[LabelSplitter]
    risk_regexes: List["re.Pattern[str]"]


class Checker:
    """Check texts with one word list and one configuration."""

    def __init__(
        self, word_choices: Sequence[WordChoice], config: Optional[Config] = None,
        languages_dir: Optional[Path] = DEFAULT_LANGUAGES_DIR,
    ) -> None:
        self.config = config or Config()
        self.word_choices = list(word_choices)
        self.languages_dir = languages_dir
        self.choice_rules = [self._choice_rule(choice) for choice in self.word_choices if choice.lint]
        self.project_rules = self._project_rules()
        self.phrasal_rules = self._phrasal_rules()
        self.cleaner = InlineCleaner(self._glossary_regex())
        self.spelling_rules = {variant: self._spelling_rule(variant) for variant in ("us", "uk")}
        self._languages: Dict[str, Optional[_Language]] = {}

    # -- compiled rules -----------------------------------------------------

    @staticmethod
    def _choice_rule(choice: WordChoice) -> _Rule:
        regex = re.compile(phrase_regex(choice.phrases, inflect=choice.inflect), re.I)
        lowercase = all(phrase == phrase.lower() for phrase in choice.phrases)
        return _Rule(regex, choice.rule, "choice", choice.use, choice, lowercase)

    def language(self, code: str) -> Optional[_Language]:
        """Return the rules of the language file for the code, or None."""
        if code not in self._languages:
            path = find_language_file(code, self.languages_dir)
            language = None
            if path is not None:
                rules = LanguageRules.load(code, path)
                regex = rules.label_regex()
                language = _Language(
                    rules,
                    [self._choice_rule(choice) for choice in rules.word_choices if choice.lint],
                    localized_label_splitter(regex, rules.label_kinds()) if regex is not None else None,
                    rules.risk_regexes(),
                )
            self._languages[code] = language
        return self._languages[code]

    def _project_rules(self) -> List[_Rule]:
        rules = []
        for use, forms in self.config.preferred_terms:
            if forms:
                regex = re.compile(phrase_regex(forms), re.I)
                rules.append(_Rule(regex, "T1", "term", use, term=use))
        for word, use in self.config.avoid_words:
            regex = re.compile(phrase_regex([word]), re.I)
            rules.append(_Rule(regex, "W2", "avoid", use, term=word))
        return rules

    @staticmethod
    def _phrasal_rules() -> List[Tuple[str, "re.Pattern[str]"]]:
        rules = []
        for verb, particle in PHRASAL_VERBS:
            forms = VERB_FORMS.get(verb, (verb, verb + "s", verb + "ed", verb + "ing"))
            pronoun = "" if (verb, particle) in PHRASAL_NO_SEPARATION else r"(?:\s+(?:it|them))?"
            pattern = (
                r"(?<![\w-])(?P<verb>" + "|".join(forms) + r")" + pronoun + r"\s+"
                + re.escape(particle) + r"(?![\w-])"
            )
            rules.append((f"{verb} {particle}", re.compile(pattern, re.I)))
        return rules

    def _glossary_regex(self) -> Optional["re.Pattern[str]"]:
        config = self.config
        bodies = set()
        for terms, suffix in (
            (config.technical_nouns, "(?:s|es)?"),
            (config.technical_verbs, "(?:s|es|ed|d)?"),
            ([use for use, _ in config.preferred_terms], ""),
            (config.keep_verbatim, ""),
        ):
            for term in terms:
                words = term.split()
                if words:
                    bodies.add(r"\s+".join(re.escape(word) for word in words) + suffix)
        if not bodies:
            return None
        ordered = sorted(bodies, key=len, reverse=True)
        return re.compile(r"(?<![\w-])(?:" + "|".join(ordered) + r")(?![\w-])", re.I)

    @staticmethod
    def _spelling_rule(variant: str) -> Tuple["re.Pattern[str]", Dict[str, str]]:
        """Return a regex for the wrong spelling and a map to the right one."""
        wrong_to_right: Dict[str, str] = {}
        for us, uk, both in _SPELLING_PAIRS:
            if variant == "uk" and not both:
                continue
            # Pair the forms by position: base, -s, -ed, -ing. For a pair in
            # one direction, use only the base and the -s form, because the
            # other forms can be correct in both ("programmed").
            count = 4 if both else 2
            for us_form, uk_form in zip(inflection_list(us)[:count], inflection_list(uk)[:count]):
                wrong, right = (uk_form, us_form) if variant == "us" else (us_form, uk_form)
                wrong_to_right[wrong] = right
        for us, uk in _SPELLING_FIXED:
            wrong_to_right[uk if variant == "us" else us] = us if variant == "us" else uk
        for word in _SPELLING_AMBIGUOUS:
            wrong_to_right.pop(word, None)
        for right in list(wrong_to_right.values()):  # A form that is correct is never wrong.
            wrong_to_right.pop(right, None)
        ordered = sorted(wrong_to_right, key=len, reverse=True)
        regex = re.compile(r"(?<![\w-])(?:" + "|".join(map(re.escape, ordered)) + r")(?![\w-])", re.I)
        return regex, wrong_to_right

    def checked_rules(self) -> Set[str]:
        rules = set(BUILT_IN_CHECKS)
        rules |= {choice.rule for choice in self.word_choices if choice.lint}
        return rules

    def not_checked(self) -> List[str]:
        checked = self.checked_rules() | NOT_A_CHECK
        return [rule for rule in RULE_MATRIX if rule not in checked]

    # -- entry point ----------------------------------------------------------

    def check_text(
        self,
        text: str,
        path: str = "<stdin>",
        file_path: Optional[Path] = None,
        level: Optional[int] = None,
        lang: str = "auto",
        suggestions: bool = True,
    ) -> FileReport:
        """Check one document and return its report."""
        lines = text.splitlines()
        front_matter, body_start = split_front_matter(lines)
        relative = relative_to_config(file_path, self.config)
        file_level, source = resolve_level(level, front_matter_level(front_matter), self.config, relative)

        def parse(splitter: Optional[LabelSplitter] = None) -> Tuple[List[Block], List[Prose]]:
            parser = BlockParser(file_level, lock_level=level is not None, label_splitter=splitter)
            parsed = parser.parse(lines[body_start:], body_start + 1)
            return parsed, [self.cleaner.clean(block.lines) for block in parsed]

        blocks, proses = parse()
        cli_language = normalize_language(lang) if lang else None
        if lang and cli_language is None:
            raise UsageError(f"--lang {lang}: use auto, en, other, or a language code, for example ru or pt-BR")
        language = resolve_language(cli_language, front_matter_language(front_matter), self.config)
        if language is None:
            language = detect_language(proses)
        report = FileReport(path, file_level, source, language)
        if not is_english(language) and self.config.non_english == "off":
            report.skipped = True
            path_found = find_language_file(language, self.languages_dir)
            report.language_rules = path_found.name if path_found else None
            return report
        rules = None if is_english(language) else self.language(language)
        if rules is not None:
            report.language_rules = rules.rules.name
            if rules.label_splitter is not None:
                blocks, proses = parse(rules.label_splitter)  # Find the localized labels.
        run = _FileRun(self, report, rules)
        for block, prose in zip(blocks, proses):
            run.check_block(block, prose)
        if not suggestions:
            report.findings = [f for f in report.findings if f.severity != SUGGESTION]
        report.findings.sort(key=lambda finding: finding.line)
        return report


def is_data_cell(prose: Prose) -> bool:
    """True for a table cell that is a data value, not prose.

    configuration.md says that the rules apply to "table text that is prose"
    and not to "data values in tables". A cell with fewer than 4 words and no
    sentence punctuation at the end is a data value: "set up", "`us`", "2".
    """
    text = prose.text.strip()
    return len(tokenize(text)) < 4 and not text.endswith((".", "!", "?"))


class _FileRun:
    """The checks for one file. It keeps the state that W9 needs."""

    def __init__(self, checker: Checker, report: FileReport, language: Optional[_Language] = None) -> None:
        self.checker = checker
        self.report = report
        self.english = is_english(report.language)
        self.language = language
        if self.english:
            self.choice_rules = checker.choice_rules
        else:
            self.choice_rules = language.choice_rules if language is not None else []
        self.check_s2 = self.english or primary_subtag(report.language) not in NO_SPACE_LANGUAGES
        self.defined: Set[str] = set()
        self.flagged: Set[str] = set()
        # Per block:
        self.block: Block = Block("paragraph", DEFAULT_LEVEL)
        self.prose: Prose = Prose("", [], [], 0)
        self.level = DEFAULT_LEVEL

    # -- helpers --------------------------------------------------------------

    def add(
        self, rule: str, severity: Optional[str], offset: int, message: str, excerpt: str,
        suggestion: Optional[str] = None,
    ) -> None:
        if severity is None:
            return
        line = self.prose.line_at(offset) if offset >= 0 else self.block.line
        self.report.findings.append(Finding(line, rule, severity, message, excerpt, suggestion))

    def severity(self, rule: str, reliable: bool = True, procedural: bool = True) -> Optional[str]:
        return severity_for(rule, self.level, self.report.language, reliable, procedural)

    def excerpt(self, sentence: _Sentence, start: Optional[int] = None, end: Optional[int] = None) -> str:
        prose = self.prose
        if start is None or end is None:
            return make_excerpt("", prose.restore(sentence.start, sentence.end).strip(), "")
        return make_excerpt(
            prose.restore(sentence.start, start),
            prose.restore(start, end),
            prose.restore(end, sentence.end),
        )

    def looks_like_name(self, sentence: _Sentence, start: int, matched: str) -> bool:
        """True for a capitalized word in the middle of a sentence.

        Such a word is usually a name or a UI label ("the Display menu").
        Headings use title case, so this test does not apply to them.
        """
        if self.block.kind == "heading" or not matched[:1].isupper() or matched.isupper():
            return False
        before = self.prose.text[sentence.start:start].rstrip()
        return bool(before) and before[-1] not in ":\"“‘'([{—–-•*«„"

    # -- block ------------------------------------------------------------------

    def check_block(self, block: Block, prose: Prose) -> None:
        if block.kind == "cell" and is_data_cell(prose):
            return
        self.block, self.prose = block, prose
        self.level = block.level
        sentences = self.sentences(block, prose)
        prose_block = block.kind in ("paragraph", "item")
        if prose_block:
            self.count_sentences(sentences)
            if block.kind == "paragraph" and any(s.kind for s in sentences):
                self.report.paragraphs += 1
                self.check_paragraph_length(sentences)
            self.check_labels(sentences)
        for sentence in sentences:
            claimed: List[Tuple[int, int]] = []
            if prose_block and sentence.kind is not None:
                if self.check_s2:
                    self.check_length(sentence)
                self.check_semicolon(sentence)
            self.check_phrases(sentence, claimed)
            if not self.english:
                continue  # The other checks need English words.
            self.check_phrasal_verbs(sentence, claimed)
            if prose_block and sentence.kind is not None:
                self.check_passive(sentence, claimed)
                self.check_verb_forms(sentence, claimed)
            self.check_ing(sentence, claimed)
            self.check_spelling(sentence, claimed)
            self.check_double_negative(sentence)
            if block.kind != "heading":
                self.check_abbreviations(sentence)

    def count_sentences(self, sentences: List[_Sentence]) -> None:
        for sentence in sentences:
            if sentence.kind == PROCEDURAL:
                self.report.procedural += 1
            elif sentence.kind == DESCRIPTIVE:
                self.report.descriptive += 1
        self.report.sentences = self.report.procedural + self.report.descriptive

    def sentences(self, block: Block, prose: Prose) -> List[_Sentence]:
        """Split a block into sentences and find the type of each sentence.

        Sentences in headings and table cells have no type. A sentence with
        no letters (only code or numbers) has no type and does not count.
        """
        result = []
        for index, (start, end) in enumerate(split_sentences(prose.text)):
            text = prose.text[start:end]
            kind: Optional[str] = None
            if block.kind in ("paragraph", "item") and re.search(r"[^\W\d_]", text):
                first_step = block.kind == "item" and block.ordered and block.first_of_item and index == 0
                if first_step or (self.english and starts_with_instruction(text)):
                    kind = PROCEDURAL
                else:
                    kind = DESCRIPTIVE
            result.append(_Sentence(start, end, kind, tokenize(prose.text, start, end)))
        return result

    # -- structure checks -------------------------------------------------------

    def check_length(self, sentence: _Sentence) -> None:
        limits = S2_LIMITS[self.level]
        limit = limits[0] if sentence.kind == PROCEDURAL else limits[1]
        words = count_words(self.prose, sentence.start, sentence.end, self.english)
        if words > limit:
            kind = "an instruction" if sentence.kind == PROCEDURAL else "a description"
            message = f"Sentence has {words} words (max {limit} in {kind} at Level {self.level})"
            self.add("S2", self.severity("S2"), sentence.start, message, self.excerpt(sentence))

    def check_paragraph_length(self, sentences: List[_Sentence]) -> None:
        count = sum(1 for sentence in sentences if sentence.kind is not None)
        limit = D2_LIMITS[self.level]
        if count > limit:
            first = next(s for s in sentences if s.kind is not None)
            message = f"Paragraph has {count} sentences (max {limit} at Level {self.level})"
            self.add("D2", self.severity("D2"), first.start, message, self.excerpt(first))

    def check_semicolon(self, sentence: _Sentence) -> None:
        position = self.prose.text.find(";", sentence.start, sentence.end)
        if position < 0:
            return
        rest = self.prose.text[position + 1:sentence.end].strip().lower()
        if self.block.kind == "item" and rest in ("", "and", "or"):
            return  # "item;" at the end of a list item is list punctuation.
        self.add(
            "S5", self.severity("S5"), position, "Semicolon: write two sentences",
            self.excerpt(sentence, position, position + 1),
        )

    def check_labels(self, sentences: List[_Sentence]) -> None:
        label = self.block.label
        if label not in ("note", "warning", "caution"):
            return
        text = self.prose.text
        if not self.english and not is_english(detect_language([self.prose])):
            # The checks for instructions need English words. A language file
            # can give localized signal words: then find a safety word in a
            # note (SF2).
            risks = self.language.risk_regexes if self.language is not None else []
            if label == "note" and any(regex.search(text) for regex in risks):
                first = next((s for s in sentences if s.kind is not None), None)
                self.add(
                    "SF2", self.severity("SF2", reliable=False), first.start if first else -1,
                    "Safety information in a note: use a warning or a caution before the step",
                    self.excerpt(first) if first else "",
                )
            return
        first = next((s for s in sentences if s.kind is not None), None)
        first_text = text[first.start:first.end] if first else ""
        excerpt = self.excerpt(first) if first else ""
        offset = first.start if first else -1
        if label == "note":
            if first and starts_with_instruction(first_text):
                self.add(
                    "P5", self.severity("P5", reliable=False), offset,
                    "Instruction in a note: notes give information only. Put the instruction in a step",
                    excerpt,
                )
            if RISK_WORDS_RE.search(text):
                self.add(
                    "SF2", self.severity("SF2", reliable=False), offset,
                    "Safety information in a note: use WARNING or CAUTION before the step",
                    excerpt,
                )
        elif not first or not starts_with_instruction(first_text):
            self.add(
                "SF1", self.severity("SF1", reliable=False), offset,
                f"{label.upper()} does not start with a command: give the command first, then the risk",
                excerpt,
            )

    # -- word and phrase checks -------------------------------------------------

    def _free(self, start: int, end: int, claimed: List[Tuple[int, int]], kinds: Tuple[str, ...] = (LABEL, TERM)) -> bool:
        if self.prose.protected(start, end, kinds):
            return False
        return not any(a < end and start < b for a, b in claimed)

    def check_phrases(self, sentence: _Sentence, claimed: List[Tuple[int, int]]) -> None:
        """Project terms (T1), project avoid_words (W2), and the word list."""
        text = self.prose.text
        matches = []
        for order, rule in enumerate(self.checker.project_rules + self.choice_rules):
            for match in rule.regex.finditer(text, sentence.start, sentence.end):
                matches.append((match.start(), -(match.end() - match.start()), order, match, rule))
        for start, _, _, match, rule in sorted(matches, key=lambda item: item[:3]):
            end = match.end()
            if not self._free(start, end, claimed):
                continue
            matched = " ".join(match.group().split())
            if rule.source == "choice":
                if rule.lowercase and self.looks_like_name(sentence, start, match.group()):
                    continue
                if rule.lowercase and any(len(w) > 1 and w.isupper() for w in re.findall(r"[^\W\d_]+", match.group())):
                    continue  # A signal word or a keyword: "Use CAUTION", "MAY".
                if rule.choice is not None and rule.choice.verb_only and self._after_determiner(start):
                    continue
                severity = self._choice_severity(rule.choice)
                message = f'Avoid "{matched}"'
            elif rule.source == "term":
                severity = VIOLATION
                message = f'Use the project term "{rule.term}", not "{matched}"'
            else:
                severity = VIOLATION
                message = f'The project avoids "{matched}"'
            if severity is None:
                continue
            claimed.append((start, end))
            self.add(rule.rule, severity, start, message, self.excerpt(sentence, start, end), rule.suggestion)

    def _choice_severity(self, choice: Optional[WordChoice]) -> Optional[str]:
        """From the "From level" of the row: required, a suggestion, or off.

        Below the "From level", the row is a suggestion, unless its rule is
        off at the level. The strength of a language rule (for example RU2)
        comes from the "Rules" table of the language file.
        """
        if choice is None:
            return None
        if self.level >= choice.from_level:
            return WARNING if choice.conditional else VIOLATION
        if self._rule_strength(choice.rule) == OFF:
            return None
        return SUGGESTION

    def _rule_strength(self, rule: str) -> str:
        if self.language is not None and rule in self.language.rules.strengths:
            return self.language.rules.strengths[rule][self.level - 1]
        if rule in RULE_MATRIX:
            if not self.english and RULE_MATRIX[rule][3] == ENGLISH_ONLY:
                return OFF
            return RULE_MATRIX[rule][self.level - 1]
        return PREFER

    def _after_determiner(self, start: int) -> bool:
        before = re.search(r"([A-Za-z]+)\s+$", self.prose.text[max(0, start - 30):start])
        return bool(before) and before.group(1).lower() in DETERMINERS

    def check_phrasal_verbs(self, sentence: _Sentence, claimed: List[Tuple[int, int]]) -> None:
        severity = self.severity("V3")
        if severity is None:
            return
        for name, regex in self.checker.phrasal_rules:
            for match in regex.finditer(self.prose.text, sentence.start, sentence.end):
                start, end = match.start(), match.end()
                if not self._free(start, end, claimed):
                    continue
                if self._after_determiner(start) or self.looks_like_name(sentence, start, match.group()):
                    continue
                claimed.append((start, end))
                phrase = " ".join(match.group().split())
                self.add(
                    "V3", severity, start, f'Phrasal verb "{phrase}": use a one-word verb',
                    self.excerpt(sentence, start, end), PHRASAL_SUGGESTIONS.get(name),
                )

    def check_passive(self, sentence: _Sentence, claimed: List[Tuple[int, int]]) -> None:
        procedural = sentence.kind == PROCEDURAL
        severity = self.severity("V1", reliable=procedural, procedural=procedural)
        if severity is None:
            return
        text, tokens = self.prose.text, sentence.tokens
        for index, token in enumerate(tokens):
            if token.kind != "word" or token.norm not in BE_WORDS:
                continue
            position = _after_adverbs(text, tokens, index)
            if position is None:
                continue
            participle = tokens[position]
            word = participle.norm
            if participle.kind != "word" or not is_participle(word) or word in ("been",):
                continue
            following = tokens[position + 1].norm if position + 1 < len(tokens) else ""
            if word in ADJECTIVE_PARTICIPLES or (word in STATIVE_PARTICIPLES and following != "by"):
                continue
            if word.startswith("un") and word.endswith("ed"):
                continue
            if word == "used" and following == "to":
                continue
            if not self._free(participle.start, participle.end, claimed, (LABEL,)):
                continue
            phrase = " ".join(text[token.start:participle.end].split())
            claimed.append((token.start, participle.end))
            where = "in an instruction" if procedural else "(use it only if the agent is unknown)"
            self.add(
                "V1", severity, token.start, f'Passive voice {where}: "{phrase}"',
                self.excerpt(sentence, token.start, participle.end),
            )

    def check_verb_forms(self, sentence: _Sentence, claimed: List[Tuple[int, int]]) -> None:
        severity = self.severity("V2")
        if severity is None:
            return
        text, tokens = self.prose.text, sentence.tokens
        last_end = -1
        for index, token in enumerate(tokens):
            if token.kind != "word" or token.start < last_end:
                continue
            word = token.norm
            if word not in HAVE_WORDS and (word not in BE_WORDS or word == "being"):
                continue
            position = _after_adverbs(text, tokens, index)
            if position is None:
                continue
            target = tokens[position]
            form = target.norm
            if target.kind != "word" or not self._free(target.start, target.end, claimed, (LABEL,)):
                continue
            following = tokens[position + 1].norm if position + 1 < len(tokens) else ""
            if word in HAVE_WORDS:
                if not is_participle(form) or form in ADJECTIVE_PARTICIPLES:
                    continue
                if form.startswith("un") and form.endswith("ed"):
                    continue
                if form == "read" and following in ("access", "permission", "permissions", "rights", "only"):
                    continue
                name = "perfect tense"
            else:
                if not form.endswith("ing") or len(form) < 5 or form in ING_EXCEPTIONS or form in ADJECTIVE_ING:
                    continue
                name = "continuous tense"
            phrase = " ".join(text[token.start:target.end].split())
            claimed.append((token.start, target.end))
            last_end = target.end
            self.add(
                "V2", severity, token.start, f'Use a simple verb form, not the {name}: "{phrase}"',
                self.excerpt(sentence, token.start, target.end),
            )

    def check_ing(self, sentence: _Sentence, claimed: List[Tuple[int, int]]) -> None:
        severity = self.severity("W6")
        if severity is None:
            return
        for token in sentence.tokens:
            if token.kind != "word":
                continue
            word = token.norm
            last = word.rsplit("-", 1)[-1]
            if not last.endswith("ing") or len(last) < 5 or last in ING_EXCEPTIONS or word in ING_EXCEPTIONS:
                continue
            if token.text.isupper() or not self._free(token.start, token.end, claimed):
                continue
            if self.looks_like_name(sentence, token.start, token.text):
                continue
            self.add(
                "W6", severity, token.start, f'"-ing" form: "{token.text}"',
                self.excerpt(sentence, token.start, token.end),
            )

    def check_spelling(self, sentence: _Sentence, claimed: List[Tuple[int, int]]) -> None:
        severity = self.severity("W8")
        if severity is None:
            return
        variant = "us" if self.level == 3 else self.checker.config.spelling
        regex, wrong_to_right = self.checker.spelling_rules[variant]
        for match in regex.finditer(self.prose.text, sentence.start, sentence.end):
            start, end = match.start(), match.end()
            if not self._free(start, end, claimed) or self.looks_like_name(sentence, start, match.group()):
                continue
            right = wrong_to_right[match.group().lower()]
            if match.group()[:1].isupper():
                right = right.capitalize()
            self.add(
                "W8", severity, start, f'Use {variant.upper()} spelling: "{match.group()}"',
                self.excerpt(sentence, start, end), right,
            )

    def check_double_negative(self, sentence: _Sentence) -> None:
        severity = self.severity("S6", reliable=False)
        if severity is None:
            return
        pattern = r"(?:\bnot|n['’]t|\bnever)\s+(?:" + "|".join(sorted(DOUBLE_NEGATIVE_WORDS)) + r")\b"
        for match in re.finditer(pattern, self.prose.text[sentence.start:sentence.end], re.I):
            start, end = sentence.start + match.start(), sentence.start + match.end()
            if self.prose.protected(start, end):
                continue
            self.add(
                "S6", severity, start, f'Double negative: "{" ".join(match.group().split())}". Make a positive statement',
                self.excerpt(sentence, start, end),
            )

    def check_abbreviations(self, sentence: _Sentence) -> None:
        severity = self.severity("W9", reliable=False)
        if severity is None:
            return
        text = self.prose.text
        words = [t for t in sentence.tokens if t.kind == "word" and re.search(r"[^\W\d_]", t.text)]
        capitals = [t for t in words if t.text.isupper() and len(t.text) > 1]
        if len(words) >= 3 and len(capitals) * 2 >= len(words):
            return  # A sentence in capital letters.
        for token in words:
            base = token.text[:-1] if token.text.endswith("s") and token.text[:-1].isupper() else token.text
            if not re.fullmatch(r"[A-Z][A-Z0-9]{1,5}", base) or base[-1].isdigit():
                continue
            if sum(char.isalpha() for char in base) < 2 or base in KNOWN_ABBREVIATIONS:
                continue
            if self.prose.protected(token.start, token.end):
                continue
            inside_parentheses = text[token.start - 1:token.start] == "(" and text[token.end:token.end + 1] == ")"
            before_definition = re.match(r"\s*\(\s*[A-Za-z]", text[token.end:]) is not None
            if inside_parentheses or before_definition:
                self.defined.add(base)
                continue
            if base in self.defined or base in self.flagged:
                continue
            self.flagged.add(base)
            self.add(
                "W9", severity, token.start, f'Abbreviation "{base}" has no definition: write it in full at its first use',
                self.excerpt(sentence, token.start, token.end),
            )


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------


def in_scope(path: Path, config: Config) -> bool:
    """Apply the include and exclude globs of the configuration."""
    relative = relative_to_config(path, config)
    if relative is None:
        return not config.include
    if config.include and not any(path_matches(relative, pattern) for pattern in config.include):
        return False
    return not any(path_matches(relative, pattern) for pattern in config.exclude)


def collect_files(paths: Sequence[str], config: Config) -> List[Tuple[str, Optional[Path]]]:
    """Return (display path, file path) pairs. "-" is the standard input.

    Files in folders must have a text extension and must be in scope. Files
    that you give by name are always checked.
    """
    result: List[Tuple[str, Optional[Path]]] = []
    seen: Set[str] = set()
    for name in paths:
        if name == "-":
            result.append(("<stdin>", None))
            continue
        path = Path(name)
        if path.is_dir():
            found = []
            for folder, folders, files in os.walk(str(path)):
                folders[:] = sorted(f for f in folders if f not in SKIP_DIRS)
                for file_name in files:
                    candidate = Path(folder) / file_name
                    if candidate.suffix.lower() in TEXT_EXTENSIONS and in_scope(candidate, config):
                        found.append(candidate)
            candidates = sorted(found, key=lambda p: str(p))
        elif path.is_file():
            candidates = [path]
        else:
            raise UsageError(f"{name}: no such file or folder")
        for candidate in candidates:
            key = str(candidate.resolve())
            if key not in seen:
                seen.add(key)
                result.append((str(candidate), candidate))
    return result


def read_text(path: Optional[Path]) -> str:
    if path is None:
        data = sys.stdin.buffer.read() if hasattr(sys.stdin, "buffer") else sys.stdin.read().encode("utf-8")
        return data.decode("utf-8-sig", errors="replace")
    try:
        return path.read_bytes().decode("utf-8-sig", errors="replace")
    except OSError as error:
        raise UsageError(f"cannot read {path}: {error.strerror}") from error


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

_COLORS = {VIOLATION: "\033[31m", WARNING: "\033[33m", SUGGESTION: "\033[36m"}


def summarize(reports: Sequence[FileReport], not_checked: Sequence[str]) -> Dict[str, Any]:
    keys = ("sentences", "procedural", "descriptive", "paragraphs", "violations", "warnings", "suggestions")
    totals: Dict[str, Any] = {key: 0 for key in keys}
    for report in reports:
        stats = report.stats()
        for key in keys:
            totals[key] += stats[key]
    totals["violations_per_100_sentences"] = per_100(totals["violations"], totals["sentences"])
    totals["files"] = len(reports)
    totals["skipped"] = sum(1 for report in reports if report.skipped)
    totals["not_checked"] = list(not_checked)
    return totals


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")


def format_text(reports: Sequence[FileReport], not_checked: Sequence[str], color: bool = False) -> str:
    out = []
    for report in reports:
        if report.skipped:
            out.append(f"{report.path}: skipped ({report.language}: the text is not in English, and non_english is off)")
            continue
        for finding in report.findings:
            severity = finding.severity
            if color:
                severity = f"{_COLORS[severity]}{severity}\033[0m"
            line = f'{report.path}:{finding.line}: {severity} {finding.rule} {finding.message} — "{finding.excerpt}"'
            if finding.suggestion:
                line += f" → {finding.suggestion}"
            out.append(line)
        stats = report.stats()
        out.append(
            f"{report.path}: Level {report.level} ({report.level_source}), {report.language_label()}, "
            f"{_plural(stats['sentences'], 'sentence')} ({stats['procedural']} procedural, "
            f"{stats['descriptive']} descriptive): {_plural(stats['violations'], 'violation')}, "
            f"{_plural(stats['warnings'], 'warning')}, {_plural(stats['suggestions'], 'suggestion')}, "
            f"{stats['violations_per_100_sentences']} violations per 100 sentences"
        )
        out.append("")
    total = summarize(reports, not_checked)
    skipped = f" ({total['skipped']} skipped)" if total["skipped"] else ""
    out.append(
        f"Total: {_plural(total['files'], 'file')}{skipped}, {_plural(total['sentences'], 'sentence')}: "
        f"{_plural(total['violations'], 'violation')}, {_plural(total['warnings'], 'warning')}, "
        f"{_plural(total['suggestions'], 'suggestion')}, "
        f"{total['violations_per_100_sentences']} violations per 100 sentences"
    )
    return "\n".join(out)


def format_json(reports: Sequence[FileReport], not_checked: Sequence[str]) -> str:
    data = {
        "version": VERSION,
        "files": [report.to_dict() for report in reports],
        "summary": summarize(reports, not_checked),
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def exit_code(reports: Sequence[FileReport], fail_on: str) -> int:
    violations = sum(report.count(VIOLATION) for report in reports)
    warnings = sum(report.count(WARNING) for report in reports)
    if fail_on == "violation" and violations:
        return 1
    if fail_on == "warning" and (violations or warnings):
        return 1
    return 0


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

DESCRIPTION = """\
Check Markdown and text files against the controlled-language rules.
The script does not change the files. It shows each problem with its
rule ID, its severity, and the line number."""

EPILOG = """\
severity:
  violation   The rule is "must" at the level, and the script finds the
              problem reliably.
  warning     The rule is "must", but a person must examine the text.
  suggestion  The rule is "prefer" at the level.

level:
  The script uses the first level that it finds. The order is --level,
  the front matter ("controlled-language: 3"), a path override in the
  configuration file, the level in the configuration file, and Level 2.
  A level marker (<!-- controlled-language: level 3 -->) changes the level
  from that point in the document. --level also overrides the markers.
  All levels apply to all languages.

language:
  The script uses the first language that it finds. The order is --lang,
  the front matter ("lang: ru"), the configuration file ("language: ru"),
  and the automatic detection. If the detection is wrong, use --lang.

  English text gets all the checks. Text in other languages gets the
  universal checks: S2, D2, S5, and the words of the project. The script
  also uses the word table and the signal words of the language file
  <code>.md, if this file exists. The default folder of the language files
  is ../references/languages/. For pt-BR, the script also tries pt.md.

  The script does not check S2 in Chinese, Japanese, and Thai, because
  these languages do not use spaces between words.

exit codes:
  0  No problems at or above the --fail-on severity.
  1  The script found problems at or above the --fail-on severity.
  2  The command line, a path, or the configuration is not correct.

not checked:
  The script does not check these rules: {not_checked}.
  Examine them yourself, or use the review mode of the skill.
"""


def build_parser(not_checked: Sequence[str]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check.py",
        description=DESCRIPTION,
        epilog=EPILOG.format(not_checked=", ".join(not_checked)),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "paths", nargs="+", metavar="PATH",
        help="A file, a folder, or - for the standard input. In a folder, the "
        "script checks .md, .mdx, .markdown, and .txt files.",
    )
    parser.add_argument(
        "--level", type=int, choices=(1, 2, 3),
        help="Use this level for all files: 1 (light), 2 (standard), or 3 (strict).",
    )
    parser.add_argument(
        "--config", metavar="PATH",
        help=f"Use this configuration file. Without this option, the script looks "
        f"for {CONFIG_NAME} in the current folder and in the folders above it.",
    )
    parser.add_argument(
        "--format", choices=("text", "json"), default="text",
        help="Write the results as text (the default) or as JSON.",
    )
    parser.add_argument(
        "--fail-on", choices=("never", "violation", "warning"), default="never",
        help="Exit with code 1 if the script finds a violation (violation), or a "
        "violation or a warning (warning). The default is never.",
    )
    parser.add_argument("--no-suggestions", action="store_true", help="Do not show suggestions.")
    parser.add_argument(
        "--lang", type=_language_argument, default=AUTO, metavar="CODE",
        help="The language of the text: auto (the default), en, or a language code, "
        "for example ru, de, or pt-BR. auto finds the language of each file. "
        "other means a language that is not English and has no language file.",
    )
    parser.add_argument(
        "--word-list", metavar="PATH",
        help="Use this word list for English. The default is ../references/word-choices.md.",
    )
    parser.add_argument(
        "--languages-dir", metavar="PATH",
        help="Use the language files in this folder. The default is ../references/languages/.",
    )
    return parser


def _language_argument(value: str) -> str:
    code = normalize_language(value)
    if code is None:
        raise argparse.ArgumentTypeError(
            f"'{value}' is not a language code. Use auto, en, other, or a code such as ru or pt-BR"
        )
    return code


def _default_not_checked() -> List[str]:
    try:
        return Checker(load_word_choices(DEFAULT_WORD_LIST)).not_checked()
    except UsageError:
        return [rule for rule in RULE_MATRIX if rule not in BUILT_IN_CHECKS | NOT_A_CHECK]


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser(_default_not_checked())
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")  # type: ignore[attr-defined]
    try:
        if args.config:
            config = load_config(Path(args.config))
        else:
            found = find_config(Path.cwd())
            config = load_config(found) if found else Config()
        word_list = Path(args.word_list) if args.word_list else DEFAULT_WORD_LIST
        languages_dir = Path(args.languages_dir) if args.languages_dir else DEFAULT_LANGUAGES_DIR
        if args.languages_dir and not languages_dir.is_dir():
            raise UsageError(f"{args.languages_dir}: no such folder")
        checker = Checker(load_word_choices(word_list), config, languages_dir)
        reports = []
        for display, path in collect_files(args.paths, config):
            reports.append(
                checker.check_text(
                    read_text(path), display, path, args.level,
                    args.lang, not args.no_suggestions,
                )
            )
    except UsageError as error:
        print(f"check.py: error: {error}", file=sys.stderr)
        return 2
    not_checked = checker.not_checked()
    if args.format == "json":
        print(format_json(reports, not_checked))
    else:
        color = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
        print(format_text(reports, not_checked, color))
    return exit_code(reports, args.fail_on)


if __name__ == "__main__":
    sys.exit(main())
