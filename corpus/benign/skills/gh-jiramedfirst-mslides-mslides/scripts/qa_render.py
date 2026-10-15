"""QA pages at a resolution where 1-4 px gaps and badge overlaps are judgeable.

  python qa_render.py <workspace>/manual.json [outdir] [--edition ALL] [--dpi 200]
  python qa_render.py <deck.pdf> [outdir] [--dpi 200]

Rasterises the edition's PDF (vector, so any dpi is exact) with poppler's pdftoppm into <outdir>/s-NN.png,
default <workspace>/qa-render. Keynote's own PNG export is fixed at 960x540 and cannot be raised, which is why QA
works from the PDF: build it first with `manual.py --all --pdf`. 200 dpi = ~2700 px per 13.33" slide.
"""
import json, pathlib, shutil, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from manual import arg, edition_names


def pdftoppm():
    return shutil.which("pdftoppm")


def render(pdf, out_dir, dpi=200):
    exe = pdftoppm()
    if not exe:
        raise SystemExit("pdftoppm not found — install poppler (macOS: brew install poppler · Debian/Ubuntu: apt install "
                         "poppler-utils · Windows: scoop/choco install poppler), or render.applescript/render.ps1 … png "
                         "for low-resolution pages")
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([exe, "-r", str(dpi), "-png", str(pdf), str(out_dir / "s")], check=True)
    pages = sorted(out_dir.glob("s-*.png"))
    print(f"{len(pages)} pages at {dpi} dpi → {out_dir}")
    return pages


if __name__ == "__main__":
    pos = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and sys.argv[i - 1] not in ("--dpi", "--edition")]
    if not pos:
        raise SystemExit(__doc__)
    src = pathlib.Path(pos[0]).expanduser().resolve()
    if src.suffix == ".json":
        cfg = json.loads(src.read_text(encoding="utf-8"))
        code = arg("--edition", "ALL")
        role = "all" if code.lower() == "all" else code
        pdf = src.parent / "out" / f"{edition_names(cfg, [role])[0]}.pdf"
        default_out = src.parent / "qa-render"
    else:
        pdf, default_out = src, src.parent / "qa-render"
    if not pdf.exists():
        raise SystemExit(f"{pdf} not found — build it first: python manual.py <ws>/manual.json --all --pdf")
    render(pdf, pathlib.Path(pos[1]).expanduser().resolve() if len(pos) > 1 else default_out, int(arg("--dpi", 200)))
