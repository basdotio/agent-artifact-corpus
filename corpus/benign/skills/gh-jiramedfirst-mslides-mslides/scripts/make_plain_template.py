"""Generate templates/plain.pptx (and templates/dark.pptx): python-pptx's built-in default template, widened to
16:9, no branding.

  python make_plain_template.py [--theme dark] [<out.pptx>]     # default: ../templates/plain.pptx | dark.pptx

The default template is 4:3 (10" x 7.5"); changing slide_width alone leaves every master/layout placeholder at its
4:3 position, so each placeholder's x and width are scaled to the new 13.333" width as well.
--theme dark swaps the theme's dk1/lt1 (text / background) so every placeholder's inherited text turns light and
the master background (bgRef → bg1 → lt1) turns dark — one edit, no per-layout fills.
"""
import pathlib, re, sys
from pptx import Presentation
from pptx.util import Inches
from pptx.oxml.ns import qn

DARK_BG, DARK_INK = "1B1F24", "E8EAED"

dark = "--theme" in sys.argv and sys.argv[sys.argv.index("--theme") + 1] == "dark"
rest = [a for i, a in enumerate(sys.argv[1:], 1) if a != "--theme" and sys.argv[i - 1] != "--theme"]
out = pathlib.Path(rest[0]) if rest else pathlib.Path(__file__).resolve().parents[1] / "templates" / ("dark.pptx" if dark else "plain.pptx")
prs = Presentation()
k = Inches(13.333) / prs.slide_width
prs.slide_width = Inches(13.333)
for master in prs.slide_masters:
    for owner in [master, *master.slide_layouts]:
        # Only shapes with their OWN xfrm: a layout placeholder without one inherits the (already scaled) master
        # position, and writing through python-pptx's inherited getters would pin a broken partial xfrm on it.
        for xfrm in owner._element.iter(qn("a:xfrm")):
            off, ext = xfrm.find(qn("a:off")), xfrm.find(qn("a:ext"))
            if off is not None and ext is not None:
                off.set("x", str(int(int(off.get("x")) * k)))
                ext.set("cx", str(int(int(ext.get("cx")) * k)))
    if dark:
        theme = master.part.part_related_by("http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme")
        xml = theme.blob.decode("utf8")
        for tag, val in (("dk1", DARK_INK), ("lt1", DARK_BG)):  # sysClr (windowText/window) → fixed srgbClr
            xml = re.sub(rf"<a:{tag}>.*?</a:{tag}>", f'<a:{tag}><a:srgbClr val="{val}"/></a:{tag}>', xml, flags=re.S)
        theme._blob = xml.encode("utf8")
out.parent.mkdir(parents=True, exist_ok=True)
prs.save(out)
print(out, f"{out.stat().st_size / 1e3:.0f} KB")
