#!/usr/bin/env python3
"""hookscore.py - score a short-form hook before you spend a take on it, and name its formula.

Origin (MIT, same author as this repo):
  - The five-property scoring panel (LENGTH, SPECIFICITY, STAKES, FRONTLOAD, ADDRESS, the
    dealbreakers and the verdict formula) is copied with its scoring unchanged from
    Jakeschincariol/instagram-agent-skill@d03c56b skills/ig-reel/hookscore.py, because that
    panel was measured against real short-form hooks (numbers below).
  - The formula classifier comes from Jakeschincariol/youtube-agent-skill@a2feb21
    skills/yt-script/hookscore.py, run against the fused hooks.json in this folder.
  - The PAYOFF line is new: Jake's house rule that a hook leads with money made, money saved
    or a number. It is reported beside the score and never folded into it, so the calibration
    below still describes the score.

What the score is: five local heuristics computed from the text alone. Strong hooks tend to
share them: a length you can say in about three seconds, a concrete marker, something at
stake, the payload at the front, and a viewer to aim it at.

What it is NOT: a view predictor. The panel was tested against 74 real short-form hooks,
transcribed from the first three seconds of the top eight and bottom eight performers on five
channels. Separating a real hook from a deliberately bad one it does well: AUC 0.83. Separating
a creator's hits from that same creator's misses it barely does at all: AUC 0.56, where 0.50 is
a coin flip. Use it to catch greetings, preambles, hooks with nothing concrete in them and hooks
that take five seconds to say. A low score is a reason to rewrite; a high score is not a promise.

Usage
  python3 hookscore.py hooks.txt                  # one hook per line, ranked
  python3 hookscore.py --hook "I lost $18,000 on one missing contract."
  python3 hookscore.py --hook "first" --hook "second"
  pbpaste | python3 hookscore.py -
  python3 hookscore.py hooks.txt --json
  python3 hookscore.py --list                     # the 26 formulas, payoff-first marked

Exit codes: 0 the best hook is STRONG, 1 no hook is STRONG yet, 2 bad input.
"""

import argparse
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOOKS_PATH = os.path.join(HERE, "hooks.json")

# ------------------------------------------------------------------ the scoring panel
# Copied from instagram-agent-skill. Non-ASCII literals are written as escapes; the
# character classes are identical.

# Counts "$18,000" as one token. The LENGTH band (5 to 12) was calibrated with this exact
# tokenizer, so it stays. speech.py estimates spoken seconds separately, numbers expanded.
WORD_RE = re.compile(r"[A-Za-z0-9$%'’-]+")
NUMBER_RE = re.compile(
    r"\$\s?\d[\d,]*(?:\.\d+)?"                       # money, whole
    r"|\b\d[\d,]*(?:\.\d+)?\s?"                      # a figure, with or
    r"(?:%|k\b|x\b|hrs?\b|hours?\b|mins?\b|minutes?\b"  # without a unit
    r"|days?\b|weeks?\b|months?\b|years?\b)?",
    re.IGNORECASE)
PROPER_RE = re.compile(r"(?<!^)\b[A-Z][a-z]{2,}\b")
HASHTAG_RE = re.compile(r"(?:^|\s)#\w+")
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF☀-➿]")

# Spoken hooks say their numbers out loud. "Zero dollars" and "twenty grand" are as concrete
# as "$0" and "$20,000". "one" and "first" are deliberately absent: they are filler far more
# often than they are a quantity.
SPOKEN_NUMBERS = {
    "zero", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "fifteen", "twenty", "thirty", "forty", "fifty",
    "sixty", "seventy", "eighty", "ninety", "hundred", "thousand", "million",
    "billion", "dozen", "half", "twice", "triple",
}
MONEY_WORDS = {
    "dollars", "dollar", "bucks", "grand", "percent", "cents",
    "millionaire", "billionaire", "revenue", "profit", "salary", "rent",
}

# Words that put something on the line. A hook with none of these is a statement; a hook
# with one is a reason to keep watching.
STAKES = {
    "stop", "never", "wrong", "mistake", "mistakes", "lost", "lose", "losing",
    "cost", "costs", "broke", "broken", "failed", "failure", "fail", "nobody",
    "no", "not", "don't", "dont", "doesn't", "didn't", "can't", "won't",
    "quit", "quitting", "fired", "deleted", "delete", "killed", "kills", "kill",
    "replaced", "replaces", "cut", "beat", "free", "paid", "charged", "hired",
    "saved", "first",
    "banned", "illegal", "worst", "hate", "hated", "wasted", "waste", "scam",
    "lie", "lied", "lying", "truth", "secret", "hidden", "stole", "stolen",
    "before", "until", "instead", "but", "except", "unless", "problem",
    "risk", "danger", "warning", "regret", "wish", "should", "shouldn't",
    "still", "already", "only", "without", "versus", "vs", "actually",
}

# Openers that spend the first second saying nothing.
WEAK_OPENERS = [
    "so", "ok", "okay", "hey", "hi", "hello", "guys", "yo", "alright",
    "welcome", "today", "basically", "honestly", "look", "listen", "um",
    "just", "let", "lets", "let's", "i wanted", "i want", "one of",
    "have you", "did you", "do you", "are you", "in this", "in today",
    "the thing", "a lot", "there is", "there are", "this is", "it is",
    "as a", "when it", "if you've", "you know",
]

# Imperatives that earn the front position.
IMPERATIVES = {
    "stop", "steal", "copy", "delete", "try", "watch", "read", "save",
    "use", "build", "make", "write", "send", "take", "start", "quit",
    "never", "always", "don't", "dont", "do", "put", "run", "check",
}

DEALBREAKERS = [
    (re.compile(r"(?i)^\s*(?:stop scrolling|don'?t scroll)"),
     "Opens with \"stop scrolling\". Asking for attention proves you have not earned it."),
    (re.compile(r"(?i)\b(?:in (?:this|today'?s) (?:video|reel)|i'?m going to show you|i'?ll show you how)\b"),
     "Video preamble. Delete it and open on the payoff."),
    (re.compile(r"(?i)^\s*(?:hey |hi |what'?s up |welcome )"),
     "Greeting. Nobody came to the feed to be greeted."),
    (HASHTAG_RE,
     "Hashtag in the hook. Hashtags belong at the bottom of the caption, if anywhere."),
    (EMOJI_RE,
     "Emoji in the hook. On-screen text at hook size has room for words or for an emoji, not both."),
]


def clamp(n):
    return max(0.0, min(100.0, n))


def words(text):
    return WORD_RE.findall(re.sub(r"(?<=\d),(?=\d)", "", text))


def check_length(text):
    """A hook has to land before the thumb moves. Roughly two seconds."""
    w = words(text)
    n = len(w)
    secs = n / 2.75                      # ~165 words per minute, spoken
    chars = len(text.strip())
    if 5 <= n <= 12:
        score = 100.0
    elif n < 5:
        score = clamp(100 - (5 - n) * 20)
    else:
        score = clamp(100 - (n - 12) * 11)
    if chars > 60:                       # two lines of big on-screen text
        score -= 12
    return clamp(score), "%d words, %d chars, ~%.1fs spoken (want 5-12 words)" % (n, chars, secs)


def check_specificity(text):
    """One concrete thing beats three abstract ones."""
    nums = [n.strip() for n in NUMBER_RE.findall(text) if n.strip()]
    propers = set(PROPER_RE.findall(text))
    low = [w.lower().strip("'’") for w in words(text)]
    spoken = [w for w in low if w in SPOKEN_NUMBERS or w in MONEY_WORDS]
    hits = len(nums) + len(propers) + len(spoken)
    score = 15.0 if hits == 0 else clamp(45 + hits * 30)
    found = ", ".join(nums[:2] + sorted(propers)[:2] + spoken[:2])
    return score, ("%d concrete marker(s)" % hits + (": %s" % found if found else
                   " - no number, no name, nothing checkable"))


def check_stakes(text):
    """Tension, cost, negation. Something the viewer might lose."""
    w = [x.lower().strip("'’") for x in words(text)]
    hits = [x for x in w if x in STAKES]
    markers = sorted(set(hits))
    if re.search(r"\$\s?\d", text):
        markers.append("a price")
    n = len(markers)
    score = {0: 20.0, 1: 70.0}.get(n, 100.0)
    detail = "%d tension marker(s)" % n + (": %s" % ", ".join(markers[:4]) if markers else
                                           " - nothing is at stake in this line")
    return clamp(score), detail


def check_frontload(text):
    """The interesting word cannot be in position nine."""
    w = words(text)
    if not w:
        return 0.0, "empty"
    low = [x.lower().strip("'’") for x in w]
    opener = " ".join(low[:2])
    penalty = 0
    hit_opener = None
    for weak in WEAK_OPENERS:
        if opener.startswith(weak) or low[0] == weak:
            penalty, hit_opener = 30, weak
            break
    payload = None
    for i, token in enumerate(low):
        if (token in STAKES or token in SPOKEN_NUMBERS or token in MONEY_WORDS
                or NUMBER_RE.match(w[i]) or (i and PROPER_RE.match(w[i]))):
            payload = i
            break
    if payload is None:
        base = 30.0
        where = "no payload word anywhere in the line"
    elif payload <= 3:
        base = 100.0
        where = "payload at word %d" % (payload + 1)
    elif payload <= 6:
        base = 70.0
        where = "payload at word %d, could move forward" % (payload + 1)
    else:
        base = 40.0
        where = "payload at word %d, too late" % (payload + 1)
    detail = where + ("; weak opener \"%s\"" % hit_opener if hit_opener else "")
    return clamp(base - penalty), detail


def check_address(text):
    """Aimed at one viewer, or floating in the air."""
    low = text.lower()
    w = [x.lower().strip("'’") for x in words(text)]
    if re.search(r"\b(you|your|you're|youre|yourself)\b", low):
        return 100.0, "speaks to the viewer"
    if w and w[0] in IMPERATIVES:
        return 90.0, "imperative opener (\"%s\")" % w[0]
    if re.search(r"\b(i|my|me|we|our)\b", low):
        return 70.0, "first person, no viewer named"
    return 35.0, "third person, nobody in the room"


CHECKS = ["LENGTH", "SPECIFICITY", "STAKES", "FRONTLOAD", "ADDRESS"]


def run(text):
    """The calibrated panel. Returns (results, overall, verdict, flags)."""
    results = {
        "LENGTH": check_length(text),
        "SPECIFICITY": check_specificity(text),
        "STAKES": check_stakes(text),
        "FRONTLOAD": check_frontload(text),
        "ADDRESS": check_address(text),
    }
    flags = [msg for pattern, msg in DEALBREAKERS if pattern.search(text)]
    scores = [results[c][0] for c in CHECKS]
    # The weakest property caps the hook: one bad property is enough for the thumb to keep
    # moving.
    overall = statistics.mean(scores) * 0.6 + min(scores) * 0.4 - len(flags) * 15
    overall = clamp(overall)
    verdict = "STRONG" if overall >= 70 and min(scores) >= 55 and not flags else (
        "OK" if overall >= 50 else "WEAK")
    return results, overall, verdict, flags


# ------------------------------------------------------------- formula classifier
# From youtube-agent-skill: count each formula's matching patterns, most hits wins. Ties go to
# the formula listed first in hooks.json.

_FORMULAS = None


def load_formulas(path=HOOKS_PATH):
    global _FORMULAS
    if _FORMULAS is None or path != HOOKS_PATH:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        compiled = []
        for f in data["hooks"]:
            compiled.append((f, [re.compile(p, re.IGNORECASE) for p in f["match"]]))
        if path != HOOKS_PATH:
            return compiled
        _FORMULAS = compiled
    return _FORMULAS


def classify(text):
    """Return (formula dict or None, number of patterns that matched)."""
    best, hits = None, 0
    for f, patterns in load_formulas():
        n = sum(1 for p in patterns if p.search(text))
        if n > hits:
            best, hits = f, n
    return best, hits


# ------------------------------------------------------------------- payoff rule
# Jake's rule: lead with a concrete payoff. Money beats a bare number; both beat nothing.

MONEY_RE = re.compile(
    r"[$£€]\s?\d[\d,.]*(?:\s?(?:k|m|b|bn)\b|\s(?:million|billion|thousand|grand)\b)?"
    r"|\b\d[\d,.]*\s?(?:k\s|m\s)?(?:dollars|bucks|grand|euros|pounds)\b"
    r"|\b(?:a|one|two|three|four|five|six|seven|eight|nine|ten|twenty|fifty|hundred)\s+"
    r"(?:grand|thousand dollars|million dollars|hundred dollars|bucks|dollars)\b",
    re.IGNORECASE)
FIGURE_RE = re.compile(
    r"\b\d[\d,.]*\s?(?:%|x\b|k\b|m\b)?"
    r"|\b(?:two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|"
    r"forty|fifty|sixty|ninety|hundred|thousand|million|billion|half|double|triple|twice)\b",
    re.IGNORECASE)
LEAD_WORDS = 8          # about three seconds at 165 wpm


def payoff(text):
    """Where the first concrete payoff sits. status is LEADS, LATE or MISSING."""
    money, figure = MONEY_RE.search(text), FIGURE_RE.search(text)
    hit = money if money else figure
    if not hit:
        return {"kind": None, "token": None, "word": None, "status": "MISSING"}
    first = money if not figure or (money and money.start() <= figure.start()) else figure
    word = len(text[:first.start()].split()) + 1
    return {"kind": "money" if money else "number", "token": hit.group(0).strip(),
            "word": word, "status": "LEADS" if word <= LEAD_WORDS else "LATE"}


def payoff_line(p):
    if p["status"] == "MISSING":
        return "MISSING  no money and no number. Lead with what the viewer gets, or ask for the real figure"
    what = "money (%s)" % p["token"] if p["kind"] == "money" else "a number (%s)" % p["token"]
    if p["status"] == "LEADS":
        return "LEADS    %s at word %d" % (what, p["word"])
    return "LATE     %s at word %d. Move it into the first %d words" % (what, p["word"], LEAD_WORDS)


# ---------------------------------------------------------------------- analysis

def analyse(text):
    results, overall, verdict, flags = run(text)
    formula, hits = classify(text)
    return {
        "hook": text.strip(),
        "checks": {k: {"score": round(v[0], 1), "detail": v[1]} for k, v in results.items()},
        "weakest": min(CHECKS, key=lambda c: results[c][0]),
        "flags": flags,
        "score": round(overall, 1),
        "verdict": verdict,
        "formula": ({"id": formula["id"], "name": formula["name"], "matched": hits,
                     "payoff_first": formula.get("payoff_first", False)}
                    if formula else {"id": None, "name": "Unclassified", "matched": 0,
                                     "payoff_first": False}),
        "payoff": payoff(text),
    }


def bar(score, width=24):
    filled = int(round(score / 100.0 * width))
    return "#" * filled + "." * (width - filled)


def render_one(a, out=sys.stdout):
    print("\nHOOK SCORE", file=out)
    print("=" * 62, file=out)
    print("  \"%s\"\n" % a["hook"], file=out)
    for name in CHECKS:
        c = a["checks"][name]
        print("  %-13s %s %5.1f" % (name, bar(c["score"]), c["score"]), file=out)
        print("  %-13s %s" % ("", c["detail"]), file=out)
    print("-" * 62, file=out)
    print("  %-13s %s %5.1f   %s" % ("HOOK SCORE", bar(a["score"]), a["score"], a["verdict"]), file=out)
    f = a["formula"]
    print("  %-13s %s" % ("FORMULA", f["name"] + ("  (%d pattern%s matched)" % (
        f["matched"], "" if f["matched"] == 1 else "s") if f["matched"] else
        "  (no formula matched; that is usually a summary, not a hook)")), file=out)
    print("  %-13s %s" % ("PAYOFF", payoff_line(a["payoff"])), file=out)
    for flag in a["flags"]:
        print("\n  DEALBREAKER  %s" % flag, file=out)
    if a["verdict"] != "STRONG":
        print("\n  Weakest property: %s. Fix that one and re-run." % a["weakest"], file=out)
    print("", file=out)


def render_table(rows, out=sys.stdout):
    print("\nHOOK RANKING\n" + "=" * 78, file=out)
    for i, r in enumerate(rows, 1):
        mark = "->" if i == 1 else "  "
        hook = r["hook"] if len(r["hook"]) <= 62 else r["hook"][:59] + "..."
        print("%s %5.1f %-7s %s" % (mark, r["score"], r["verdict"], hook), file=out)
        print("        %s · payoff %s · weakest %s (%.0f)" % (
            r["formula"]["name"], r["payoff"]["status"], r["weakest"],
            r["checks"][r["weakest"]]["score"]), file=out)
        for flag in r["flags"]:
            print("        dealbreaker: %s" % flag, file=out)
    print("\nShoot the top one. If the top one is under 50, none of these is the hook yet.\n",
          file=out)


def render_list(out=sys.stdout):
    print("\n26 HOOK FORMULAS  (P = payoff-first)\n" + "=" * 78, file=out)
    for f, _ in load_formulas():
        print("  %s %-22s %-28s %s" % ("P" if f.get("payoff_first") else " ", f["name"],
                                       f["on_screen"], f["source"]), file=out)
        print("     %s" % f["example"], file=out)
    print("", file=out)


def main():
    ap = argparse.ArgumentParser(
        description="Score short-form hooks on five calibrated properties and name the formula.",
        epilog="Exit 0 when the best hook is STRONG, 1 when none is yet, 2 on bad input.")
    ap.add_argument("input", nargs="?", help="file with one hook per line, or - for stdin")
    ap.add_argument("--hook", action="append", default=[], help="a hook to score (repeatable)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--list", action="store_true", help="print the formula library and exit")
    args = ap.parse_args()

    if args.list:
        if args.json:
            print(json.dumps([f for f, _ in load_formulas()], indent=1))
        else:
            render_list()
        return 0
    if args.hook:
        lines = [h for h in args.hook if h.strip()]
    elif args.input:
        if args.input != "-" and not os.path.exists(args.input):
            print("no such file: %s" % args.input, file=sys.stderr)
            return 2
        raw = sys.stdin.read() if args.input == "-" else open(args.input, encoding="utf-8").read()
        lines = [l.strip() for l in raw.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    else:
        ap.print_help(sys.stderr)
        return 2
    if not lines:
        print("nothing to score", file=sys.stderr)
        return 2

    rows = [analyse(line) for line in lines]
    if args.json:
        print(json.dumps(rows if len(rows) > 1 else rows[0], indent=2, ensure_ascii=False))
    elif len(rows) == 1:
        render_one(rows[0])
    else:
        render_table(sorted(rows, key=lambda r: -r["score"]))
    return 0 if any(r["verdict"] == "STRONG" for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
