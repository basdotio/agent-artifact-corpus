# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Embed the TWK Everett / TWK Lausanne font faces used by sow-template.docx
into the .docx itself (ECMA-376 §17.6.2 obfuscated font embedding), so the
document renders correctly on machines that don't have these fonts installed.

Only the font *names* actually referenced in document.xml / styles.xml are
embedded, each as a single "regular" face — table header rows and bold labels
get their own named face (TWK Lausanne 550) rather than a synthetic/faux bold
of TWK Lausanne 300, and the template never asks Word for italics.

    uv run embed_fonts.py [TEMPLATE.docx]
"""

import argparse
import re
import shutil
import sys
import uuid
import zipfile
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
DEFAULT_TEMPLATE = ASSETS / "sow-template.docx"
FONTS_DIR = ASSETS / "fonts"

# Font family name (as written into w:ascii/w:rFonts) -> source .otf file.
FONT_FILES = {
    "TWK Everett Black": FONTS_DIR / "TWKEverett" / "TWKEverett-Black.otf",
    "TWK Everett Bold": FONTS_DIR / "TWKEverett" / "TWKEverett-Bold.otf",
    "TWK Everett Medium": FONTS_DIR / "TWKEverett" / "TWKEverett-Medium.otf",
    "TWK Lausanne 300": FONTS_DIR / "TWKLausanne" / "TWKLausanne-300.otf",
    "TWK Lausanne 550": FONTS_DIR / "TWKLausanne" / "TWKLausanne-550.otf",
}

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PR_FONT_TABLE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/fontTable"
PR_FONT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/font"
FONT_TABLE_CT = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.fontTable+xml"
)
OBFUSCATED_FONT_CT = "application/x-font-data"


def guid_bytes(g: uuid.UUID) -> bytes:
    """The 16 bytes of the GUID in the literal left-to-right order it is
    written in its string form ("XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"),
    i.e. plain big-endian hex decoding — not .NET's mixed-endian struct
    layout. This is the order the OOXML font-obfuscation key is defined in.
    """
    return g.bytes


def obfuscate(data: bytes, key: bytes) -> bytes:
    """XOR the font's first 32 bytes with the 16-byte key, reversed per
    ECMA-376 §17.6.2.1: byte i is XORed with key[0x0F - (i % 0x10)].
    """
    out = bytearray(data)
    for i in range(32):
        out[i] ^= key[0x0F - (i % 0x10)]
    return bytes(out)


def used_font_names(docx_path: Path) -> set[str]:
    """Every w:ascii="..." font name referenced anywhere in the package."""
    names = set()
    with zipfile.ZipFile(docx_path) as z:
        for info in z.infolist():
            if info.filename.startswith("word/") and info.filename.endswith(".xml"):
                text = z.read(info.filename).decode("utf-8")
                names.update(re.findall(r'w:ascii="([^"]+)"', text))
    return names


def font_table_xml(entries):
    """entries: list of (name, rel_id, guid_str)."""
    fonts = "\n".join(
        f'    <w:font w:name="{name}">\n'
        f'      <w:embedRegular r:id="{rel_id}" w:fontKey="{guid_str}"/>\n'
        f"    </w:font>"
        for name, rel_id, guid_str in entries
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<w:fonts xmlns:w="{W_NS}" xmlns:r="{R_NS}">\n{fonts}\n</w:fonts>\n'
    )


def font_rels_xml(entries):
    rels = "\n".join(
        f'  <Relationship Id="{rel_id}" '
        f'Type="{PR_FONT}" Target="fonts/{rel_id}.fntdata"/>'
        for _, rel_id, _ in entries
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        f"{rels}\n</Relationships>\n"
    )


def add_document_rel(rels_xml: str) -> str:
    if PR_FONT_TABLE in rels_xml:
        return rels_xml
    existing_ids = [int(m) for m in re.findall(r'Id="rId(\d+)"', rels_xml)]
    new_id = f"rId{max(existing_ids, default=0) + 1}"
    rel = f'<Relationship Id="{new_id}" Type="{PR_FONT_TABLE}" Target="fontTable.xml"/>'
    return rels_xml.replace("</Relationships>", f"{rel}</Relationships>")


def add_settings_flag(settings_xml: str) -> str:
    if "embedTrueTypeFonts" in settings_xml:
        return settings_xml
    tag = '<w:embedTrueTypeFonts w:val="true"/><w:embedOnlyUsedFonts w:val="true"/>'
    # Insert right after the opening <w:settings ...> tag's closing '>'.
    return re.sub(r"(<w:settings\b[^>]*>)", r"\1" + tag, settings_xml, count=1)


def add_content_types(ct_xml: str) -> str:
    additions = []
    if 'Extension="fntdata"' not in ct_xml:
        additions.append(f'<Default Extension="fntdata" ContentType="{OBFUSCATED_FONT_CT}"/>')
    if "fontTable.xml" not in ct_xml:
        additions.append(
            f'<Override PartName="/word/fontTable.xml" ContentType="{FONT_TABLE_CT}"/>'
        )
    if not additions:
        return ct_xml
    return ct_xml.replace("</Types>", "".join(additions) + "</Types>")


def embed(template: Path, out: Path) -> dict:
    names = used_font_names(template)
    needed = {n: p for n, p in FONT_FILES.items() if n in names}
    if not needed:
        raise SystemExit(f"none of the known font names appear in {template}")

    entries = []
    font_blobs = {}
    for i, (name, src) in enumerate(sorted(needed.items()), start=1):
        rel_id = f"fontId{i}"
        g = uuid.uuid4()
        guid_str = f"{{{str(g).upper()}}}"
        data = src.read_bytes()
        font_blobs[rel_id] = obfuscate(data, guid_bytes(g))
        entries.append((name, rel_id, guid_str))

    with zipfile.ZipFile(template) as zin:
        items = {info.filename: zin.read(info.filename) for info in zin.infolist()}

    items["word/fontTable.xml"] = font_table_xml(entries).encode("utf-8")
    items["word/_rels/fontTable.xml.rels"] = font_rels_xml(entries).encode("utf-8")
    for rel_id, blob in font_blobs.items():
        items[f"word/fonts/{rel_id}.fntdata"] = blob

    doc_rels_path = "word/_rels/document.xml.rels"
    items[doc_rels_path] = add_document_rel(items[doc_rels_path].decode("utf-8")).encode("utf-8")

    settings_path = "word/settings.xml"
    items[settings_path] = add_settings_flag(items[settings_path].decode("utf-8")).encode("utf-8")

    items["[Content_Types].xml"] = add_content_types(
        items["[Content_Types].xml"].decode("utf-8")
    ).encode("utf-8")

    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in items.items():
            zout.writestr(name, data)

    return {"embedded": sorted(needed), "unmatched_names": sorted(names - FONT_FILES.keys())}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("template", nargs="?", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--out", type=Path, help="defaults to overwriting the template in place")
    args = parser.parse_args()
    out = args.out or args.template
    tmp = out.with_suffix(".tmp.docx")
    result = embed(args.template, tmp)
    shutil.move(tmp, out)
    print(f"wrote {out}")
    print("embedded:", ", ".join(result["embedded"]))
    if result["unmatched_names"]:
        print("not embedded (no mapped font file):", ", ".join(result["unmatched_names"]))


if __name__ == "__main__":
    sys.exit(main())
