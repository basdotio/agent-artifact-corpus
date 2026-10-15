"""
OneNote MCP Server (Local Files)
=================================
An MCP (Model Context Protocol) server that reads local OneNote (.one) files
directly from disk and writes to OneNote via the COM API.
No Azure registration or authentication needed.

Reading: parses backup files at:
    C:\\Users\\<user>\\AppData\\Local\\Microsoft\\OneNote\\16.0\\Backup\\

Writing: uses the OneNote COM API via PowerShell (requires OneNote desktop app).

It exposes tools for Claude Code to:
    - List all notebooks and sections
    - Read page text content
    - Search across all pages
    - Create new pages in any notebook/section
    - Append content to existing pages

Prerequisites:
    pip install "mcp[cli]" pyOneNote
    (or: uv add "mcp[cli]" pyOneNote)
    + OneNote desktop app (for write features)

Usage with Claude Code:
    claude mcp add --transport stdio onenote -- uv --directory "path/to/this/project" run server.py
"""

import logging
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

# Ensure dependencies in local .venv are always resolvable regardless of which python binary executes server.py
import site
_venv_site = Path(__file__).parent / ".venv" / "Lib" / "site-packages"
if _venv_site.exists():
    site.addsitedir(str(_venv_site))
    for sub in ("win32", "win32/lib", "pywin32_system32"):
        p = _venv_site / sub
        if p.exists() and str(p) not in sys.path:
            sys.path.insert(0, str(p))
    p32 = _venv_site / "pywin32_system32"
    if p32.exists():
        try:
            os.add_dll_directory(str(p32))
        except (AttributeError, OSError):
            pass
        os.environ["PATH"] = str(p32) + os.pathsep + os.environ.get("PATH", "")

try:
    from pyOneNote.OneDocument import OneDocment
except ImportError:
    OneDocment = None

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _find_default_backup_dir() -> Path:
    """Dynamically resolve the OneNote backup directory across Windows editions and users."""
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        roaming = os.environ.get("APPDATA", "")
        local_appdata = str(Path(roaming).parent / "Local") if roaming else ""

    if local_appdata:
        # Check standard Office versions: 16.0 (2016/2019/2021/365), 15.0 (2013)
        for ver in ("16.0", "15.0"):
            candidate = Path(local_appdata) / "Microsoft" / "OneNote" / ver / "Backup"
            if candidate.exists():
                return candidate
        return Path(local_appdata) / "Microsoft" / "OneNote" / "16.0" / "Backup"

    return Path(tempfile.gettempdir())


DEFAULT_BACKUP_DIR = _find_default_backup_dir()

ONENOTE_DIR = Path(
    os.environ.get("ONENOTE_BACKUP_DIR", str(DEFAULT_BACKUP_DIR))
)

# ---------------------------------------------------------------------------
# Logging (to stderr so it doesn't break stdio MCP transport)
# ---------------------------------------------------------------------------

LOG_FILE = os.path.join(tempfile.gettempdir(), "onenote_mcp.log")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger("onenote-mcp")
log.info("Log file: %s", LOG_FILE)

# ---------------------------------------------------------------------------
# OneNote file parsing helpers
# ---------------------------------------------------------------------------


def _discover_notebooks() -> dict[str, dict]:
    """
    Scan the OneNote backup directory and build a notebook -> section -> files map.

    Returns a dict like:
    {
        "My Notebook": {
            "path": Path(...),
            "sections": {
                "Algorithm": {
                    "files": [Path("Algorithm (On 1-4-2026).one"), ...],
                    "latest": Path(...)   # most recently modified
                },
                ...
            }
        },
        ...
    }
    """
    if not ONENOTE_DIR.exists():
        log.error("OneNote backup directory not found: %s", ONENOTE_DIR)
        return {}

    notebooks = {}
    for notebook_dir in ONENOTE_DIR.iterdir():
        if not notebook_dir.is_dir():
            continue

        notebook_name = notebook_dir.name
        sections: dict[str, dict] = {}

        # Walk all .one files in this notebook (including subdirectories)
        for one_file in notebook_dir.rglob("*.one"):
            # Skip recycle bin
            if "RecycleBin" in str(one_file):
                continue

            # Extract the base section name (strip the date suffix)
            # e.g. "Algorithm (On 1-4-2026).one" -> "Algorithm"
            # e.g. "Python.one (On 12-6-2025).one" -> "Python"
            fname = one_file.name
            # Remove .one extension(s) and date suffixes
            section_name = re.sub(r"\.one$", "", fname)
            section_name = re.sub(r"\s*\(On \d+-\d+-\d+\)$", "", section_name)
            section_name = re.sub(r"\.one$", "", section_name)  # handle double .one
            section_name = section_name.strip()

            if not section_name:
                section_name = "(unnamed)"

            # Build relative path for context (subfolder within notebook)
            rel_parts = one_file.parent.relative_to(notebook_dir).parts
            if rel_parts:
                section_key = "/".join(rel_parts) + "/" + section_name
            else:
                section_key = section_name

            if section_key not in sections:
                sections[section_key] = {"files": [], "latest": None}

            sections[section_key]["files"].append(one_file)

        # For each section, determine the latest (most recently modified) file
        for sec_info in sections.values():
            sec_info["files"].sort(key=lambda p: p.stat().st_mtime, reverse=True)
            sec_info["latest"] = sec_info["files"][0]

        if sections:
            notebooks[notebook_name] = {
                "path": notebook_dir,
                "sections": sections,
            }

    return notebooks


def _parse_one_file(filepath: Path) -> list[str]:
    """
    Parse a .one file and extract all text content.

    Returns a list of text strings found in the file.
    """
    texts = []
    try:
        with open(filepath, "rb") as f:
            doc = OneDocment(f)

        props = doc.get_properties()
        for prop in props:
            ptype = prop.get("type", "")
            val = prop.get("val", {})
            if not isinstance(val, dict):
                continue

            # Extract RichEditTextUnicode (the actual text content)
            text = val.get("RichEditTextUnicode", "")
            if text and isinstance(text, str) and text.strip():
                texts.append(text.strip())

    except Exception as e:
        log.warning("Failed to parse %s: %s", filepath, e)

    return texts


def _get_page_titles_from_props(filepath: Path) -> list[str]:
    """Extract page titles from a .one file."""
    titles = []
    try:
        with open(filepath, "rb") as f:
            doc = OneDocment(f)

        props = doc.get_properties()
        for prop in props:
            if prop.get("type") == "jcidTitleNode":
                val = prop.get("val", {})
                if isinstance(val, dict):
                    text = val.get("RichEditTextUnicode", "")
                    if text and text.strip():
                        titles.append(text.strip())
    except Exception as e:
        log.warning("Failed to extract titles from %s: %s", filepath, e)

    return titles


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP("onenote")


@mcp.tool()
async def list_notebooks() -> str:
    """List all locally available OneNote notebooks.

    Shows notebook names and how many sections each one has.
    """
    notebooks = _discover_notebooks()
    if not notebooks:
        return f"No notebooks found in {ONENOTE_DIR}"

    lines = []
    for name, info in sorted(notebooks.items()):
        section_count = len(info["sections"])
        lines.append(f"- {name}  ({section_count} sections)")
    return "\n".join(lines)


@mcp.tool()
async def list_sections(notebook_name: str) -> str:
    """List all sections in a specific notebook.

    Args:
        notebook_name: The name of the notebook (from list_notebooks).
    """
    notebooks = _discover_notebooks()
    if notebook_name not in notebooks:
        # Try case-insensitive match
        for key in notebooks:
            if key.lower() == notebook_name.lower():
                notebook_name = key
                break
        else:
            available = ", ".join(sorted(notebooks.keys()))
            return f"Notebook '{notebook_name}' not found. Available: {available}"

    sections = notebooks[notebook_name]["sections"]
    lines = []
    for sec_name, sec_info in sorted(sections.items()):
        latest = sec_info["latest"]
        size_kb = latest.stat().st_size / 1024
        lines.append(f"- {sec_name}  ({size_kb:.0f} KB)")
    return "\n".join(lines)


@mcp.tool()
async def read_section(notebook_name: str, section_name: str) -> str:
    """Read all text content from a specific section of a notebook.

    Args:
        notebook_name: The name of the notebook.
        section_name: The name of the section (from list_sections).
    """
    notebooks = _discover_notebooks()

    # Case-insensitive notebook match
    nb = None
    for key, val in notebooks.items():
        if key.lower() == notebook_name.lower():
            nb = val
            break
    if nb is None:
        available = ", ".join(sorted(notebooks.keys()))
        return f"Notebook '{notebook_name}' not found. Available: {available}"

    # Case-insensitive section match
    sec_info = None
    for key, val in nb["sections"].items():
        if key.lower() == section_name.lower():
            sec_info = val
            break
    if sec_info is None:
        available = ", ".join(sorted(nb["sections"].keys()))
        return f"Section '{section_name}' not found. Available: {available}"

    filepath = sec_info["latest"]
    texts = _parse_one_file(filepath)

    if not texts:
        return f"No text content found in section '{section_name}'."

    return "\n\n".join(texts)


@mcp.tool()
async def search_notes(query: str) -> str:
    """Search for text across ALL notebooks and sections.

    Searches through the text content of every section for the given query.
    Returns matching sections with a snippet of the matched text.

    Args:
        query: The text to search for (case-insensitive).
    """
    query_lower = query.lower()
    notebooks = _discover_notebooks()
    results = []

    for nb_name, nb_info in sorted(notebooks.items()):
        for sec_name, sec_info in sorted(nb_info["sections"].items()):
            filepath = sec_info["latest"]
            texts = _parse_one_file(filepath)

            for text in texts:
                if query_lower in text.lower():
                    # Build a snippet around the match
                    idx = text.lower().index(query_lower)
                    start = max(0, idx - 80)
                    end = min(len(text), idx + len(query) + 80)
                    snippet = text[start:end].strip()
                    if start > 0:
                        snippet = "..." + snippet
                    if end < len(text):
                        snippet = snippet + "..."

                    results.append(
                        f"[{nb_name} / {sec_name}]\n  {snippet}"
                    )

    if not results:
        return f"No results found for '{query}'."

    header = f"Found {len(results)} match(es) for '{query}':\n\n"
    return header + "\n\n".join(results[:30])  # limit to 30 results


@mcp.tool()
async def list_all_sections() -> str:
    """List ALL sections across ALL notebooks.

    Useful for getting a complete overview of everything in your OneNote.
    """
    notebooks = _discover_notebooks()
    if not notebooks:
        return f"No notebooks found in {ONENOTE_DIR}"

    lines = []
    for nb_name, nb_info in sorted(notebooks.items()):
        lines.append(f"\n## {nb_name}")
        for sec_name, sec_info in sorted(nb_info["sections"].items()):
            latest = sec_info["latest"]
            size_kb = latest.stat().st_size / 1024
            lines.append(f"  - {sec_name}  ({size_kb:.0f} KB)")

    return "\n".join(lines)


@mcp.tool()
async def get_notebook_summary(notebook_name: str) -> str:
    """Get a summary of a notebook: its sections and a preview of each section's content.

    Args:
        notebook_name: The name of the notebook.
    """
    notebooks = _discover_notebooks()

    nb = None
    for key, val in notebooks.items():
        if key.lower() == notebook_name.lower():
            nb = val
            notebook_name = key
            break
    if nb is None:
        available = ", ".join(sorted(notebooks.keys()))
        return f"Notebook '{notebook_name}' not found. Available: {available}"

    lines = [f"# {notebook_name}\n"]

    for sec_name, sec_info in sorted(nb["sections"].items()):
        filepath = sec_info["latest"]
        texts = _parse_one_file(filepath)

        lines.append(f"## {sec_name}")
        if texts:
            # Show first ~200 chars as preview
            preview = " | ".join(texts)
            if len(preview) > 200:
                preview = preview[:200] + "..."
            lines.append(f"  Preview: {preview}")
        else:
            lines.append("  (no text content)")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Rich HTML -> OneNote XML Converter
# ---------------------------------------------------------------------------

ONE_NS = "http://schemas.microsoft.com/office/onenote/2013/onenote"

HEADING_FONT_SIZES = {
    "h1": 24, "h2": 18, "h3": 14, "h4": 13, "h5": 12, "h6": 11
}


# ---------------------------------------------------------------------------
# HTML to OneNote OE XML Converter (DOM-based with nested outlines & tables)
# ---------------------------------------------------------------------------

class _HtmlNode:
    """Lightweight DOM node for HTML structure parsing."""
    def __init__(self, tag: str, attrs=None):
        self.tag = tag.lower()
        self.attrs = dict(attrs) if attrs else {}
        self.children = []


class _TreeBuilder(HTMLParser):
    """Parses HTML into a lightweight DOM tree of _HtmlNode objects."""
    def __init__(self):
        super().__init__()
        self.root = _HtmlNode("root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = _HtmlNode(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in ("hr", "br", "img", "meta", "link", "input"):
            self.stack.append(node)

    def handle_endtag(self, tag):
        tag = tag.lower()
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                self.stack = self.stack[:i]
                break

    def handle_data(self, data):
        if self.stack:
            self.stack[-1].children.append(data)

    def handle_entityref(self, name):
        entities = {
            "amp": "&amp;", "lt": "&lt;", "gt": "&gt;", "quot": "&quot;",
            "apos": "&#39;", "nbsp": "&nbsp;", "mdash": "—", "ndash": "–",
            "bull": "•", "copy": "©", "reg": "®", "trade": "™"
        }
        val = entities.get(name, f"&{name};")
        if self.stack:
            self.stack[-1].children.append(val)

    def handle_charref(self, name):
        try:
            char = chr(int(name[1:], 16)) if name.startswith("x") else chr(int(name))
            if self.stack:
                self.stack[-1].children.append(char)
        except (ValueError, OverflowError):
            if self.stack:
                self.stack[-1].children.append(f"&#{name};")


def _get_inner_html(node: _HtmlNode) -> str:
    """Serialize inline formatted HTML inside a node for OneNote CDATA."""
    res = []
    for c in node.children:
        if isinstance(c, str):
            res.append(c)
        elif isinstance(c, _HtmlNode):
            if c.tag in ("b", "strong"):
                res.append(f"<b>{_get_inner_html(c)}</b>")
            elif c.tag in ("i", "em"):
                res.append(f"<i>{_get_inner_html(c)}</i>")
            elif c.tag == "u":
                res.append(f"<u>{_get_inner_html(c)}</u>")
            elif c.tag == "span":
                style = c.attrs.get("style", "")
                res.append(f'<span style="{style}">{_get_inner_html(c)}</span>')
            elif c.tag == "a":
                href = c.attrs.get("href", "")
                res.append(f'<a href="{href}">{_get_inner_html(c)}</a>')
            elif c.tag == "br":
                res.append("<br />")
            elif c.tag == "code":
                style = c.attrs.get("style", "color:#9C4100;")
                res.append(f'<span style="font-family:Consolas, monospace;{style}">{_get_inner_html(c)}</span>')
            else:
                res.append(_get_inner_html(c))
    return "".join(res)


def _get_raw_text(node: _HtmlNode) -> str:
    """Extract raw text recursively from a node."""
    res = []
    for c in node.children:
        if isinstance(c, str):
            res.append(c)
        elif isinstance(c, _HtmlNode):
            res.append(_get_raw_text(c))
    return "".join(res)


def _html_to_onenote_xml(html_str: str) -> str:
    """
    Convert an HTML string to structured OneNote OE XML.
    Supports:
    - Headings (H1=24pt, H2=18pt, H3=14pt) with bold weight and dark navy accents
    - Minimum 12.0pt font size for all body paragraphs and list items
    - True hierarchical sub-bullets via native nested <one:OEChildren>
    - Native grid tables via <one:Table bordersVisible="true"> with styled header rows
    - Shaded monospace code blocks (<pre><code>) with Consolas font and multi-language color accents
    """
    parser = _TreeBuilder()
    parser.feed(html_str)
    root = parser.root

    oe_list = []

    def spacer() -> str:
        return '<one:OE><one:T><![CDATA[<span style="font-size:6.0pt;">&nbsp;</span>]]></one:T></one:OE>'

    def process_nodes(nodes, list_depth=0):
        for n in nodes:
            if isinstance(n, str):
                continue
            tag = n.tag

            if tag == "h1":
                text = _get_inner_html(n).strip()
                if text:
                    oe_list.append(spacer())
                    oe_list.append(f'<one:OE><one:T><![CDATA[<span style="font-size:24.0pt;font-weight:bold;color:#003366;">{text}</span>]]></one:T></one:OE>')
                    oe_list.append(spacer())

            elif tag == "h2":
                text = _get_inner_html(n).strip()
                if text:
                    oe_list.append(spacer())
                    oe_list.append(f'<one:OE><one:T><![CDATA[<span style="font-size:18.0pt;font-weight:bold;color:#004080;">{text}</span>]]></one:T></one:OE>')
                    oe_list.append(spacer())

            elif tag == "h3":
                text = _get_inner_html(n).strip()
                if text:
                    oe_list.append(spacer())
                    oe_list.append(f'<one:OE><one:T><![CDATA[<span style="font-size:14.0pt;font-weight:bold;color:#0059B3;">{text}</span>]]></one:T></one:OE>')
                    oe_list.append(spacer())

            elif tag in ("h4", "h5", "h6"):
                text = _get_inner_html(n).strip()
                if text:
                    oe_list.append(spacer())
                    oe_list.append(f'<one:OE><one:T><![CDATA[<span style="font-size:13.0pt;font-weight:bold;color:#0059B3;">{text}</span>]]></one:T></one:OE>')
                    oe_list.append(spacer())

            elif tag == "p":
                text = _get_inner_html(n).strip()
                if text:
                    oe_list.append(f'<one:OE><one:T><![CDATA[<span style="font-size:12.0pt;">{text}</span>]]></one:T></one:OE>')

            elif tag == "br":
                oe_list.append(spacer())

            elif tag == "hr":
                oe_list.append(spacer())
                oe_list.append('<one:OE><one:T><![CDATA[<span style="color:#CCCCCC;font-size:10.0pt;">──────────────────────────────────────────────────</span>]]></one:T></one:OE>')
                oe_list.append(spacer())

            elif tag in ("ul", "ol"):
                process_list(n, depth=list_depth + 1, list_type=tag)

            elif tag == "pre":
                process_code_block(n)

            elif tag == "table":
                process_table(n)

            elif tag in ("div", "section", "article", "header", "footer", "nav", "aside", "blockquote"):
                process_nodes(n.children, list_depth)

    def process_list(list_node: _HtmlNode, depth=1, list_type="ul"):
        bullet_type = "1" if depth == 1 else ("2" if depth == 2 else "3")
        font_size = "12.0" if depth <= 2 else "11.0"

        idx = 0
        for li in list_node.children:
            if not isinstance(li, _HtmlNode) or li.tag != "li":
                continue
            idx += 1

            inline_children = []
            nested_lists = []
            for c in li.children:
                if isinstance(c, _HtmlNode) and c.tag in ("ul", "ol"):
                    nested_lists.append(c)
                else:
                    inline_children.append(c)

            dummy_li = _HtmlNode("li")
            dummy_li.children = inline_children
            text = _get_inner_html(dummy_li).strip()

            if list_type == "ol":
                bullet_xml = ""
                prefix = f"<b>{idx}.</b> "
            else:
                bullet_xml = f'<one:List><one:Bullet bullet="{bullet_type}" fontSize="{font_size}" fontColor="automatic" /></one:List>'
                prefix = ""

            oe_parts = [f'<one:OE>{bullet_xml}<one:T><![CDATA[<span style="font-size:{font_size}pt;">{prefix}{text}</span>]]></one:T>']

            if nested_lists:
                child_oes = []
                for sublist in nested_lists:
                    sub_bullet_type = "2" if depth == 1 else "3"
                    sub_font_size = "12.0" if depth == 1 else "11.0"
                    sub_idx = 0
                    for sub_li in sublist.children:
                        if not isinstance(sub_li, _HtmlNode) or sub_li.tag != "li":
                            continue
                        sub_idx += 1
                        sub_inlines = []
                        deep_lists = []
                        for sc in sub_li.children:
                            if isinstance(sc, _HtmlNode) and sc.tag in ("ul", "ol"):
                                deep_lists.append(sc)
                            else:
                                sub_inlines.append(sc)
                        d_li = _HtmlNode("li")
                        d_li.children = sub_inlines
                        sub_text = _get_inner_html(d_li).strip()

                        if sublist.tag == "ol":
                            s_bullet = ""
                            s_prefix = f"<b>{sub_idx}.</b> "
                        else:
                            s_bullet = f'<one:List><one:Bullet bullet="{sub_bullet_type}" fontSize="{sub_font_size}" fontColor="automatic" /></one:List>'
                            s_prefix = ""

                        s_parts = [f'<one:OE>{s_bullet}<one:T><![CDATA[<span style="font-size:{sub_font_size}pt;">{s_prefix}{sub_text}</span>]]></one:T>']
                        if deep_lists:
                            deep_oes = []
                            for dl in deep_lists:
                                for dl_li in dl.children:
                                    if isinstance(dl_li, _HtmlNode) and dl_li.tag == "li":
                                        dl_text = _get_inner_html(dl_li).strip()
                                        deep_oes.append(f'<one:OE><one:List><one:Bullet bullet="3" fontSize="11.0" fontColor="automatic" /></one:List><one:T><![CDATA[<span style="font-size:11.0pt;color:#555555;">{dl_text}</span>]]></one:T></one:OE>')
                            if deep_oes:
                                s_parts.append(f'<one:OEChildren>{"".join(deep_oes)}</one:OEChildren>')
                        s_parts.append('</one:OE>')
                        child_oes.append("".join(s_parts))

                if child_oes:
                    oe_parts.append(f'<one:OEChildren>{"".join(child_oes)}</one:OEChildren>')

            oe_parts.append('</one:OE>')
            oe_list.append("".join(oe_parts))

    def process_code_block(pre_node: _HtmlNode):
        code_color = "#003366"
        for c in pre_node.children:
            if isinstance(c, _HtmlNode) and c.tag == "code":
                style = c.attrs.get("style", "")
                m = re.search(r"color:\s*([^;]+)", style)
                if m:
                    code_color = m.group(1).strip()

        raw_code = _get_raw_text(pre_node).strip("\r\n")
        lines = raw_code.split("\n")

        line_oes = []
        for line in lines:
            line_str = line.rstrip("\r\n")
            indent_count = len(line_str) - len(line_str.lstrip(" "))
            indent = "&nbsp;" * (indent_count * 2)
            content = line_str.lstrip(" ").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if not content:
                content = "&nbsp;"
            line_oes.append(f'<one:OE><one:T><![CDATA[<span style="font-family:Consolas, monospace;font-size:10.5pt;color:{code_color};">{indent}{content}</span>]]></one:T></one:OE>')

        code_table = (
            f'<one:OE><one:Table bordersVisible="true">'
            f'<one:Columns><one:Column index="0" width="560.0" isLocked="true" /></one:Columns>'
            f'<one:Row><one:Cell shadingColor="#F5F7FA">'
            f'<one:OEChildren>{"".join(line_oes)}</one:OEChildren>'
            f'</one:Cell></one:Row>'
            f'</one:Table></one:OE>'
        )
        oe_list.append(spacer())
        oe_list.append(code_table)
        oe_list.append(spacer())

    def process_table(table_node: _HtmlNode):
        rows = []
        for c in table_node.children:
            if isinstance(c, _HtmlNode):
                if c.tag == "tr":
                    rows.append(c)
                elif c.tag in ("thead", "tbody"):
                    for tr in c.children:
                        if isinstance(tr, _HtmlNode) and tr.tag == "tr":
                            rows.append(tr)

        if not rows:
            return

        col_count = 0
        for r in rows:
            cells = [cell for cell in r.children if isinstance(cell, _HtmlNode) and cell.tag in ("td", "th")]
            col_count = max(col_count, len(cells))

        if col_count == 0:
            return

        col_widths = {
            1: [560.0],
            2: [180.0, 380.0],
            3: [140.0, 160.0, 260.0],
            4: [120.0, 120.0, 220.0, 100.0]
        }.get(col_count, [560.0 / col_count] * col_count)

        cols_xml = "".join([f'<one:Column index="{i}" width="{w}" isLocked="true" />' for i, w in enumerate(col_widths)])

        row_xmls = []
        for r in rows:
            cells = [cell for cell in r.children if isinstance(cell, _HtmlNode) and cell.tag in ("td", "th")]
            cell_xmls = []
            for cell in cells:
                is_th = (cell.tag == "th")
                shading = ' shadingColor="#EBF2FA"' if is_th else ''
                weight = "font-weight:bold;color:#003366;" if is_th else ""
                c_text = _get_inner_html(cell).strip()
                cell_oe = f'<one:OE><one:T><![CDATA[<span style="font-size:12.0pt;{weight}">{c_text}</span>]]></one:T></one:OE>'
                cell_xmls.append(f'<one:Cell{shading}><one:OEChildren>{cell_oe}</one:OEChildren></one:Cell>')
            row_xmls.append(f'<one:Row>{"".join(cell_xmls)}</one:Row>')

        table_xml = (
            f'<one:OE><one:Table bordersVisible="true">'
            f'<one:Columns>{cols_xml}</one:Columns>'
            f'{"".join(row_xmls)}'
            f'</one:Table></one:OE>'
        )
        oe_list.append(spacer())
        oe_list.append(table_xml)
        oe_list.append(spacer())

    process_nodes(root.children)
    return "\n".join(oe_list)



# ---------------------------------------------------------------------------
# OneNote COM API helpers (for writing)
# ---------------------------------------------------------------------------


_SECTION_CACHE: dict[str, str] = {}


def _find_powershell() -> str:
    """Locate the Windows PowerShell 5.1 executable to satisfy STA COM requirements."""
    sys_root = os.environ.get("SystemRoot") or os.environ.get("WINDIR") or r"C:\Windows"
    candidate = os.path.join(sys_root, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
    if os.path.exists(candidate):
        return candidate
    return "powershell.exe"


POWERSHELL_EXE = _find_powershell()


def _cleanup_orphan_onenote() -> None:
    """Terminate orphaned headless ONENOTE.EXE instances (MainWindowHandle == 0) without affecting active user desktop windows."""
    try:
        cleanup_cmd = (
            "Get-Process onenote -ErrorAction SilentlyContinue | "
            "Where-Object { $_.MainWindowHandle -eq 0 } | "
            "Stop-Process -Force"
        )
        subprocess.run(
            [POWERSHELL_EXE, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cleanup_cmd],
            capture_output=True,
            timeout=5,
        )
    except Exception:
        pass


def _run_powershell(script: str, timeout: int = 15) -> tuple[bool, str]:
    """Run a PowerShell script and return (success, output)."""
    try:
        result = subprocess.run(
            [POWERSHELL_EXE, "-STA", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True, text=True, timeout=timeout,
        )
        output = result.stdout.strip()
        if result.returncode != 0:
            return False, result.stderr.strip() or output
        return True, output
    except subprocess.TimeoutExpired:
        _cleanup_orphan_onenote()
        return False, (
            f"Microsoft OneNote COM connection timed out after {timeout}s. "
            "Please ensure Microsoft OneNote desktop app is open on your desktop with no modal dialogs open."
        )
    except FileNotFoundError:
        return False, "Windows PowerShell not found (OneNote live features require Windows PowerShell)"



def _com_get_hierarchy(level: int = 3) -> ET.Element | None:
    """
    Get OneNote hierarchy via COM API.
    Levels: 0=Notebooks, 1=SectionGroups, 2=Sections, 3=Sections(full), 4=Pages
    """
    tmpfile = os.path.join(tempfile.gettempdir(), "onenote_hierarchy.xml")
    tmpfile_ps = tmpfile.replace("\\", "\\\\")
    script = (
        f'$onenote = New-Object -ComObject OneNote.Application; '
        f'$h = ""; '
        f'$onenote.GetHierarchy("", {level}, [ref]$h); '
        f'$h | Out-File -FilePath "{tmpfile_ps}" -Encoding UTF8; '
        f'Write-Output "OK"'
    )
    ok, msg = _run_powershell(script)
    if not ok:
        log.warning("COM GetHierarchy failed: %s", msg)
        return None
    try:
        with open(tmpfile, "r", encoding="utf-8-sig") as f:
            xml_content = f.read()
        return ET.fromstring(xml_content)
    except Exception as e:
        log.warning("Failed to parse hierarchy XML: %s", e)
        return None
    finally:
        try:
            os.remove(tmpfile)
        except OSError:
            pass


def _com_find_section_id(notebook_name: str, section_name: str) -> str | None:
    """Find a section ID by notebook and section name (case-insensitive) with caching."""
    cache_key = f"{notebook_name.strip().lower()}/{section_name.strip().lower()}"
    if cache_key in _SECTION_CACHE:
        return _SECTION_CACHE[cache_key]

    root = _com_get_hierarchy(3)
    if root is None:
        return None

    for nb in root.iter(f"{{{ONE_NS}}}Notebook"):
        if nb.get("name", "").lower() != notebook_name.lower():
            continue
        for sec in nb.iter(f"{{{ONE_NS}}}Section"):
            if sec.get("isInRecycleBin") == "true":
                continue
            if sec.get("name", "").lower() == section_name.lower():
                sec_id = sec.get("ID")
                if sec_id:
                    _SECTION_CACHE[cache_key] = sec_id
                return sec_id
    return None


def _run_powershell_file(script: str, timeout: int = 15) -> tuple[bool, str]:
    """Write a PowerShell script to a temp file and execute it safely with process cleanup and diagnostics."""
    ps_file = os.path.join(tempfile.gettempdir(), f"onenote_mcp_cmd_{os.getpid()}.ps1")
    try:
        with open(ps_file, "w", encoding="utf-8") as f:
            f.write(script)
        log.debug("Running PowerShell script (%d chars): %s", len(script), ps_file)
        proc = subprocess.Popen(
            [POWERSHELL_EXE, "-STA", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps_file],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            output = stdout.strip()
            err = stderr.strip()
            log.debug("PowerShell exit=%d stdout=%s stderr=%s",
                      proc.returncode, output[:500] if output else "(empty)",
                      err[:500] if err else "(empty)")
            if proc.returncode != 0:
                return False, err or output
            return True, output
        except subprocess.TimeoutExpired:
            log.error("PowerShell timed out after %ds - terminating process", timeout)
            proc.kill()
            proc.communicate()
            _cleanup_orphan_onenote()
            return False, (
                f"Microsoft OneNote COM connection timed out after {timeout}s. "
                "Please verify that Microsoft OneNote desktop app is open and running on your desktop, "
                "and that no modal dialogs, password prompts, or sync conflicts are open."
            )
    except FileNotFoundError:
        log.error("PowerShell not found at %s", POWERSHELL_EXE)
        return False, "PowerShell not found (OneNote live features require Windows PowerShell)"
    finally:
        try:
            if os.path.exists(ps_file):
                os.remove(ps_file)
        except OSError:
            pass



def _com_create_page(section_id: str, title: str, body_html: str) -> tuple[bool, str]:
    """Create a new page in a section using the OneNote COM API with rich HTML formatting."""
    log.info("create_page: title=%r, body_len=%d, section=%s", title, len(body_html), section_id)
    log.debug("create_page: raw body=%r", body_html[:500])

    # Convert HTML to structured OneNote OE XML
    oe_xml = _html_to_onenote_xml(body_html)
    log.debug("create_page: oe_xml preview=%r", oe_xml[:800])

    # Write title and OE XML to temp files
    title_file = os.path.join(tempfile.gettempdir(), f"onenote_mcp_title_{os.getpid()}.txt")
    body_file = os.path.join(tempfile.gettempdir(), f"onenote_mcp_body_{os.getpid()}.txt")
    with open(title_file, "w", encoding="utf-8") as f:
        f.write(title)
    with open(body_file, "w", encoding="utf-8") as f:
        f.write(oe_xml)

    section_id_esc = section_id.replace("'", "''")
    title_file_ps = title_file.replace("'", "''")
    body_file_ps = body_file.replace("'", "''")

    script = f"""
$titleContent = (Get-Content -LiteralPath '{title_file_ps}' -Raw -Encoding UTF8).Trim()
$oeXml = (Get-Content -LiteralPath '{body_file_ps}' -Raw -Encoding UTF8).Trim()

$onenote = New-Object -ComObject OneNote.Application
$pageId = ""
$onenote.CreateNewPage('{section_id_esc}', [ref]$pageId, 0)

# Get the new page XML
$pageXml = ""
$onenote.GetPageContent($pageId, [ref]$pageXml, 0)

# ---- Set title ----
# Use regex to replace the CDATA content inside the title T element
$titlePattern = '(<one:T[^>]*>)(<!\\[CDATA\\[)(.*?)(\\]\\]>)(</one:T>)'
$titleReplace = '$1$2' + $titleContent + '$4$5'
$pageXml = [System.Text.RegularExpressions.Regex]::Replace(
    $pageXml,
    $titlePattern,
    $titleReplace,
    [System.Text.RegularExpressions.RegexOptions]::Singleline
)

# ---- Add body outline to SAME pageXml ----
$ns = "http://schemas.microsoft.com/office/onenote/2013/onenote"
$outlineXml = "<one:Outline xmlns:one=`"$ns`"><one:OEChildren>" + $oeXml + "</one:OEChildren></one:Outline>"
$pageXml = $pageXml -replace '</one:Page>', ($outlineXml + '</one:Page>')

try {{
    $onenote.UpdatePageContent($pageXml)
    Write-Output $pageId
}} catch {{
    Write-Error "UpdatePageContent failed: $_"
    exit 1
}} finally {{
    if ($onenote) {{ [System.Runtime.InteropServices.Marshal]::ReleaseComObject($onenote) | Out-Null }}
}}
"""
    try:
        ok, output = _run_powershell_file(script)
        log.info("create_page result: ok=%s output=%r", ok, output[:200] if output else "(empty)")
        if ok and output:
            return True, f"Page '{title}' created successfully (ID: {output})"
        return False, f"Failed to create page: {output}"
    finally:
        for fpath in (title_file, body_file):
            try:
                if os.path.exists(fpath):
                    os.remove(fpath)
            except OSError:
                pass


def _com_append_to_page(page_id: str, body_html: str) -> tuple[bool, str]:
    """Append rich-formatted content to an existing page using the OneNote COM API."""
    log.info("append_to_page: page=%s, body_len=%d", page_id, len(body_html))
    log.debug("append_to_page: raw body=%r", body_html[:500])

    # Convert HTML to structured OE XML
    oe_xml = _html_to_onenote_xml(body_html)
    log.debug("append_to_page: oe_xml preview=%r", oe_xml[:500])

    body_file = os.path.join(tempfile.gettempdir(), f"onenote_mcp_body_append_{os.getpid()}.txt")
    with open(body_file, "w", encoding="utf-8") as f:
        f.write(oe_xml)

    page_id_esc = page_id.replace("'", "''")
    body_file_ps = body_file.replace("'", "''")

    script = f"""
$oeXml = (Get-Content -LiteralPath '{body_file_ps}' -Raw -Encoding UTF8).Trim()

$onenote = New-Object -ComObject OneNote.Application
$pageXml = ""
$onenote.GetPageContent('{page_id_esc}', [ref]$pageXml, 0)

$ns = "http://schemas.microsoft.com/office/onenote/2013/onenote"
$outlineXml = "<one:Outline xmlns:one=`"$ns`"><one:OEChildren>" + $oeXml + "</one:OEChildren></one:Outline>"

$pageXml = $pageXml -replace '</one:Page>', ($outlineXml + '</one:Page>')

try {{
    $onenote.UpdatePageContent($pageXml)
    Write-Output "OK"
}} catch {{
    Write-Error "Append UpdatePageContent failed: $_"
    exit 1
}} finally {{
    if ($onenote) {{ [System.Runtime.InteropServices.Marshal]::ReleaseComObject($onenote) | Out-Null }}
}}
"""
    try:
        ok, output = _run_powershell_file(script)
        log.info("append_to_page result: ok=%s output=%r", ok, output[:200] if output else "(empty)")
        if ok:
            return True, f"Content appended to page {page_id}"
        return False, f"Failed to append to page: {output}"
    finally:
        try:
            if os.path.exists(body_file):
                os.remove(body_file)
        except OSError:
            pass


def _com_update_page_content(page_id: str, body_html: str) -> tuple[bool, str]:
    """Replace body content of an existing OneNote page with rich HTML."""
    log.info("update_page_content: page=%s, body_len=%d", page_id, len(body_html))
    oe_xml = _html_to_onenote_xml(body_html)

    body_file = os.path.join(tempfile.gettempdir(), f"onenote_mcp_body_update_{os.getpid()}.txt")
    with open(body_file, "w", encoding="utf-8") as f:
        f.write(oe_xml)

    page_id_esc = page_id.replace("'", "''")
    body_file_ps = body_file.replace("'", "''")

    script = f"""
$oeXml = (Get-Content -LiteralPath '{body_file_ps}' -Raw -Encoding UTF8).Trim()

$onenote = New-Object -ComObject OneNote.Application
$pageXml = ""
$onenote.GetPageContent('{page_id_esc}', [ref]$pageXml, 0)

# Strip existing Outline elements
$pageXml = [System.Text.RegularExpressions.Regex]::Replace($pageXml, '<one:Outline.*?</one:Outline>', '', [System.Text.RegularExpressions.RegexOptions]::Singleline)

$ns = "http://schemas.microsoft.com/office/onenote/2013/onenote"
$outlineXml = "<one:Outline xmlns:one=`"$ns`"><one:OEChildren>" + $oeXml + "</one:OEChildren></one:Outline>"
$pageXml = $pageXml -replace '</one:Page>', ($outlineXml + '</one:Page>')

try {{
    $onenote.UpdatePageContent($pageXml)
    Write-Output "OK"
}} catch {{
    Write-Error "UpdatePageContent failed: $_"
    exit 1
}} finally {{
    if ($onenote) {{ [System.Runtime.InteropServices.Marshal]::ReleaseComObject($onenote) | Out-Null }}
}}
"""
    try:
        ok, output = _run_powershell_file(script)
        log.info("update_page_content result: ok=%s output=%r", ok, output[:200] if output else "(empty)")
        if ok:
            return True, f"Page {page_id} updated successfully"
        return False, f"Failed to update page: {output}"
    finally:
        try:
            if os.path.exists(body_file):
                os.remove(body_file)
        except OSError:
            pass


def _com_list_pages(section_id: str) -> list[dict]:
    """List pages in a section via COM API. Returns list of {id, name}."""
    root = _com_get_hierarchy(4)
    if root is None:
        return []

    pages = []
    for sec in root.iter(f"{{{ONE_NS}}}Section"):
        if sec.get("ID") == section_id:
            for page in sec.iter(f"{{{ONE_NS}}}Page"):
                if page.get("isInRecycleBin") == "true":
                    continue
                pages.append({
                    "id": page.get("ID", ""),
                    "name": page.get("name", "(untitled)"),
                })
            break
    return pages


# ---------------------------------------------------------------------------
# MCP Write Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_live_notebooks() -> str:
    """List notebooks from the running OneNote app (live, not backup files).

    This uses the OneNote COM API and shows the notebooks currently open in
    the OneNote desktop app, including their sections. Use this to find
    where to create new pages.
    """
    root = _com_get_hierarchy(3)
    if root is None:
        return "Could not connect to OneNote. Make sure the OneNote desktop app is installed."

    lines = []
    for nb in root.findall(f"{{{ONE_NS}}}Notebook"):
        nb_name = nb.get("name", "?")
        lines.append(f"\n## {nb_name}")
        for sec in nb.iter(f"{{{ONE_NS}}}Section"):
            if sec.get("isInRecycleBin") == "true":
                continue
            sec_name = sec.get("name", "?")
            locked = " (locked)" if sec.get("locked") == "true" else ""
            lines.append(f"  - {sec_name}{locked}")

    if not lines:
        return "No notebooks found in OneNote."
    return "\n".join(lines)


@mcp.tool()
async def create_page(notebook_name: str, section_name: str, title: str, content: str) -> str:
    """Create a new page in a OneNote notebook section.

    The content is written as HTML with full rich-text support.
    Supported tags: h1-h6 (headings with auto font sizing), p, ul/ol/li (lists
    with bullets/numbers), b/strong (bold), i/em (italic), u (underline),
    span (with style), a (links), hr (horizontal rule), br, table/tr/td/th.

    Headings get automatic font sizes: h1=24pt, h2=18pt, h3=14pt, h4=13pt,
    h5=12pt, h6=11pt. All body text is 11pt minimum.

    Requires the OneNote desktop app to be installed.

    Args:
        notebook_name: Name of the notebook (from list_live_notebooks).
        section_name: Name of the section within the notebook.
        title: Title for the new page.
        content: The page content as HTML.
    """
    section_id = _com_find_section_id(notebook_name, section_name)
    if section_id is None:
        return (
            f"Could not find section '{section_name}' in notebook '{notebook_name}'. "
            f"Use list_live_notebooks to see available notebooks and sections."
        )

    ok, msg = _com_create_page(section_id, title, content)
    return msg


@mcp.tool()
async def list_live_pages(notebook_name: str, section_name: str) -> str:
    """List pages in a section from the running OneNote app.

    Use this to find page IDs for appending content to existing pages.

    Args:
        notebook_name: Name of the notebook.
        section_name: Name of the section.
    """
    section_id = _com_find_section_id(notebook_name, section_name)
    if section_id is None:
        return (
            f"Could not find section '{section_name}' in notebook '{notebook_name}'. "
            f"Use list_live_notebooks to see available notebooks and sections."
        )

    pages = _com_list_pages(section_id)
    if not pages:
        return "No pages found in this section."

    lines = []
    for p in pages:
        lines.append(f"- {p['name']}  (id: {p['id']})")
    return "\n".join(lines)


@mcp.tool()
async def append_to_page(page_id: str, content: str) -> str:
    """Append content to an existing OneNote page.

    The content is added as a new outline block at the bottom of the page.
    Supports full rich HTML formatting (h1-h6, p, ul/ol/li, b, i, u, span, hr, br).

    Args:
        page_id: The page ID (from list_live_pages).
        content: The content to append as HTML.
    """
    ok, msg = _com_append_to_page(page_id, content)
    return msg


@mcp.tool()
async def update_page_content(page_id: str, content: str) -> str:
    """Replace the body content of an existing OneNote page with new HTML formatting.

    Args:
        page_id: The persistent OneNote page ID (from list_live_pages).
        content: The new page content as HTML.
    """
    ok, msg = _com_update_page_content(page_id, content)
    return msg


def _page_xml_to_markdown(xml_str: str) -> str:
    """Parse OneNote page XML into structured Markdown with headings, sub-bullets, and tables."""
    try:
        root = ET.fromstring(xml_str)
    except Exception as e:
        return f"Failed to parse page XML: {e}"

    title_elem = root.find(f".//{{{ONE_NS}}}Title//{{{ONE_NS}}}T")
    title = ""
    if title_elem is not None and title_elem.text:
        title = re.sub(r"<[^>]+>", "", title_elem.text).strip()

    lines = []
    if title:
        lines.append(f"# {title}\n")

    def walk_oe_children(parent, indent=0):
        prefix = "  " * indent
        for oe in parent.findall(f"./{{{ONE_NS}}}OE"):
            t_elem = oe.find(f"./{{{ONE_NS}}}T")
            list_elem = oe.find(f"./{{{ONE_NS}}}List")
            table_elem = oe.find(f"./{{{ONE_NS}}}Table")

            if t_elem is not None and t_elem.text:
                clean = re.sub(r"<[^>]+>", "", t_elem.text)
                clean = clean.replace("&nbsp;", " ").strip()
                if clean:
                    if list_elem is not None:
                        if list_elem.find(f"./{{{ONE_NS}}}Bullet") is not None:
                            lines.append(f"{prefix}- {clean}")
                        elif list_elem.find(f"./{{{ONE_NS}}}Number") is not None:
                            lines.append(f"{prefix}1. {clean}")
                        else:
                            lines.append(f"{prefix}- {clean}")
                    else:
                        lines.append(f"{prefix}{clean}")

            if table_elem is not None:
                for row in table_elem.findall(f"./{{{ONE_NS}}}Row"):
                    cell_texts = []
                    for cell in row.findall(f"./{{{ONE_NS}}}Cell"):
                        c_text_node = cell.find(f".//{{{ONE_NS}}}T")
                        if c_text_node is not None and c_text_node.text:
                            c_clean = re.sub(r"<[^>]+>", "", c_text_node.text).strip()
                            c_clean = c_clean.replace("&nbsp;", " ")
                            cell_texts.append(c_clean)
                        else:
                            cell_texts.append("")
                    if cell_texts:
                        lines.append(f"| {' | '.join(cell_texts)} |")
                lines.append("")

            child_container = oe.find(f"./{{{ONE_NS}}}OEChildren")
            if child_container is not None:
                walk_oe_children(child_container, indent + 1)

    for outline in root.findall(f".//{{{ONE_NS}}}Outline/{{{ONE_NS}}}OEChildren"):
        walk_oe_children(outline, 0)
        lines.append("")

    return "\n".join(lines).strip()


def _com_get_page_content(page_id: str) -> str | None:
    """Fetch OneNote page XML via COM GetPageContent."""
    tmpfile = os.path.join(tempfile.gettempdir(), f"onenote_read_{os.getpid()}.xml")
    tmpfile_ps = tmpfile.replace("'", "''")
    page_id_esc = page_id.replace("'", "''")
    script = f"""
$onenote = New-Object -ComObject OneNote.Application
$pageXml = ""
try {{
    $onenote.GetPageContent('{page_id_esc}', [ref]$pageXml, 0)
    $pageXml | Out-File -LiteralPath '{tmpfile_ps}' -Encoding UTF8
    Write-Output "OK"
}} catch {{
    Write-Error "GetPageContent failed: $_"
    exit 1
}} finally {{
    if ($onenote) {{ [System.Runtime.InteropServices.Marshal]::ReleaseComObject($onenote) | Out-Null }}
}}
"""
    try:
        ok, msg = _run_powershell_file(script)
        if not ok or not os.path.exists(tmpfile):
            log.warning("COM GetPageContent failed: %s", msg)
            return None
        with open(tmpfile, "r", encoding="utf-8-sig") as f:
            return f.read()
    finally:
        try:
            if os.path.exists(tmpfile):
                os.remove(tmpfile)
        except OSError:
            pass


@mcp.tool()
async def read_live_page(
    page_id: str = "",
    notebook_name: str = "",
    section_name: str = "",
    page_title: str = "",
    raw_xml: bool = False,
) -> str:
    """Read full text, tables, and hierarchical sub-bullets from a live OneNote page as Markdown or raw XML.

    Args:
        page_id: The persistent OneNote page ID (e.g. from list_live_pages).
        notebook_name: Optional notebook name if page_id is not provided.
        section_name: Optional section name if page_id is not provided.
        page_title: Optional substring of the page title to search for if page_id is not provided.
        raw_xml: If True, returns the raw OneNote page XML instead of Markdown.
    """
    target_id = page_id.strip() if page_id else ""

    if not target_id:
        if not notebook_name or not section_name:
            return "Please provide either 'page_id' or both 'notebook_name' and 'section_name'."
        section_id = _com_find_section_id(notebook_name, section_name)
        if not section_id:
            return f"Section '{section_name}' in notebook '{notebook_name}' not found."
        pages = _com_list_pages(section_id)
        if not pages:
            return f"No pages found in section '{section_name}'."
        if page_title:
            matching = [p for p in pages if page_title.lower() in p["name"].lower()]
            if not matching:
                return f"No page matching '{page_title}' found in '{section_name}'. Available: {', '.join(p['name'] for p in pages)}"
            target_id = matching[0]["id"]
        else:
            target_id = pages[0]["id"]

    xml_content = _com_get_page_content(target_id)
    if not xml_content:
        return f"Failed to retrieve page content for ID {target_id}."

    if raw_xml:
        return xml_content

    return _page_xml_to_markdown(xml_content)



# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if not ONENOTE_DIR.exists():
        log.warning(
            "OneNote backup directory not found: %s\n"
            "Read features (list_notebooks, search_notes, read_section) will not work.\n"
            "Write features (create_page, append_to_page) will still work via COM API.\n"
            "Set the ONENOTE_BACKUP_DIR environment variable to the correct path if needed.",
            ONENOTE_DIR,
        )
    else:
        log.info("Reading from: %s", ONENOTE_DIR)

    log.info("Starting OneNote MCP server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
