"""Markdown edition of a manual — the same content as the deck, for a wiki or a repo README.

  python export_md.py <workspace>/manual.json [--role <code> | --all] [--out-dir <dir>]
  (manual.py --md calls this for every edition it builds)

Per edition: <out>/<out_name>-<Edition>.md with the intro tables, one H2 per chapter, one H3 per task slide
(steps, the shot cropped to the slide's own crop window with the numbered boxes drawn, tip), then the reference
tables. Images go to <out>/md-images/<shot>.png and are shared by every edition.
"""
import json, pathlib, sys
from PIL import Image
import build_manual as B
from overlay import draw_marks
from manual import arg, for_role, edition_names


def cell(v):
    return str(v).replace("|", "\\|").replace("\n", " ")


def table(e):
    head = "| " + " | ".join(cell(h) for h in e["header"]) + " |"
    return [head, "|" + "---|" * len(e["header"])] + ["| " + " | ".join(cell(v) for v in r) + " |" for r in e["rows"]]


def entry(e):
    lines = [f"## {e['title']}", ""]
    if e.get("type") == "bullets":
        lines += [f"{i}. {l}" for i, l in enumerate(e["lines"], 1)]
    else:
        lines += table(e)
    return lines + [""]


def shot_image(shots, name, out_dir):
    """The shot cropped exactly like the slide (same crop_window call as task_slide), boxes drawn first so the
    crop can never cut a badge off. Editions share images; always rewritten, so a single-edition rebuild after a
    re-capture never keeps a stale picture."""
    img_dir = out_dir / "md-images"
    img_dir.mkdir(parents=True, exist_ok=True)
    dst = img_dir / f"{name}.png"
    meta = {**json.loads((shots / f"{name}.json").read_text(encoding="utf-8")), "name": name}
    with Image.open(shots / f"{name}.png") as im:
        im = im.convert("RGB")
        x, y, w, h = B.crop_window(meta, img=im)
        draw_marks(im, meta["marks"]).crop((int(x), int(y), int(x + w), int(y + h))).save(dst)
    return dst


def export(cfg, ws, role, out_dir):
    chapters = cfg["chapters"] if role == "all" else [c for c in cfg["chapters"] if c["code"] == role]
    items = json.loads((ws / cfg.get("manifest", "manifest.json")).read_text(encoding="utf-8"))
    shots = ws / cfg.get("shots", "shots")
    t = cfg["template"]
    tip_label = t.get("tip_label", cfg.get("tip_label", "Tip: ")).rstrip(": ")
    edition = cfg.get("edition_all", "All roles") if role == "all" else cfg.get("edition_one", "{name} edition").format(name=chapters[0]["name"])
    stamp = " · ".join(x for x in (cfg.get("subtitle", ""), edition, f"v{cfg['version']}" if cfg.get("version") else "", cfg.get("captured_at", "")) if x)
    out = [f"# {cfg['title']}", "", stamp, ""]
    for e in cfg.get("intro", []):
        if for_role(e, role):
            out += entry(e)
    for c in chapters:
        out += [f"## {c['no']} · {c['name']}", ""]
        for it in (i for i in items if i["chapter"] == c["code"]):
            out += [f"### {it['task']}", ""] + [f"{n}. {s}" for n, s in enumerate(it["steps"], 1)] + [""]
            out += [f"![{it['task']}](md-images/{shot_image(shots, it['shot'], out_dir).name})", ""]
            if it.get("tip"):
                out += [f"> **{tip_label}:** {it['tip']}", ""]
    for e in cfg.get("reference", []):
        if for_role(e, role):
            out += entry(e)
    dst = out_dir / f"{edition_names(cfg, [role])[0]}.md"
    dst.write_text("\n".join(out), encoding="utf8")
    print(dst)
    return dst


if __name__ == "__main__":
    cfg_path = pathlib.Path(sys.argv[1]).expanduser().resolve()
    cfg, ws = json.loads(cfg_path.read_text(encoding="utf-8")), cfg_path.parent
    roles = ["all"] + [c["code"] for c in cfg["chapters"]] if "--all" in sys.argv else [arg("--role", "all")]
    out_dir = pathlib.Path(arg("--out-dir", ws / "out"))
    out_dir.mkdir(parents=True, exist_ok=True)
    for r in roles:
        export(cfg, ws, r, out_dir)
