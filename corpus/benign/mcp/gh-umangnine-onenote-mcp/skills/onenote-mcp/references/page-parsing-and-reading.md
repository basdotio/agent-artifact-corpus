# Reading and Parsing OneNote Pages & Content

## 1. Dual Inspection Strategy

There are two distinct methods for reading and extracting content from Microsoft OneNote:

1. **Direct COM API Live Extraction (Recommended for recent/current notes)**:
   - Queries the active OneNote desktop application directly.
   - 100% real-time (0 second latency). Reflects pages created seconds ago.
   - Extracts full XML DOM including titles, timestamps, author metadata, tags, and formatting.

2. **Binary Backup File Parser (`.one` via `pyOneNote`)**:
   - Parses local `.one` backup files from `%LOCALAPPDATA%\Microsoft\OneNote\16.0\Backup\`.
   - Completely headless (does not require OneNote to be running).
   - Only reflects notes that have been backed up (subject to OneNote's backup schedule).

---

## 2. Reading Live OneNote Pages via COM API

### A. Discovering Page IDs
Before reading a page, you need its unique OneNote ID (`{GUID}{1}{GUID}`). Use `list_live_pages` or PowerShell:

```powershell
# PowerShell STA snippet to list all pages in a notebook/section
$onenote = New-Object -ComObject OneNote.Application
$h = ""
# Level 4 = Full hierarchy down to individual pages
$onenote.GetHierarchy("", 4, [ref]$h)
$xml = [xml]$h

# Filter for section and list pages
$pages = $xml.SelectNodes("//*[local-name()='Section'][@name='Update-Notes-26']/*[local-name()='Page']")
foreach ($p in $pages) {
    [PSCustomObject]@{
        Name = $p.name
        ID   = $p.ID
        Date = $p.dateTime
    } | Format-Table -AutoSize
}
```

### B. Extracting Clean Content from a Page ID (`GetPageContent`)
To read a specific page by ID:

```powershell
$pageId = "{607EC381-2238-4686-89F1-F86135DFD43A}{1}{E1953829625770263200451999671275850004164341}"
$onenote = New-Object -ComObject OneNote.Application
$content = ""
# 0 = Default info (piBasic: text, formatting, outlines)
$onenote.GetPageContent($pageId, [ref]$content, 0)

# Save or parse XML
$pageXml = [xml]$content
$nsMgr = New-Object System.Xml.XmlNamespaceManager($pageXml.NameTable)
$nsMgr.AddNamespace("one", "http://schemas.microsoft.com/office/onenote/2013/onenote")

# Extract Page Title
$title = $pageXml.SelectSingleNode("//one:Title/one:OE/one:T", $nsMgr).InnerText

# Extract all text blocks preserving list structure
$elements = $pageXml.SelectNodes("//one:Outline//one:OE", $nsMgr)
foreach ($oe in $elements) {
    $isBullet = $oe.SelectSingleNode("one:List/one:Bullet", $nsMgr) -ne $null
    $isNumber = $oe.SelectSingleNode("one:List/one:Number", $nsMgr) -ne $null
    $tNode = $oe.SelectSingleNode("one:T", $nsMgr)
    
    if ($tNode) {
        # Strip internal HTML tags inside CDATA for clean plain text
        $cleanText = [System.Text.RegularExpressions.Regex]::Replace($tNode.InnerText, "<[^>]+>", "")
        $cleanText = [System.Net.WebUtility]::HtmlDecode($cleanText).Trim()
        
        if ($cleanText) {
            if ($isBullet) {
                Write-Host "  • $cleanText"
            } elseif ($isNumber) {
                Write-Host "  1. $cleanText"
            } else {
                Write-Host $cleanText
            }
        }
    }
}
```

---

## 3. Parsing Local `.one` Backup Files with Python (`pyOneNote`)

When OneNote desktop is closed or reading offline backups:

```python
from pathlib import Path
from pyOneNote.OneDocument import OneDocment

def parse_onenote_file(one_filepath: Path) -> dict:
    """
    Parses a local .one file and extracts page titles and rich text blocks.
    """
    result = {
        "file": str(one_filepath),
        "titles": [],
        "text_blocks": []
    }
    
    with open(one_filepath, "rb") as f:
        doc = OneDocment(f)
        
    for prop in doc.get_properties():
        prop_type = prop.get("type", "")
        val = prop.get("val", {})
        
        if not isinstance(val, dict):
            continue
            
        # Detect page titles
        if prop_type == "jcidTitleNode":
            title = val.get("RichEditTextUnicode", "").strip()
            if title:
                result["titles"].append(title)
                
        # Detect text content
        text = val.get("RichEditTextUnicode", "").strip()
        if text and prop_type != "jcidTitleNode":
            result["text_blocks"].append(text)
            
    return result

# Example usage:
backup_file = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "OneNote" / "16.0" / "Backup" / "Notes" / "Section.one"
if backup_file.exists():
    data = parse_onenote_file(backup_file)
    print("Found titles:", data["titles"])
    print(f"Extracted {len(data['text_blocks'])} text blocks.")
```

---

## 4. Converting OneNote Page Content to Clean Markdown

When an agent needs to read a OneNote page and represent it as Markdown in a conversation:

```python
import re
import xml.etree.ElementTree as ET

def onenote_xml_to_markdown(page_xml_str: str) -> str:
    """
    Converts OneNote COM GetPageContent XML into clean GitHub-flavored Markdown.
    """
    ONE_NS = {"one": "http://schemas.microsoft.com/office/onenote/2013/onenote"}
    root = ET.fromstring(page_xml_str)
    
    md_lines = []
    
    # 1. Extract Page Title
    title_node = root.find(".//one:Title//one:T", ONE_NS)
    if title_node is not None and title_node.text:
        md_lines.append(f"# {title_node.text.strip()}\n")
        
    # 2. Iterate Outline Elements (OEs)
    for oe in root.findall(".//one:Outline//one:OE", ONE_NS):
        t_node = oe.find("one:T", ONE_NS)
        if t_node is None or not t_node.text:
            continue
            
        raw_text = t_node.text.strip()
        
        # Check if list item
        is_bullet = oe.find("one:List/one:Bullet", ONE_NS) is not None
        is_number = oe.find("one:List/one:Number", ONE_NS) is not None
        
        # Convert simple HTML formatting to Markdown
        clean = re.sub(r"<b>(.*?)</b>", r"**\1**", raw_text)
        clean = re.sub(r"<i>(.*?)</i>", r"*\1*", clean)
        clean = re.sub(r"<code>(.*?)</code>", r"`\1`", clean)
        clean = re.sub(r"<[^>]+>", "", clean).strip() # Strip remaining HTML
        
        if not clean:
            continue
            
        if is_bullet:
            md_lines.append(f"- {clean}")
        elif is_number:
            md_lines.append(f"1. {clean}")
        elif "font-size:18" in raw_text or "font-size:24" in raw_text:
            md_lines.append(f"\n## {clean}\n")
        elif "font-size:14" in raw_text or "font-size:16" in raw_text:
            md_lines.append(f"\n### {clean}\n")
        else:
            md_lines.append(f"\n{clean}")
            
    return "\n".join(md_lines)
```
