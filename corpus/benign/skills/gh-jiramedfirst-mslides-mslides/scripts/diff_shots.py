"""Refresh: compare the accepted shots/ with a replay's shots-new/, per manifest slide.

  python diff_shots.py <ws> [--partial]                 # report → <ws>/refresh-report.md
  python diff_shots.py <ws> --accept <shot> [<shot>…]   # promote reviewed shots into shots/
  python diff_shots.py <ws> --accept-changed            # promote every CHANGED or NEW shot (never a broken one)

Verdicts:
  broken    — no new shot (its step failed or no longer produces it). --partial treats that as "not replayed".
  changed   — mark count differs, a mark hint (e.g. `badge`) differs, a mark moved/resized > 8 px, > 5% of a mark box differs, or ≥ 50 px of the crop.
              These slides need a look (wording may be stale too — run check_copy.py) and go to visual QA.
  unchanged — same marks, same picture where the slide shows it. Accepting is optional.
Only the crop window the slide actually shows is compared (build_manual.crop_window), so a changed sidebar
badge outside the crop does not flag a slide whose visible part is identical.
"""
import json, pathlib, shutil, sys
# Windows consoles/pipes default to a legacy code page; the arrows in our messages would raise UnicodeEncodeError.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from PIL import Image, ImageChops
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from build_manual import crop_window

# Measured on a real app: two replays of the same screen differ by 0 px; a page heading growing by a few words
# changed ~1000 px = 0.09% of the crop. So the crop test is an
# absolute pixel count, not a share — any real text change is far above 50 px, render noise is 0.
MOVE_PX, PIXEL_MIN, MARK_FRAC = 8, 50, 0.05

ws = pathlib.Path(sys.argv[1]).expanduser()
old_d, new_d = ws / "shots", ws / "shots-new"
items = json.loads((ws / "manifest.json").read_text(encoding="utf-8"))
shots = list(dict.fromkeys(it["shot"] for it in items))


def verdict(name):
    o, n = old_d / f"{name}.json", new_d / f"{name}.json"
    if not n.exists():
        return "missing", "no new shot"
    if not o.exists():
        return "new", "no accepted shot yet — review and --accept it"
    om, nm = json.loads(o.read_text(encoding="utf-8")), json.loads(n.read_text(encoding="utf-8"))
    if len(om["marks"]) != len(nm["marks"]):
        return "changed", f"marks {len(om['marks'])} → {len(nm['marks'])} (steps must be re-counted)"
    for i, (a, b) in enumerate(zip(om["marks"], nm["marks"]), 1):
        d = max(abs(a[k] - b[k]) for k in ("x", "y", "w", "h"))
        if d > MOVE_PX:
            return "changed", f"mark {i} moved/resized {d:.0f}px"
    # Everything in the marks JSON except geometry is part of the slide (a `badge` hint moves a badge): a shot
    # whose picture is identical but whose hints differ is still a change, or --accept-changed would drop it.
    geo = ("x", "y", "w", "h")
    for i, (a, b) in enumerate(zip(om["marks"], nm["marks"]), 1):
        ra, rb = ({k: v for k, v in m.items() if k not in geo} for m in (a, b))
        if ra != rb:
            return "changed", f"mark {i} hints {ra or '{}'} → {rb or '{}'}"
    extra = lambda m: {k: v for k, v in m.items() if k not in ("w", "h", "marks")}
    if extra(om) != extra(nm):
        return "changed", f"shot metadata {extra(om)} → {extra(nm)}"
    if (om["w"], om["h"]) != (nm["w"], nm["h"]):  # the crop would compare the same rectangle of different screens
        return "changed", f"viewport {om['w']}x{om['h']} → {nm['w']}x{nm['h']}"
    x, y, w, h = (int(v) for v in crop_window(om))
    a = Image.open(old_d / f"{name}.png").convert("L").crop((x, y, x + w, y + h))
    b = Image.open(new_d / f"{name}.png").convert("L").crop((x, y, x + w, y + h))
    if a.size != b.size:
        return "changed", "screen size differs"
    diff = ImageChops.difference(a, b).point(lambda p: 255 if p > 40 else 0)
    # A marked control is what a step talks about: a restyled or relabelled button is a fraction of a percent of
    # the crop, so judge each mark's own box separately (measured: a repainted button scored 0.3% of the crop).
    for i, m in enumerate(om["marks"], 1):
        box = diff.crop((int(m["x"] - x), int(m["y"] - y), int(m["x"] - x + m["w"]), int(m["y"] - y + m["h"])))
        f = sum(box.histogram()[255:]) / max(1, box.size[0] * box.size[1])
        if f > MARK_FRAC:
            return "changed", f"inside mark {i}: {f:.0%} of its pixels differ"
    n = sum(diff.histogram()[255:])
    return ("changed", f"{n} px of the visible area differ") if n >= PIXEL_MIN else ("unchanged", f"{n} px")


def accept(names):
    for name in names:
        if not (new_d / f"{name}.json").exists():
            raise SystemExit(f"{name}: no new shot to accept")
        for ext in (".png", ".json"):
            shutil.copy2(new_d / f"{name}{ext}", old_d / f"{name}{ext}")
        print("accepted", name)


if "--accept" in sys.argv:
    accept(sys.argv[sys.argv.index("--accept") + 1:])
    sys.exit(0)

partial = "--partial" in sys.argv
if (new_d / ".partial").exists() and not partial and "--accept" not in sys.argv:
    raise SystemExit("shots-new/ comes from a replay --only run — run a full replay, or pass --partial to look at it")
if partial and "--accept-changed" in sys.argv:
    # --partial hides missing shots; a bulk accept on top would publish old pictures for the steps that never ran.
    raise SystemExit("refusing --partial with --accept-changed — accept reviewed shots by name with --accept")
rows = []
for name in shots:
    v, why = verdict(name)
    if v == "missing":
        if partial:
            continue
        v = "broken"
    rows.append((v, name, why))

if "--accept-changed" in sys.argv:
    broken = [n for v, n, _ in rows if v == "broken"]
    if broken:  # promoting the rest would ship a deck with the OLD picture for the broken task
        raise SystemExit(f"refusing --accept-changed: {len(broken)} broken shot(s) first — {', '.join(broken)}")
    accept([n for v, n, _ in rows if v in ("changed", "new")])
    sys.exit(0)

order = {"broken": 0, "changed": 1, "new": 2, "unchanged": 3}
rows.sort(key=lambda r: (order[r[0]], shots.index(r[1])))
counts = {k: sum(1 for r in rows if r[0] == k) for k in order}
report = [f"# Refresh report — {counts['broken']} broken · {counts['changed']} changed · {counts['new']} new · {counts['unchanged']} unchanged", "",
          "| verdict | shot | why |", "|---|---|---|"] + [f"| {v} | {n} | {w} |" for v, n, w in rows]
(ws / "refresh-report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
print(report[0])
for v, n, w in rows:
    if v != "unchanged":
        print(f"  {v:9} {n}: {w}")
sys.exit(1 if counts["broken"] else 0)
