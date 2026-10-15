#!/usr/bin/env python3
"""Bookkeeping for the marginalia reading skill.

Deterministic chores, so Claude never does date math or file shuffling by hand:

  * creating and locating the reader's journal
  * a small spaced-review queue (Leitner boxes) of "keeper" questions,
    stored in <journal>/review-queue.json
  * the inbox where page photos and scans are dropped
  * copying bundled reading plans into the journal

Commands
  where                                print the journal's location
  init                                 create the journal from the templates (never overwrites)
  due      [--limit N] [--book SLUG]   questions due now, interleaved across books
  add      --book SLUG --question TEXT --key TEXT --source TEXT --result RESULT
  grade    ID RESULT                   reschedule after a rerun (RESULT: got|partial|missed)
  drop     ID                          retire a question that isn't worth keeping
  list     [--book SLUG] [--all]       the queue (active only unless --all)
  stats                                counts for status checks and reflections
  inbox                                new files in the inbox (HEIC photos converted to JPEG)
  archive  FILE... | --all             move processed inbox files to inbox/done/<date>/
  plans                                reading plans bundled with the skill
  add-plan NAME                        copy a bundled plan into the journal
  pages    PDF RANGES [--offset N]     pull printed pages (e.g. 398-405 or 337,395-410) out of a
                                       PDF the reader owns, as files of up to 10 pages (macOS)

Every command accepts --today YYYY-MM-DD for testing. The journal lives in
~/Documents/Marginalia unless MARGINALIA_HOME points elsewhere.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path

try:
    import fcntl
except ImportError:  # Windows has no flock; simultaneous queue writes are rare enough to go unlocked.
    fcntl = None

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_DIR / "templates" / "journal"
PLANS = SKILL_DIR / "plans"
DEFAULT_HOME = Path.home() / "Documents" / "Marginalia"
JOURNAL_DIRS = ("books", "plans", "inbox", "inbox/done")
# Leitner box -> days until the next review. A question answered well while in
# box 5 retires: by then it has survived five spaced recalls over ~3 months.
INTERVALS = {1: 1, 2: 3, 3: 7, 4: 21, 5: 60}
RESULTS = ("got", "partial", "missed")
READABLE = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf", ".txt", ".md"}
HEIC = {".heic", ".heif"}
PDF_HELPER_SRC = SKILL_DIR / "scripts" / "pdftool.swift"
PDF_HELPER = Path.home() / "Library" / "Caches" / "marginalia" / "pdftool"
CHUNK = 10  # Claude Code reads a PDF of up to 10 pages without extra tools
DIGITISH = str.maketrans("OoIl", "0011")  # OCR often prints page numbers like "4O9"


def home() -> Path:
    return Path(os.environ.get("MARGINALIA_HOME", DEFAULT_HOME)).expanduser()


def queue_file() -> Path:
    return home() / "review-queue.json"


@contextmanager
def locked():
    """Serialize queue writes so two commands run at once can't drop an update."""
    if fcntl is None:
        yield
        return
    lock = home() / ".review-queue.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield


def load() -> dict:
    path = queue_file()
    if not path.exists():
        return {"next_id": 1, "items": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"review-queue.json is not valid JSON ({e}). Fix or restore it before continuing.")


def save(data: dict) -> None:
    path = queue_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".review-queue-", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.chmod(tmp, 0o644)  # mkstemp creates 0600; match the rest of the journal
    os.replace(tmp, path)


def find(data: dict, raw_id: str) -> dict:
    try:
        wanted = int(raw_id.lstrip("#"))
    except ValueError:
        sys.exit(f"Not a question id: {raw_id}")
    for item in data["items"]:
        if item["id"] == wanted:
            return item
    sys.exit(f"No question #{wanted} in the queue.")


def apply_result(item: dict, result: str, today: date) -> None:
    box = item["box"]
    if result == "got":
        box += 1
    elif result == "missed":
        box = 1
    # "partial" stays in the same box and comes back at the same interval.
    item["history"].append({"date": today.isoformat(), "result": result})
    if box > max(INTERVALS):
        item["retired"] = today.isoformat()
        item["due"] = None
    else:
        item["box"] = box
        item["due"] = (today + timedelta(days=INTERVALS[box])).isoformat()


def is_due(item: dict, today: date) -> bool:
    return not item.get("retired") and date.fromisoformat(item["due"]) <= today


def describe_when(item: dict, today: date) -> str:
    if item.get("retired"):
        return ("dropped " if item.get("dropped") else "retired ") + item["retired"]
    days = (date.fromisoformat(item["due"]) - today).days
    if days < 0:
        return f"due {item['due']} ({-days}d overdue)"
    if days == 0:
        return "due today"
    return f"due {item['due']} (in {days}d)"


def show(item: dict, today: date) -> None:
    print(f"#{item['id']} · {item['book']} · box {item['box']} · {describe_when(item, today)}")
    print(f"   Q: {item['question']}")
    print(f"   Key: {item['key']}")
    print(f"   From: {item['source']}")


def interleave(items: list[dict], limit: int) -> list[dict]:
    """Round-robin across books so a review mixes subjects."""
    queues: dict[str, list[dict]] = {}
    for item in items:
        queues.setdefault(item["book"], []).append(item)
    picked: list[dict] = []
    while len(picked) < limit and any(queues.values()):
        for book in queues:
            if queues[book] and len(picked) < limit:
                picked.append(queues[book].pop(0))
    return picked


def cmd_where(args, today: date) -> None:
    root = home()
    print(root)
    if not (root / "shelf.md").exists():
        print("(no journal here yet: run init)")


def cmd_init(args, today: date) -> None:
    root = home()
    created = []
    for sub in JOURNAL_DIRS:
        folder = root / sub
        if not folder.exists():
            folder.mkdir(parents=True)
            created.append(f"{sub}/")
    if TEMPLATES.exists():
        for src in sorted(TEMPLATES.rglob("*")):
            if not src.is_file() or src.name.startswith("."):
                continue
            dest = root / src.relative_to(TEMPLATES)
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dest)
                created.append(str(src.relative_to(TEMPLATES)))
    else:
        print(f"(templates not found at {TEMPLATES}; created folders only)")
    if created:
        print(f"Journal ready at {root}")
        for name in created:
            print(f"   + {name}")
    else:
        print(f"Journal already set up at {root}; nothing changed.")


def cmd_due(args, today: date) -> None:
    data = load()
    due = [it for it in data["items"]
           if is_due(it, today) and (not args.book or it["book"] == args.book)]
    if not due:
        print("Nothing due.")
        return
    due.sort(key=lambda it: (it["due"], it["box"], it["id"]))
    picked = interleave(due, args.limit)
    shown = f" (showing {len(picked)})" if len(picked) < len(due) else ""
    print(f"{len(due)} due{shown}:")
    for it in picked:
        show(it, today)


def cmd_add(args, today: date) -> None:
    with locked():
        data = load()
        item = {
            "id": data["next_id"],
            "book": args.book,
            "question": args.question.strip(),
            "key": args.key.strip(),
            "source": args.source.strip(),
            "added": today.isoformat(),
            "box": 1,
            "due": None,
            "history": [],
        }
        apply_result(item, args.result, today)
        data["items"].append(item)
        data["next_id"] += 1
        save(data)
    print(f"Added #{item['id']} ({item['book']}) · next review {item['due']}")


def cmd_grade(args, today: date) -> None:
    with locked():
        data = load()
        item = find(data, args.id)
        if item.get("retired"):
            sys.exit(f"#{item['id']} is already retired.")
        apply_result(item, args.result, today)
        save(data)
    if item.get("retired"):
        print(f"#{item['id']} retired: five spaced recalls, it's yours now.")
    else:
        print(f"#{item['id']} → box {item['box']} · next review {item['due']}")


def cmd_drop(args, today: date) -> None:
    with locked():
        data = load()
        item = find(data, args.id)
        item["retired"] = today.isoformat()
        item["dropped"] = True
        item["due"] = None
        save(data)
    print(f"#{item['id']} dropped.")


def cmd_list(args, today: date) -> None:
    data = load()
    items = [it for it in data["items"]
             if (args.all or not it.get("retired")) and (not args.book or it["book"] == args.book)]
    if not items:
        print("Queue is empty.")
        return
    items.sort(key=lambda it: (bool(it.get("retired")), it.get("due") or "", it["id"]))
    for it in items:
        show(it, today)


def cmd_stats(args, today: date) -> None:
    items = load()["items"]
    active = [it for it in items if not it.get("retired")]
    due = [it for it in active if is_due(it, today)]
    retired = [it for it in items if it.get("retired") and not it.get("dropped")]

    def within(day: str, days: int) -> bool:
        return today - timedelta(days=days) < date.fromisoformat(day) <= today

    def reruns_within(days: int) -> int:
        # history[0] is the answer given in the session that created the question.
        return sum(1 for it in items for h in it["history"][1:] if within(h["date"], days))

    def added_within(days: int) -> int:
        return sum(1 for it in items if within(it["added"], days))

    print(f"Active: {len(active)} · due now: {len(due)} · retired (yours now): {len(retired)}")
    print(f"Reruns answered: last 7 days {reruns_within(7)} · last 30 days {reruns_within(30)}")
    print(f"Keepers added: last 7 days {added_within(7)} · last 30 days {added_within(30)}")
    books = sorted({it["book"] for it in items})
    if books:
        print("By book:")
        for book in books:
            a = sum(1 for it in active if it["book"] == book)
            d = sum(1 for it in due if it["book"] == book)
            r = sum(1 for it in retired if it["book"] == book)
            print(f"   {book}: active {a} · due {d} · retired {r}")


def inbox_dir() -> Path:
    path = home() / "inbox"
    path.mkdir(parents=True, exist_ok=True)
    return path


def done_dir(today: date) -> Path:
    path = inbox_dir() / "done" / today.isoformat()
    path.mkdir(parents=True, exist_ok=True)
    return path


def unique(dest: Path) -> Path:
    if not dest.exists():
        return dest
    for n in range(1, 1000):
        candidate = dest.with_name(f"{dest.stem}-{n}{dest.suffix}")
        if not candidate.exists():
            return candidate
    sys.exit(f"Too many files named like {dest.name}")


def inbox_files() -> list[Path]:
    files = [p for p in inbox_dir().iterdir() if p.is_file() and not p.name.startswith(".")]
    return sorted(files, key=lambda p: p.stat().st_mtime)


def cmd_inbox(args, today: date) -> None:
    ready: list[Path] = []
    skipped: list[tuple[Path, str]] = []
    for p in inbox_files():
        ext = p.suffix.lower()
        if ext in HEIC:
            # iPhone photos: convert so they can be read (macOS sips), then file the original away.
            jpg = unique(p.with_suffix(".jpg"))
            try:
                subprocess.run(["sips", "-s", "format", "jpeg", str(p), "--out", str(jpg)],
                               capture_output=True, check=True)
            except (OSError, subprocess.CalledProcessError):
                skipped.append((p, "could not convert this HEIC photo"))
                continue
            shutil.move(str(p), str(unique(done_dir(today) / p.name)))
            ready.append(jpg)
        elif ext in READABLE:
            ready.append(p)
        else:
            skipped.append((p, f"can't read {ext or 'this'} files"))
    if not ready and not skipped:
        print("Inbox is empty.")
        return
    print(f"{len(ready)} file(s) ready to read, oldest first:")
    for p in ready:
        print(f"   {p}")
    for p, why in skipped:
        print(f"   (skipped {p.name}: {why})")


def cmd_archive(args, today: date) -> None:
    box = inbox_dir().resolve()
    if args.all:
        targets = inbox_files()
    elif args.files:
        targets = []
        for raw in args.files:
            p = Path(raw).expanduser()
            p = (p if p.is_absolute() else box / p).resolve()
            if p.parent != box:
                sys.exit(f"Only files directly inside the inbox can be archived: {raw}")
            if not p.is_file():
                sys.exit(f"Not in the inbox: {raw}")
            targets.append(p)
    else:
        sys.exit("Name the files to archive, or pass --all.")
    if not targets:
        print("Nothing to archive.")
        return
    dest = done_dir(today)
    for p in targets:
        shutil.move(str(p), str(unique(dest / p.name)))
    print(f"Moved {len(targets)} file(s) to {dest}")


def bundled_plans() -> list[Path]:
    return sorted(PLANS.glob("*.md")) if PLANS.exists() else []


def cmd_plans(args, today: date) -> None:
    plans = bundled_plans()
    if not plans:
        print("No bundled reading plans.")
        return
    for p in plans:
        lines = p.read_text(encoding="utf-8").splitlines()
        title = next((line[2:].strip() for line in lines if line.startswith("# ")), p.stem)
        print(f"{p.stem} · {title}")


def cmd_add_plan(args, today: date) -> None:
    src = PLANS / f"{args.name}.md"
    if not src.is_file():
        sys.exit(f"No bundled plan named {args.name!r}. Run `plans` to see them.")
    dest = home() / "plans" / src.name
    if dest.exists():
        print(f"{dest} already exists; left it alone.")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    print(f"Copied {args.name} to {dest}")


def pdf_helper() -> Path:
    if sys.platform != "darwin":
        sys.exit("Reading pages from your own PDFs needs macOS for now. Send photos of the pages instead.")
    if not PDF_HELPER.exists() or PDF_HELPER.stat().st_mtime < PDF_HELPER_SRC.stat().st_mtime:
        if not shutil.which("swiftc"):
            sys.exit("The PDF helper needs Apple's command line tools: run `xcode-select --install`, then try again.")
        PDF_HELPER.parent.mkdir(parents=True, exist_ok=True)
        print("(building the PDF helper; this happens once and takes a few seconds)")
        built = subprocess.run(["swiftc", "-O", str(PDF_HELPER_SRC), "-o", str(PDF_HELPER)],
                               capture_output=True, text=True)
        if built.returncode != 0:
            sys.exit(f"Couldn't build the PDF helper:\n{built.stderr.strip()}")
    return PDF_HELPER


def run_helper(*args) -> str:
    done = subprocess.run([str(pdf_helper()), *map(str, args)], capture_output=True, text=True)
    if done.returncode != 0:
        sys.exit(done.stderr.strip() or "The PDF helper failed.")
    return done.stdout


def head_number(line: str) -> int | None:
    """The printed page number in a running head: its first or last token, if that's a number."""
    tokens = line.split()
    for token in tokens[:1] + tokens[-1:]:
        token = token.strip(".,;:")
        if re.fullmatch(r"[0-9OoIl]{1,4}", token) and any(c.isdigit() for c in token):
            return int(token.translate(DIGITISH))
    return None


def pick_offset(numbers: dict[int, int]) -> int | None:
    """The most common (PDF page - printed page) among pages whose number could be read.

    One misread number can't win: at least two pages have to agree.
    """
    votes = Counter(pdf_page - printed for pdf_page, printed in numbers.items())
    if not votes:
        return None
    offset, count = votes.most_common(1)[0]
    return offset if count >= 2 else None


def parse_ranges(text: str) -> list[tuple[int, int]]:
    cleaned = text.replace("–", "-").replace("—", "-").replace("pp.", "").replace("p.", "")
    ranges = []
    for part in re.split(r"[,;]|\balso\b", cleaned):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"(\d+)\s*(?:-\s*(\d+))?", part)
        if not m or int(m.group(2) or m.group(1)) < int(m.group(1)):
            sys.exit(f"Can't read the page range {text!r}. Use something like 398-405 or 337,395-410.")
        ranges.append((int(m.group(1)), int(m.group(2) or m.group(1))))
    if not ranges:
        sys.exit("Give the printed pages to pull out, e.g. 398-405.")
    return ranges


def cmd_pages(args, today: date) -> None:
    pdf = Path(args.pdf).expanduser().resolve()
    if not pdf.is_file():
        sys.exit(f"No PDF at {pdf}")
    ranges = parse_ranges(args.pages)
    total = int(run_helper("count", pdf).strip())
    out_dir = home() / ".pages"
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_file = out_dir / "offsets.json"
    cache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}

    offset = args.offset
    if offset is None:
        # Read the running heads from just before the first page to well past it, so the
        # front matter (usually under 100 pages) is covered, and let the pages vote.
        first = ranges[0][0]
        numbers = {}
        for row in run_helper("heads", pdf, max(1, first - 5), min(total, first + 100)).splitlines():
            page, *lines = row.split("\t")
            for line in lines:
                number = head_number(line)
                if number is not None:
                    numbers[int(page)] = number
                    break
        offset = pick_offset(numbers)
        if offset is None:
            offset = cache.get(str(pdf))
        if offset is None:
            sys.exit("Couldn't read printed page numbers near there. Pass --offset N, where PDF page = printed page + N.")
    cache[str(pdf)] = offset
    cache_file.write_text(json.dumps(cache, indent=2) + "\n", encoding="utf-8")

    for old in out_dir.glob("*.pdf"):
        old.unlink()
    written = []
    for a, b in ranges:
        if a + offset < 1 or b + offset > total:
            sys.exit(f"Printed pp. {a}-{b} fall outside this PDF ({total} pages, offset {offset:+d}).")
        for start in range(a, b + 1, CHUNK):
            end = min(start + CHUNK - 1, b)
            out = out_dir / f"{pdf.stem}-pp{start}-{end}.pdf"
            run_helper("extract", pdf, start + offset, end + offset, out)
            written.append((out, start, end))
    print(f"{pdf.name}: PDF page = printed page {offset:+d}")
    for out, a, b in written:
        print(f"   {out}  (printed pp. {a}–{b})")


def main() -> None:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--today", type=date.fromisoformat, default=date.today(),
                        help="override today's date (YYYY-MM-DD), for testing")

    parser = argparse.ArgumentParser(description="Bookkeeping for the marginalia reading skill.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("where", parents=[common], help="print the journal's location")
    p.set_defaults(func=cmd_where)

    p = sub.add_parser("init", parents=[common], help="create the journal from the templates")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("due", parents=[common], help="questions due now")
    p.add_argument("--limit", type=int, default=3)
    p.add_argument("--book")
    p.set_defaults(func=cmd_due)

    p = sub.add_parser("add", parents=[common], help="queue a keeper question")
    p.add_argument("--book", required=True, help="book slug, e.g. anna-karenina")
    p.add_argument("--question", required=True, help="self-contained question")
    p.add_argument("--key", required=True, help="short answer key")
    p.add_argument("--source", required=True, help="span and date, e.g. 'Part 1, ch. 12 (2026-10-03)'")
    p.add_argument("--result", required=True, choices=RESULTS, help="how they did on it today")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("grade", parents=[common], help="record a rerun answer")
    p.add_argument("id")
    p.add_argument("result", choices=RESULTS)
    p.set_defaults(func=cmd_grade)

    p = sub.add_parser("drop", parents=[common], help="retire a question that isn't worth keeping")
    p.add_argument("id")
    p.set_defaults(func=cmd_drop)

    p = sub.add_parser("list", parents=[common], help="show the queue")
    p.add_argument("--book")
    p.add_argument("--all", action="store_true", help="include retired and dropped questions")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("stats", parents=[common], help="counts for status checks and reflections")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("inbox", parents=[common], help="list new page files (converts HEIC)")
    p.set_defaults(func=cmd_inbox)

    p = sub.add_parser("archive", parents=[common], help="move processed inbox files to inbox/done/")
    p.add_argument("files", nargs="*")
    p.add_argument("--all", action="store_true", help="archive everything in the inbox")
    p.set_defaults(func=cmd_archive)

    p = sub.add_parser("plans", parents=[common], help="list reading plans bundled with the skill")
    p.set_defaults(func=cmd_plans)

    p = sub.add_parser("add-plan", parents=[common], help="copy a bundled plan into the journal")
    p.add_argument("name", help="plan name, as shown by `plans`")
    p.set_defaults(func=cmd_add_plan)

    p = sub.add_parser("pages", parents=[common], help="pull printed pages out of the reader's own PDF")
    p.add_argument("pdf", help="path to the PDF")
    p.add_argument("pages", help="printed pages, e.g. 398-405 or '337, 395-410'")
    p.add_argument("--offset", type=int, help="PDF page = printed page + OFFSET (found automatically if left out)")
    p.set_defaults(func=cmd_pages)

    args = parser.parse_args()
    args.func(args, args.today)


if __name__ == "__main__":
    main()
