#!/usr/bin/env python3
"""Print the full javadoc of a class member (parameters, units, exceptions).

Usage: python3 show_doc.py <Class> [member] [QuPath.app]
  python3 show_doc.py QP createAnnotationsFromPixelClassifier
  python3 show_doc.py ParticleAnalyzer          # class description only
  python3 show_doc.py PixelProcessor.Builder merger

The API dump only keeps first sentences; use this when units or argument
semantics matter.
"""
import html
import re
import sys
import zipfile
from pathlib import Path

DEFAULT_APP = "/Applications/QuPath-0.7.0-x64.app"


def to_text(fragment):
    fragment = re.sub(r"<(dt|h3|h4|li|tr)[^>]*>", "\n", fragment)
    fragment = re.sub(r"<dd[^>]*>", "\n    ", fragment)
    text = html.unescape(re.sub(r"<[^>]+>", "", fragment)).replace("​", "").replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n", text).strip()


def find_pages(docs, cls):
    page = cls.replace(".", "/") if cls.count(".") and cls[0].islower() else None
    for jar in sorted(docs.glob("*-javadoc.jar")):
        with zipfile.ZipFile(jar) as z:
            for name in z.namelist():
                if "class-use" in name or not name.endswith(".html"):
                    continue
                if (page and name.endswith(page + ".html")) or name.rsplit("/", 1)[-1] == cls + ".html":
                    yield name, z.read(name).decode("utf-8", "replace")


def member_sections(src, member):
    # Javadoc 17+: <section class="detail" id="name(args)">; 8/11: <a id|name="name(args)"> / name-args-
    starts = [m.start() for m in re.finditer(
        rf'<(?:section class="detail"|a) (?:id|name)="{re.escape(member)}[(\-]', src)]
    for start in starts:
        end = min((i for i in (src.find("</section>", start), src.find("</li>", start + 10)) if i > 0),
                  default=start + 4000)
        yield to_text(src[start:end])


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cls, member = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None
    docs = Path(sys.argv[3] if len(sys.argv) > 3 else DEFAULT_APP) / "Contents" / "app" / "docs"
    found = False
    for name, src in find_pages(docs, cls):
        found = True
        print(f"=== {name}")
        if member:
            for text in member_sections(src, member):
                print(text, "\n---")
        else:
            m = re.search(r'<div class="block">(.*?)</div>', src, re.S)
            print(to_text(m.group(1)) if m else "(no description)")
    if not found:
        sys.exit(f"No javadoc page for {cls}; check references/api/CLASSES.md")


if __name__ == "__main__":
    main()
