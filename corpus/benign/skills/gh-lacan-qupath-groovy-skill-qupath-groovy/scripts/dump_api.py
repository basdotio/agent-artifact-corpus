#!/usr/bin/env python3
"""Build grep-friendly API references from the javadoc jars bundled with QuPath.

Usage: python3 dump_api.py [QuPath.app] [out_dir]

One line per member, prefixed with the owning class, so a single grep hit
carries its own context:
    QP.getAnnotationObjects() -> static Collection<PathObject> // Get a list ...
Handles both the Javadoc 17+ (div grid) and Javadoc 11 (table) HTML layouts,
since ImageJ ships docs from the older generator.
"""
import html
import re
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path

DEFAULT_APP = "/Applications/QuPath-0.7.0-x64.app"
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "references" / "api"

# javadoc jars that matter for scripting; others (bioimageio spec, fxtras...) add noise
JARS = [
    "qupath-core-[0-9]*", "qupath-core-processing-*", "qupath-gui-fx-*",
    "qupath-extension-processing-*", "qupath-extension-bioformats-*",
    "qupath-extension-djl-*", "qupath-imglib2-*", "ij-*", "jts-core-*",
]
SKIP_PAGES = ("class-use/", "package-", "index", "overview", "help-doc",
              "allclasses", "allpackages", "deprecated-list", "constant-values",
              "serialized-form", "search", "module-")
SECTIONS = {"field": "F", "constructor": "C", "method": "M", "enum-constant": "E"}


def clean(text):
    text = html.unescape(text).replace("​", "").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def first_sentence(text, limit=180):
    text = clean(text)
    m = re.match(r"(.+?\.)(\s|$)", text)
    text = m.group(1) if m else text
    return text if len(text) <= limit else text[: limit - 1] + "…"


class SummaryParser(HTMLParser):
    """Collects (section, first, second, last) rows from the summary tables."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.section, self.row = [], None, {}
        self.cell, self.depth, self.buf, self.block, self.block_at = None, 0, [], [], None
        self.in_title, self.title, self.in_desc, self.desc_depth = False, "", False, 0
        self.class_desc, self.class_desc_done = [], False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class", "") or ""
        ident = a.get("id") or a.get("name") or ""  # Javadoc 8 anchors use name=
        if tag == "h1" or (tag == "h2" and "title" in cls):
            self.in_title = True
        # section markers: Javadoc 17+ uses ids, Javadoc 8/11 use <a id|name=...>
        for key in SECTIONS:
            dotted = key.replace("-", ".")
            if ident in (f"{key}-summary", f"{dotted}.summary"):
                self.section = key
            if ident in (f"{key}-detail", f"{dotted}.detail"):
                self.section = None
        if ident.startswith(("methods-inherited", "methods.inherited",
                             "fields-inherited", "fields.inherited")):
            self.section = None
        # class description = first block div before any summary
        if (not self.class_desc_done and self.section is None and tag == "div"
                and cls == "block" and not self.rows):
            self.in_desc, self.desc_depth = True, 0
        if self.in_desc and tag == "div":
            self.desc_depth += 1
        if self.cell:
            if tag in ("div", "td", "th"):
                self.depth += 1
                if tag == "div" and cls == "block" and self.block_at is None:
                    self.block_at = self.depth
            return
        if self.section and tag in ("div", "td", "th"):
            tokens = cls.replace("col-", "col").replace("-", "").lower().split()
            kind = next((t for t in tokens if t in
                         ("colfirst", "colsecond", "collast", "colconstructorname", "colone")), None)
            if kind == "colfirst" and self.section == "enum-constant":
                kind = "colconstructorname"  # enum rows have no type column
            if kind:
                self.cell, self.depth, self.buf, self.block, self.block_at = kind, 1, [], [], None
                self.cell_section = self.section

    def handle_endtag(self, tag):
        if tag in ("h1", "h2"):
            self.in_title = False
        if self.in_desc and tag == "div":
            self.desc_depth -= 1
            if self.desc_depth == 0:
                self.in_desc, self.class_desc_done = False, True
        if self.cell and tag in ("div", "td", "th"):
            if self.block_at == self.depth and tag == "div":
                self.block_at = -1  # block closed; ignore any later blocks
            self.depth -= 1
            if self.depth == 0:
                text = clean("".join(self.buf) + " " + "".join(self.block))
                if self.cell in ("colfirst", "colconstructorname"):
                    self.row = {"first": text} if self.cell == "colfirst" else {"first": "", "second": text}
                elif self.cell == "colsecond":
                    self.row["second"] = text
                else:
                    if self.cell == "colone":  # Javadoc 8 constructor
                        self.row = {"first": ""}
                    if "second" not in self.row:  # Javadoc 8: signature and text share a cell
                        self.row["second"] = clean("".join(self.buf))
                        text = clean("".join(self.block))
                    if "second" in self.row:
                        self.rows.append((self.cell_section, self.row.get("first", ""),
                                          self.row["second"], text))
                    self.row = {}
                self.cell = None

    def handle_data(self, data):
        if self.cell:
            (self.block if self.block_at not in (None, -1) else self.buf).append(data)
        if self.in_title:
            self.title += data
        if self.in_desc:
            self.class_desc.append(data)


def write_if_changed(path, text):
    # the repo lives in a synced folder: rewriting identical files triggers sync conflicts
    if not path.exists() or path.read_text() != text:
        path.write_text(text)


def jar_matches(name):
    from fnmatch import fnmatch
    return any(fnmatch(name, p + "-javadoc.jar") or fnmatch(name, p + "javadoc.jar") for p in JARS)


def dump_jar(jar_path, out_dir):
    lines, index = [], []
    with zipfile.ZipFile(jar_path) as z:
        pages = sorted(n for n in z.namelist() if n.endswith(".html")
                       and not any(s in n.rsplit("/", 1)[-1] or s in n for s in SKIP_PAGES))
        for page in pages:
            p = SummaryParser()
            p.feed(z.read(page).decode("utf-8", "replace"))
            fqcn = page[:-5].replace("/", ".")
            if fqcn.startswith("ij.ij."):  # ImageJ jar nests everything under ij/
                fqcn = fqcn[3:]
            parts = fqcn.split(".")
            # keep outer class for nested types: PixelProcessor.Builder, not Builder
            simple = ".".join(parts[next(i for i, x in enumerate(parts) if x[:1].isupper()):])
            kind = clean(p.title).split(" ")[0] if p.title else "Class"
            desc = first_sentence("".join(p.class_desc))
            index.append(f"{fqcn} [{kind}] {desc}")
            lines.append(f"\n## {fqcn} [{kind}]\n{desc}")
            for section, first, second, last in p.rows:
                # skip Javadoc 11 header rows and members scripts cannot call
                if first == "Modifier and Type" or second in ("Constructor", "Method", "Field", "Enum Constant"):
                    continue
                if first.startswith("protected"):
                    continue
                tag = SECTIONS[section]
                sig = re.sub(r"\s*\(\s*", "(", second)
                ret = f" -> {first}" if first else ""
                name = f"new {sig}" if tag == "C" else f"{simple}.{sig}"
                lines.append(f"{tag} {name}{ret} // {first_sentence(last)}")
    stem = re.sub(r"-javadoc\.jar$", "", jar_path.name)
    write_if_changed(out_dir / f"{stem}.md", f"# {stem}\n" + "\n".join(lines) + "\n")
    return stem, index


def main():
    app = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_APP)
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT
    docs = app / "Contents" / "app" / "docs"
    jars = sorted(j for j in docs.glob("*-javadoc.jar") if jar_matches(j.name))
    if not jars:
        sys.exit(f"No javadoc jars found in {docs}")
    out.mkdir(parents=True, exist_ok=True)
    classes = []
    for jar in jars:
        stem, index = dump_jar(jar, out)
        classes += [f"{line}  ({stem}.md)" for line in index]
        print(f"{stem}: {len(index)} classes")
    write_if_changed(out / "CLASSES.md",
        "# Class index (fqcn [kind] summary (file))\n" + "\n".join(sorted(classes)) + "\n")


if __name__ == "__main__":
    main()
