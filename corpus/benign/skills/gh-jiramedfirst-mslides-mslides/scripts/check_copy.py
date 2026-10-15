"""Refresh: every UI label a slide quotes must still exist in the app's message catalogue.

  python check_copy.py <ws>/manual.json [--messages <file.json> [<file.json> ...]]

A renamed button can leave the screenshot looking almost the same while step 2 still says click "Send".
Slides quote on-screen text in “ ” or " " (content.md convention), so each quoted string is looked up as a
WHOLE message value or a whole segment of one ("…" in the quote stands for an omitted part). The catalogue is the
app's i18n JSON — manual.json "copy.messages" (a path or a list, relative to the workspace or absolute), or
--messages on the command line. Strings that only appear in data (record names, numbers, MANUAL-… titles) are not
labels — list them in manual.json "copy_ignore" so the report stays signal.
Exit 1 when something is stale, so it can gate a rebuild.
"""
import json, os, pathlib, re, sys

cfg_path = pathlib.Path(sys.argv[1]).expanduser().resolve()
cfg, ws = json.loads(cfg_path.read_text(encoding="utf-8")), cfg_path.parent
if "--messages" in sys.argv:
    files = [a for a in sys.argv[sys.argv.index("--messages") + 1:] if not a.startswith("--")]
else:
    files = cfg.get("copy", {}).get("messages") or []
    files = [files] if isinstance(files, str) else files
if not files:
    raise SystemExit('no message catalogue: set manual.json "copy": {"messages": "<path to the app\'s i18n JSON>"} or pass --messages')
msgs = [p if p.is_absolute() else ws / p for p in (pathlib.Path(os.path.expanduser(f)) for f in files)]
msg_label = ", ".join(m.name for m in msgs)


def values(node):
    if isinstance(node, dict):
        for v in node.values():
            yield from values(v)
    elif isinstance(node, str):
        yield node


PH = "\u0000"


def icu(v):
    """Replace every top-level {…} placeholder with PH, counting brace depth: ICU plurals nest
    ("Send {count, plural, one {# item} other {# items}}"), which a flat {[^}]*} regex cuts in half."""
    out, depth = [], 0
    for ch in v:
        if ch == "{":
            if depth == 0:
                out.append(PH)
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
        elif depth == 0:
            out.append(ch)
    return "".join(out)


catalogue = [icu(v) for m in msgs for v in values(json.loads(m.read_text(encoding="utf-8")))]
# The other direction: a slide may quote a message with its placeholders FILLED ("Sent DOC-9105 — now Waiting for review"
# for "Sent {documentNo} — now {status}"). Templates with < 6 literal chars would match anything — skipped.
templates = [re.compile(re.escape(v).replace(PH, ".+?")) for v in catalogue
             if PH in v and len(v.replace(PH, "").strip()) >= 6]
ignore = set(cfg.get("copy_ignore", []))
# Each message, plus its parts at two grains: coarse (placeholders, : · — – | newline) keeps a label that carries
# its own parenthesis ("Save total (control total) — …"); fine also splits ( ) [ ] , / for labels inside them.
segments = set()
for v in catalogue:
    segments.add(v.strip())
    for sep in (r"[\u0000:·—–|\n]", r"[\u0000:·—–()\[\]|,/\n]"):
        segments.update(s.strip() for s in re.split(sep, v) if s.strip())


def known(s):
    # Slides write a count as a bare n / m ("Send n items") where the catalogue has an ICU placeholder ("Send {count} items"),
    # so n/m standing alone become wildcards; so do "…" (a label quoted only in part) and "xxxx" (a document number
    # like DOC-xxxx). Everything else must match literally.
    esc = re.escape(s)
    for wild in (re.escape("…"), re.escape("...")):
        esc = esc.replace(wild, ".*?")
    esc = re.sub(r"[\w\\-]*xxxx", ".*?", esc)  # the whole token: "DOC-xxxx" is "{number}" in the catalogue
    pat = re.compile(re.sub(r"(?<![A-Za-z])[nm](?![A-Za-z])", ".+?", esc))
    # Match a whole message or a whole SEGMENT of one, never a bare substring. Substring missed a label that grew
    # ("Overview" → "Overview of all my requests"); whole-message-only flagged quotes that are legitimately one
    # labelled part of a longer message ("Balance" in "Balance: {amount}").
    return any(pat.fullmatch(seg) for seg in segments) or any(t.fullmatch(s) for t in templates)


QUOTED = re.compile(r"[“\"]([^”\"]{2,80})[”\"]")
def texts():
    """Every slide string that can quote UI copy: task steps/tips, and the manual.json intro/reference tables,
    bullet slides and closing — the fact-heavy tables quote status and button labels too."""
    for it in json.loads((ws / cfg.get("manifest", "manifest.json")).read_text(encoding="utf-8")):
        yield from ((it["shot"], f"step {i}", s) for i, s in enumerate(it["steps"], 1))
        yield it["shot"], "tip", it.get("tip", "")
    for sec in ("intro", "reference"):
        for e in cfg.get(sec, []):
            where = f"{sec}: {e.get('title', '')}"
            for row in e.get("rows", []):
                yield from ((where, "table", c) for c in row)
            yield from ((where, "bullet", l) for l in e.get("lines", []))
    cl = cfg.get("closing") or {}
    yield "closing", "text", " ".join(cl.get(k, "") for k in ("title", "subtitle"))


stale = []
for shot, where, text in texts():
    for q in QUOTED.findall(text):
        q = q.replace("**", "").strip()  # 'Click "**Save**"' renders as Save
        if q and q not in ignore and not q.startswith("MANUAL-") and not known(q):
            stale.append((shot, where, q))

for shot, where, q in stale:
    print(f"  {shot} · {where}: “{q}” not in {msg_label}")
print(f"{len(stale)} quoted label(s) not found in {msg_label}")
sys.exit(1 if stale else 0)
