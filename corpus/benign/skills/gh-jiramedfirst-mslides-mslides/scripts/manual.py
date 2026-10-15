"""Compose a user manual from <workspace>/manual.json + manifest.json + shots/.

  python manual.py <workspace>/manual.json                 # combined edition only
  python manual.py <workspace>/manual.json --role viewer   # one role's edition
  python manual.py <workspace>/manual.json --all [--pdf] [--md]   # combined + one per chapter, optional PDF + Markdown

Deck order: cover · agenda · intro slides · per chapter (divider + one slide per manifest item) · reference · closing.
All app wording lives in manual.json (schema: references/content.md); this file holds no app knowledge.
"""
import json, pathlib, shutil, subprocess, sys
# Windows consoles default to a legacy code page; the arrows in our messages would raise UnicodeEncodeError.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import build_manual as B
import renderers as R

HERE = pathlib.Path(__file__).parent


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def for_role(entry, role):
    """An intro/reference entry may say which editions carry it: "roles" (only these) or "skip_roles"."""
    return (role == "all" or "roles" not in entry or role in entry["roles"]) and role not in entry.get("skip_roles", [])


def add(entry):
    if entry.get("type") == "bullets":
        B.bullets_slide(entry["kicker"], entry["title"], entry["lines"], entry.get("notes", ""))
    else:
        B.table_slide(entry["kicker"], entry["title"], entry["header"], entry["rows"], entry["widths"],
                      entry.get("notes", ""), size=entry.get("size", 11))


def edition_names(cfg, roles):
    by_code = {c["code"]: c.get("edition", c["code"]) for c in cfg["chapters"]}
    return [cfg.get("out_name", "User-Manual") + "-" + ("ALL" if r == "all" else by_code.get(r, r)) for r in roles]


def build(cfg, ws, role, out_dir=None):
    chapters = cfg["chapters"] if role == "all" else [c for c in cfg["chapters"] if c["code"] == role]
    if not chapters:
        raise SystemExit(f"--role {role}: no chapter with that code in manual.json")
    items = json.loads((ws / cfg.get("manifest", "manifest.json")).read_text(encoding="utf-8"))
    # A task whose chapter is misspelled or was removed would silently vanish from every edition — refuse instead.
    unknown = sorted({it["chapter"] for it in items} - {c["code"] for c in cfg["chapters"]})
    if unknown:
        raise SystemExit(f"manifest chapters not in manual.json chapters: {unknown}")
    name = edition_names(cfg, [role])[0]
    B.init(cfg, ws, (out_dir or ws / "out") / f"{name}.pptx")

    edition = cfg.get("edition_all", "All roles") if role == "all" else cfg.get("edition_one", "{name} edition").format(name=chapters[0]["name"])
    # "v2 · 2026-01-31": readers holding a printed copy can tell which refresh they have (captured_at = shot date).
    stamp = " · ".join(x for x in (f"v{cfg['version']}" if cfg.get("version") else "", cfg.get("captured_at", "")) if x)
    B.title_slide(cfg["title"], " · ".join(x for x in (cfg.get("subtitle", ""), edition, stamp) if x), cfg.get("cover_note", ""))
    ref_no = str(len(cfg["chapters"]) + 1)  # reference keeps its number in every edition, like the chapters do
    toc = [(cfg.get("toc_intro", "Overview and terms"), "0")] + [(c["name"], c["no"].split()[-1]) for c in chapters]
    if any(for_role(e, role) for e in cfg.get("reference", [])):
        toc.append((cfg.get("toc_reference", "Reference"), ref_no))
    B.list_slide(cfg.get("toc_title", "Contents"), toc)
    for e in cfg.get("intro", []):
        if for_role(e, role):
            add(e)

    for c in chapters:
        chapter = [it for it in items if it["chapter"] == c["code"]]
        if not chapter:
            # A configured role with no task slides would ship an edition with no instructions in it. --draft
            # allows it for a mid-capture preview; a release build refuses.
            if "--draft" in sys.argv:
                continue
            raise SystemExit(f"chapter {c['code']!r} has no task slides in the manifest (use --draft for a preview)")
        # Divider lists the chapter's distinct task names ("… (step 2…)" suffixes folded). The divider body
        # auto-shrinks past ~7 lines (QA saw ~7pt text), so show 6 and say how many more.
        tasks = list(dict.fromkeys(it["task"].split(" (")[0] for it in chapter))
        shown = [(t, "") for t in tasks[:6]]
        if len(tasks) > 6:
            shown.append((cfg.get("more_topics", "and {n} more topics").format(n=len(tasks) - 6), ""))
        B.list_slide(c["name"], shown, f"{c['no']} {c['name']}")
        for it in chapter:
            if len(it["steps"]) != len(json.loads((B.SHOTS / f"{it['shot']}.json").read_text(encoding="utf-8"))["marks"]):
                # Step N must point at box N. A mismatch ships a slide whose numbers lie — refuse, don't warn.
                raise SystemExit(f"{it['shot']}: {len(it['steps'])} steps but a different number of marks")
            B.task_slide(it)

    for e in cfg.get("reference", []):
        if for_role(e, role):
            add(e)
    if cfg.get("closing"):
        cl = cfg["closing"]
        B.title_slide(cl["title"], cl.get("subtitle", ""), cl.get("notes", ""))
    return B.finish()


def render_pdf(pptx):
    """Keynote on macOS (reads .pptx directly), PowerPoint via COM on Windows, else LibreOffice anywhere.
    Keynote wedged (-609/-1708)? Quit it from its menu."""
    pdf = pptx.with_suffix(".pdf")
    pdf.unlink(missing_ok=True)
    if R.has_keynote():
        r = subprocess.run(["osascript", str(HERE / "render.applescript"), str(pptx.resolve()), str(pdf.resolve()), "pdf"],
                           capture_output=True, text=True)
        if r.returncode:
            err = (r.stderr or "").strip()
            if "-1712" in err:  # AppleEvent timeout: Keynote is up but never answers while the display is locked/asleep
                raise SystemExit("Keynote cannot export while the screen is locked or asleep (AppleEvent timeout, -1712) — "
                                 "unlock the Mac and keep it awake (caffeinate -d), then rebuild")
            raise SystemExit(f"Keynote export failed: {err or 'osascript exit ' + str(r.returncode)}")
    elif R.has_powerpoint():
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(HERE / "render.ps1"),
                        str(pptx.resolve()), str(pdf.resolve()), "pdf"], check=True)
    elif R.find_soffice():
        subprocess.run([R.find_soffice(), "--headless", "--convert-to", "pdf", "--outdir", str(pptx.parent), str(pptx)], check=True)
    else:
        print("no PDF renderer (Keynote, PowerPoint or LibreOffice soffice) — PPTX only", file=sys.stderr)
        return None
    print("pdf", pdf)
    return pdf


def export_md(cfg, ws, role, out_dir):
    import export_md as M  # lazy: export_md imports for_role/edition_names from this module
    return M.export(cfg, ws, role, out_dir)


def publish(cfg, ws, staged):
    """Swap a COMPLETE staged build into out/. Only reached after every edition (and PDF) succeeded, so a failed
    refresh leaves out/ holding the last good set. A new version first moves the previous
    version's decks to out/archive/v<old>/; out/.version records what out/ holds."""
    out, ver = ws / "out", str(cfg.get("version", ""))
    out.mkdir(exist_ok=True)
    mark = out / ".version"
    old = mark.read_text(encoding="utf-8").strip() if mark.exists() else ""
    has_decks = any(out.glob("*.pptx"))
    editions = lambda d: [f for ext in ("*.pptx", "*.pdf", "*.md") for f in d.glob(ext)]
    # A set built before `version` was introduced has an empty/missing marker: archive it as "unversioned" rather
    # than letting the first versioned refresh overwrite it.
    if has_decks and old != ver:
        dst = out / "archive" / (f"v{old}" if old else "unversioned")
        dst.mkdir(parents=True, exist_ok=True)
        for f in editions(out) + [p for p in [out / "md-images"] if p.is_dir()]:  # images travel with their .md
            shutil.rmtree(dst / f.name, ignore_errors=True)
            shutil.move(str(f), dst / f.name)
        print("archived previous decks →", dst)
    # A deck at the top of out/ whose EDITION is no longer in manual.json belongs to a removed/renamed chapter: move
    # it aside so out/ holds exactly the current editions, whatever the version. Judge by edition, not by file: a
    # build without --pdf / --md produces no PDF / Markdown, but the editions still exist — those files stay.
    current = {f.name for f in staged.iterdir()}
    live = set(edition_names(cfg, ["all"] + [c["code"] for c in cfg["chapters"]]))
    stale = [f for f in editions(out) if f.stem not in live]
    kept = sorted(f.name for f in editions(out) if f.stem in live and f.name not in current)
    if stale:
        gone = out / "archive" / "removed"
        gone.mkdir(parents=True, exist_ok=True)
        for f in stale:
            shutil.move(str(f), gone / f.name)
        print("moved editions no longer in manual.json →", gone)
    shutil.rmtree(out / "md-images", ignore_errors=True)  # else move() nests the new folder inside the old one
    for f in staged.iterdir():
        shutil.move(str(f), out / f.name)
    staged.rmdir()
    mark.write_text(ver, encoding="utf-8")
    if kept:
        print(f"warning: kept from the previous build (this run did not re-export them — rebuild with --pdf / --md "
              f"before using them, they may not match the new decks): {', '.join(kept)}", file=sys.stderr)


if __name__ == "__main__":
    cfg_path = pathlib.Path(sys.argv[1]).expanduser().resolve()
    cfg, ws = json.loads(cfg_path.read_text(encoding="utf-8")), cfg_path.parent
    codes = [c["code"] for c in cfg["chapters"]]
    names = edition_names(cfg, ["all"] + codes)
    # Two chapters with the same code or edition suffix write the same file — one role's edition would silently
    # replace the other's. Refuse before building anything.
    for label, seq in (("chapter codes", codes), ("edition names", names)):
        dup = sorted({x for x in seq if seq.count(x) > 1})
        if dup:
            raise SystemExit(f"duplicate {label} in manual.json: {dup}")
    roles = ["all"] + codes if "--all" in sys.argv else [arg("--role", "all")]
    # Each edition is a fresh Presentation: build_manual keeps module-level state, so run one process per edition.
    if len(roles) > 1:
        staged = ws / "out" / ".staging"
        shutil.rmtree(staged, ignore_errors=True)
        staged.mkdir(parents=True)
        extra = [a for a in ("--draft", "--md") if a in sys.argv]  # each child edition writes its own .md into staging
        for r in roles:  # the first failing edition aborts before anything reaches out/
            if subprocess.run([sys.executable, __file__, str(cfg_path), "--role", r, "--out-dir", str(staged), *extra]).returncode:
                raise SystemExit(f"edition {r!r} failed — out/ left unchanged (partial build in {staged})")
        if "--pdf" in sys.argv:
            # Exactly the editions built now — a glob would also export a stale deck left by a removed chapter.
            # A failed export raises (check=True) before publish(); None only means "no renderer installed".
            for name in edition_names(cfg, roles):
                render_pdf(staged / f"{name}.pptx")
        if "--draft" in sys.argv:  # a preview may lack whole chapters — it must never replace the release set
            draft = ws / "out" / "draft"
            shutil.rmtree(draft, ignore_errors=True)
            staged.rename(draft)
            print("draft preview →", draft, "(out/ unchanged)")
        else:
            publish(cfg, ws, staged)
    else:
        od = arg("--out-dir")
        out = build(cfg, ws, roles[0], pathlib.Path(od) if od else None)
        if "--pdf" in sys.argv:
            render_pdf(out)
        if "--md" in sys.argv:
            export_md(cfg, ws, roles[0], out.parent)
