---
name: onenote-mcp
description: Use when reading, creating, updating, searching, or formatting notes, pages, and sections in Microsoft OneNote via the OneNote MCP server or OneNote COM API
---

# OneNote MCP & Rich Text Mastery

## Overview

The **OneNote MCP** skill governs reading, querying, creating, and rich-formatting pages and sections in Microsoft OneNote. It bridges local binary backup file parsing (`pyOneNote`) with real-time Windows COM automation (`OneNote.Application`).

---

## When to Use

### Trigger Conditions & Symptoms
- User requests saving reports, notes, meeting logs, or architectural summaries directly to OneNote.
- User or workspace mandates writing notes to OneNote instead of local Markdown files (e.g. `daily-work/`).
- Task involves searching past notes, retrieving specifications, or reading existing OneNote sections.
- Formatted output in OneNote appears as a collapsed, unstyled single-box text block (lacking line breaks and headings).
- Encountering COM errors like `0x80042009` (*UpdatePageContent failed*) or datatype conversion errors.

### When NOT to Use
- When output must reside strictly in Git version control (e.g. project `docs/` or commit artifacts).
- In non-Windows headless Linux CI environments where the OneNote desktop COM API is unavailable.
- For cloud-only OneDrive notebooks that have never been opened or backed up in the desktop OneNote app.

---

## Quick Reference: OneNote MCP Tools

| Action | Recommended Tool / Script | Target Engine | Key Parameters |
|---|---|---|---|
| **Browse Notebooks** | `list_live_notebooks()` | COM API | None |
| **List Sections** | `list_sections(notebook_name)` | Backup / Local | `notebook_name` |
| **List Live Pages** | `list_live_pages(notebook_name, section_name)` | COM API | `notebook_name`, `section_name` |
| **Create Formatted Page**| `create_page(notebook_name, section_name, title, content)` | COM API | `notebook_name`, `section_name`, `title`, `content` |
| **Append to Page** | `append_to_page(page_id, content)` | COM API | `page_id`, `content` |
| **Read Live Page (MCP)** | `read_live_page(page_id, ...)` | COM API | `page_id` OR `notebook_name`, `section_name`, `page_title` |
| **Search All Notes** | `search_notes(query)` | `pyOneNote` Backup | `query` (string) |
| **Read Section Text** | `read_section(notebook_name, section_name)` | `pyOneNote` Backup | `notebook_name`, `section_name` |
| **Read Live Page Script**| `.\scripts\read_onenote_page.ps1` | COM API (STA) | `-Notebook`, `-Section`, `-PageTitle` |

---

## 1. How to Enable & Invoke in Any Conversation

### Tool Calling Syntax
Call tools via `call_mcp_tool` with `ServerName: "onenote"`:

```json
{
  "ServerName": "onenote",
  "ToolName": "create_page",
  "Arguments": {
    "notebook_name": "Notes-2026",
    "section_name": "Update-Notes-26",
    "title": "Wednesday, 30 September, 2026",
    "content": "<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b><br><b>📅 DAILY WORK REPORT</b><br>..."
  }
}
```

### Adding to Agent Workspaces
To activate OneNote as the primary work report destination for any conversation or project:
Add this directive to `.agent/AGENTS.md` or system prompt:

```markdown
## Work Reports & Notes Output — OneNote MCP
All daily work reports, summaries, and notes must be created as pages in Microsoft OneNote via the OneNote MCP tool:
- Notebook: `Notes-2026`
- Section: `Update-Notes-26`
- Tool: `onenote` MCP → `create_page` / `append_to_page`
```

---

## 2. Rich Text Formatting & Typography Constraints

### The 12px / 12.0pt Typography Rule
> **MANDATORY**: Standard body text, bullet items, and regular content must be styled with a **minimum font size of 12px / 12.0pt**. Headings must scale proportionally (14pt - 24pt).

### The Dual Formatting Architecture

#### Strategy A: OneNote XML Schema (When using the rewritten multi-OE engine)
In OneNote's XML schema (`http://schemas.microsoft.com/office/onenote/2013/onenote`), content inside `<one:Outline><one:OEChildren>` must be broken into separate `<one:OE>` elements for every logical block:
- **Heading 1:** `<one:OE><one:T><![CDATA[<span style="font-size:22.0pt;font-weight:bold;color:#003366;">Title</span>]]></one:T></one:OE>`
- **Heading 2:** `<one:OE><one:T><![CDATA[<span style="font-size:16.0pt;font-weight:bold;color:#1A5276;">Section</span>]]></one:T></one:OE>`
- **Body Text:** `<one:OE><one:T><![CDATA[<span style="font-size:12.0pt;">Paragraph text...</span>]]></one:T></one:OE>`
- **Bullet Items & Nested Sub-bullets:**
  ```xml
  <one:OE>
    <one:List><one:Bullet bullet="1" fontColor="automatic" fontSize="12.0" /></one:List>
    <one:T><![CDATA[<span style="font-size:12.0pt;">Parent bullet</span>]]></one:T>
    <!-- Child OEChildren for true indented sub-bullets -->
    <one:OEChildren>
      <one:OE>
        <one:List><one:Bullet bullet="2" fontColor="automatic" fontSize="12.0" /></one:List>
        <one:T><![CDATA[<span style="font-size:12.0pt;">Nested child sub-bullet</span>]]></one:T>
      </one:OE>
    </one:OEChildren>
  </one:OE>
  ```
- **Native OneNote Tables:** Use `<one:Table bordersVisible="true">` with `<one:Columns>`, `<one:Row>`, and `<one:Cell shadingColor="#EBF2FA">` containing internal `<one:OEChildren>`.
  *(Note: `fontSize` attribute on `<one:Bullet>` is `xs:double` — e.g. `12.0`, NOT `"12.0pt"`).*

#### Strategy B: Unicode Visual Hierarchy (For stock / unmodified MCP servers)
Because unmodified/stock OneNote MCP servers strip block tags and collapse HTML into `<br/>` within a single text node, naive HTML becomes an unreadable single-box dump.

**Always apply the Unicode Visual Framing pattern:**
1. **Top & Section Dividers:** `<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b><br>`
2. **Sub-dividers:** `<b>──────────────────────────────────────────────────</b><br>`
3. **Repository / App Headers:** `<b>🔧 QPRO — BACKEND / API APP</b><br>`
4. **Sub-sections:** `<b>▸ Feature Area Title</b><br>`
5. **Hierarchical Bullet Indentation:**
   - **Level 1 (Major feature):** `  • Primary task description with <b>bold tags</b>.<br>`
   - **Level 2 (Nested sub-bullet):** `      ◦ Implementation details or secondary action.<br>`
   - **Alternative arrow sub-bullet:** `    ↳ <i>Parameter:</i> <code>is_attachment_enabled</code>.<br>`
   - **Level 3 (Deep note):** `          ▫ Backwards-compatible schema detail.<br>`
6. **Rich Aligned Tables:** Monospace boxed tables wrapped in `<span style="font-family:Consolas, monospace;font-size:11.0pt;">`:
   ```
   ┌──────────────────────┬──────────────────────────────────────────┐
   │ Dimension            │ Details / Metrics                        │
   ├──────────────────────┼──────────────────────────────────────────┤
   │ Working Day          │ Wednesday, 30 September, 2026            │
   └──────────────────────┴──────────────────────────────────────────┘
   ```
7. **Impact Points:** `  ✅ Concrete measurable outcome.<br>`
8. **Spacing:** Double `<br><br>` between logical sections.
9. **Multi-Language Code Blocks (PHP, JS, SQL):** Wrap in `<pre><code style="font-family: Consolas, monospace; font-size: 10.5pt; color: #003366; background-color: #F8F9FA;">` to guarantee preserved indentation, line breaks, and monospace font in OneNote.

---

## 3. Reading and Parsing Content from OneNote

### Live COM Page Reading
To read real-time pages without waiting for OneNote backup cycles, use either:

#### A. Direct MCP Tool Call (`read_live_page`)
```json
{
  "ServerName": "onenote",
  "ToolName": "read_live_page",
  "Arguments": {
    "notebook_name": "Notes-2026",
    "section_name": "Update-Notes-26",
    "page_title": "Wednesday, 30 September"
  }
}
```
*(Or pass `"page_id"` directly from `list_live_pages` for 0ms resolution).*

#### B. Bundled PowerShell Script
```powershell
powershell -STA -NoProfile -ExecutionPolicy Bypass -File ".\scripts\read_onenote_page.ps1" -Notebook "Notebook-Name" -Section "Section-Name" -PageTitle "Page Title" -AsMarkdown
```

### Parsing Logic & Cleaning
1. Call `GetPageContent($pageId, [ref]$xml, 0)`.
2. Extract title from `//one:Title//one:T`.
3. Recursively iterate all `//one:Outline//one:OE` nodes.
4. Detect bullets via `one:List/one:Bullet` and numbers via `one:List/one:Number`.
5. Format native `one:Table` rows as Markdown tables (`| ... |`).
6. Traverse nested `one:OEChildren` containers recursively with increased indentation.
7. Strip internal HTML formatting tags inside CDATA using regex `<[^>]+>` and unescape HTML entities.

---

---

## 4. Daily Work Report Formatting Standards

When generating daily work reports or periodic task logs into OneNote, follow this streamlined architecture:

1. **Page Title on Tab Only**:
   - The page title (e.g. `Wednesday, 30 September, 2026`) must be set strictly in the OneNote page title tab via the `title` parameter of `create_page`.
   - **NEVER** write a duplicate `# Title` or `<h1>` heading inside the page body.
2. **Clean Repository Headings**:
   - Use clean `<h2>` titles for each repository:
     - `<h2>🔧 Service Architecture - Backend/API</h2>`
     - `<h2>🎨 Frontend Web Application</h2>`
     - `<h2>⚙️ Core Services & Integrations</h2>`
3. **Repository Subtitles**:
   - Immediately below each `<h2>`, include a subtitle paragraph with repository path and branch in small monospace text:
     `<p><span style="font-family:Consolas, monospace;font-size:9.5pt;color:#666666;">my-project · branch: main</span></p>`
   - Followed by the date subtitle: `<p><b>YYYY-MM-DD (Day)</b></p>`.
4. **Dividers Between All Applications**:
   - **MANDATORY**: Between all application blocks and before the Summary Metrics table, place a clear `<br /><hr /><br />` separator to produce an elegant horizontal divider (`──────────────────────────────────────────────────`) with comfortable whitespace.
5. **Hierarchical Outlines**:
   - Top-level bullet: `<b>Feature Area Title:</b>`
   - Sub-bullets (`<ul><li>...</li></ul>`): Technical details and implementation bullet points.
   - Impact bullet:
     ```html
     <li><b>Impact:</b>
       <ul>
         <li>✅ Impact bullet 1</li>
         <li>✅ Impact bullet 2</li>
       </ul>
     </li>
     ```
6. **Summary Metrics Table**:
   - At the end of each day's entry:
     ```html
     <h2>📊 Summary Metrics</h2>
     <table bordersVisible="true">
       <tr>
         <th style="background-color:#EBF2FA;">Metric / Dimension</th>
         <th style="background-color:#EBF2FA;">Value / Outcome</th>
       </tr>
       <tr><td><b>Working Day</b></td><td>Wednesday, 30 September, 2026</td></tr>
       <tr><td><b>Total Commits (approx)</b></td><td>7</td></tr>
       <tr><td><b>Key Features Delivered</b></td><td>Summary of deliverables...</td></tr>
       <tr><td><b>Repos Active</b></td><td>3</td></tr>
     </table>
     ```
7. **Attribution**:
   - Conclude every report with: `<p><i>Report generated with OneNote MCP</i></p>`.

---

## 5. OneNote Connection & Process Recovery Discipline

- **Research Before Action**: Always research the COM API behavior, plan changes carefully, and test incrementally before executing bulk operations.
- **Selective Process Cleanup**: Never forcefully terminate all OneNote desktop instances (`Stop-Process -Name ONENOTE`). This can corrupt OneNote's local cache or cause the Safe Mode prompt (*Start normally*, *Delete cache*). Only terminate headless background orphan processes where `MainWindowHandle -eq 0`.
- **Developer Partnership for Restarts**: If OneNote COM becomes non-responsive or locked by a modal dialog, do NOT poll or spin in loops. Ask the developer (**Umang Kathiyara**) to close and restart OneNote normally.
- **Fast Page Generation**: Prefer `create_page` over in-place XML replacements (`UpdatePageContent`) on existing complex outlines. Fresh page generation is single-pass and completes reliably in **< 1.0 second**.

---

## Common Mistakes & Troubleshooting

| Error / Symptom | Root Cause | Solution |
|---|---|---|
| **`0xc06d007e` (KERNELBASE.dll crash)** | `<br/>` or unescaped block elements placed inside `<one:T><![CDATA[...]]></one:T>`. | In OneNote XML, each line must be its own `<one:OE>` element within an `<one:OEChildren>` container. Never put `<br/>` in CDATA. |
| **`0x80042009` (UpdatePageContent failed)** | Block HTML tags (`<h1>`, `<p>`, `<table>`) passed directly inside `<one:T>` CDATA. | Strip block tags into inline tags (`<span>`, `<b>`) or convert each block into its own `<one:OE>` element. |
| **`Error parsing '12.0pt' as double`** | Passed unit `'pt'` into `one:Bullet fontSize` attribute. | Use pure numeric double: `<one:Bullet fontSize="12.0" />`. |
| **Missing App Dividers** | Application sections blend together without visual hierarchy. | Insert `<br /><hr /><br />` between all application sections and before summary tables. |
| **Duplicate Page Title in Body** | Adding `<h1>` or `# Title` inside content. | Omit the title from HTML body. Set title only on the page title tab. |
| **Collapsed wall of text** | Naive HTML sent to stock MCP server without visual separators. | Use Strategy B: heavy Unicode dividers (`━━━`), `▸`, `•`, and `<br><br>` spacing. |
| **`0x80080005` (CO_E_SERVER_EXEC_FAILURE / 120s Hang)** | OneNote crashed previously or was force-killed, showing Safe Mode prompt (*Start normally*, *Delete cache*, *Delete settings*), OR orphan zombie instances (`MainWindowHandle: 0`) exist. | Choose **"Start normally"** on the OneNote desktop prompt. Terminate only headless zombies (`Where-Object { $_.MainWindowHandle -eq 0 } | Stop-Process -Force`), never kill active UI instances. |
| **`Unexpected HRESULT` from COM** | PowerShell process was executed in MTA mode. | Ensure PowerShell is always executed with the `-STA` flag. |
| **Section not found** | Live OneNote notebook has not synced or name differs in case/whitespace. | Run `list_live_notebooks()` to retrieve the exact live section name. |

---

## Detailed References

For comprehensive technical specifications and code implementations, consult:
- [MCP Server Reference & Setup Guide](references/mcp-server-reference.md)
- [OneNote XML Schema & Formatting Mastery](references/onenote-xml-and-formatting.md)
- [Page Parsing and Reading Guide](references/page-parsing-and-reading.md)
- [Live Page Reader Script](scripts/read_onenote_page.ps1)
