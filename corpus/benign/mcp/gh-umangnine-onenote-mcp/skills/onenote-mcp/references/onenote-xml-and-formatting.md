# OneNote XML Schema & Rich Text Formatting Mastery Guide

## 1. The Core Problem: Why Naive HTML Looks Awful in OneNote

When agents pass raw HTML (like `<h1>`, `<h2>`, `<p>`, `<ul>`, `<li>`) into the OneNote MCP tool, two common failures occur:

### Failure Mode 1: The "Collapsed Text Blob"
The standard/naive MCP server sanitizer strips block elements or replaces them with flat `<br/>` tags inside a single text node:
```xml
<!-- Naive/Collapsed result in OneNote -->
<one:Outline>
  <one:OEChildren>
    <one:OE>
      <one:T><![CDATA[Heading 1<br/>Heading 2<br/>Normal paragraph text...]]></one:T>
    </one:OE>
  </one:OEChildren>
</one:Outline>
```
**Visual Result in OneNote:** One single, unstyled paragraph box where all lines run together, headings are indistinguishable from body text, bullets are missing, and no visual separation exists.

### Failure Mode 2: COM Exception `0x80042009` (UpdatePageContent Failed)
Passing unescaped raw block-level elements (`<h1>`, `<div>`, `<table>`) directly into OneNote's `<one:T>` node causes the COM XML parser to reject the entire document with HRESULT `0x80042009`.

---

## 2. OneNote Document Object Model (DOM) Architecture

To render rich, beautiful documents in Microsoft OneNote, you must understand the **OneNote 2013 XML Schema** (`http://schemas.microsoft.com/office/onenote/2013/onenote`).

### Structural Hierarchy
```
one:Page
  ├── one:Title
  │     └── one:OE
  │           └── one:T (Contains CDATA with page title string)
  └── one:Outline (Container for content blocks)
        └── one:OEChildren (Container for Outline Elements)
              ├── one:OE (Heading 1)
              │     └── one:T (Styled CDATA)
              ├── one:OE (Paragraph)
              │     └── one:T (Styled CDATA)
              ├── one:OE (List Item with Bullet)
              │     ├── one:List
              │     │     └── one:Bullet
              │     └── one:T (Styled CDATA)
              └── one:OE (Spacer / Vertical Margin)
                    └── one:T (Empty CDATA)
```

### The Fundamental Rule: One `OE` per Logical Block
In Microsoft OneNote:
- **Every Heading is an independent `<one:OE>`**.
- **Every Paragraph is an independent `<one:OE>`**.
- **Every Bullet / Numbered list item is an independent `<one:OE>` containing a `<one:List>` child**.
- **Empty `<one:OE>` nodes serve as vertical margin/spacers**.

---

## 3. Mandatory Font Sizing & Typography Standards

> **PROJECT MANDATE: Minimum Font Size is 12px / 12.0pt**
> All body text and lists must be rendered at a minimum of `12.0pt` (equivalent to standard 16px/12pt Word/OneNote print sizing). Never use tiny 9pt or 10pt text for main documentation.

### Recommended Hierarchy:
| Semantic Level | XML / CSS Font Size | Weight / Color | Target Use |
|---|---|---|---|
| **Document Title** | Handled by OneNote Title | Standard Bold | Set via `<one:Title>` |
| **Heading 1 (`h1`)** | `22.0pt` / `24.0pt` | Bold (`#003366` or default) | Major repo/document title |
| **Heading 2 (`h2`)** | `16.0pt` / `18.0pt` | Bold (`#1A5276`) | Major sections / App headers |
| **Heading 3 (`h3`)** | `13.0pt` / `14.0pt` | Bold (`#2C3E50`) | Feature areas / Subsections |
| **Body Paragraph** | **`12.0pt` (Minimum)** | Regular (`#333333`) | Narrative explanations |
| **Bullet / List Item**| **`12.0pt` (Minimum)** | Regular | Task bullet points |
| **Code / Monospace** | **`11.0pt` - `12.0pt`** | `font-family: Consolas, Courier New` | Hash, variable, command |
| **Captions / Footers**| `11.0pt` | Italic (`#777777`) | Timestamps and attribution |

---

## 4. OneNote XML Element Reference

### A. Paragraph & Heading Elements
Inside `<one:T>`, inline HTML tags with CSS styles are wrapped in `<![CDATA[...]]>`.

```xml
<!-- Heading 2 Example -->
<one:OE>
  <one:T><![CDATA[<span style="font-size:16.0pt;font-weight:bold;color:#003366;">🔧 QPRO - Backend/API App</span>]]></one:T>
</one:OE>

<!-- Standard Body Paragraph (Minimum 12.0pt) -->
<one:OE>
  <one:T><![CDATA[<span style="font-size:12.0pt;color:#222222;">Implemented priority-based maintenance mode with automated webhook protection.</span>]]></one:T>
</one:OE>
```

### B. Bullet Lists
Bullet lists require `<one:List><one:Bullet ... /></one:List>` before `<one:T>`.

> [!CAUTION]
> **XML Schema Data Type Trap:** The `fontSize` attribute on `<one:Bullet>` and `<one:Number>` is defined as `xs:double`.
> - ❌ WRONG: `fontSize="12.0pt"` (Throws COM error: *"Error parsing '12.0pt' as double datatype"*)
> - ✅ CORRECT: `fontSize="12.0"` (Pure decimal number)

```xml
<one:OE>
  <one:List>
    <one:Bullet fontColor="automatic" fontSize="12.0" />
  </one:List>
  <one:T><![CDATA[<span style="font-size:12.0pt;">Added <b>is_attachment_enabled</b> toggle in business settings.</span>]]></one:T>
</one:OE>
```

### C. Numbered Lists
```xml
<one:OE>
  <one:List>
    <one:Number fontColor="automatic" fontSize="12.0" />
  </one:List>
  <one:T><![CDATA[<span style="font-size:12.0pt;">Run database migration script.</span>]]></one:T>
</one:OE>
```

### E. Indentation & Nested Sub-bullets (Hierarchical Outlines)

In Microsoft OneNote, true outline indentation is achieved by nesting `<one:OEChildren>` inside a parent `<one:OE>`. OneNote automatically applies native indentation and gives the parent a collapsible outline handle:

```xml
<!-- Parent Bullet (Level 1) -->
<one:OE>
  <one:List>
    <one:Bullet fontColor="automatic" fontSize="12.0" />
  </one:List>
  <one:T><![CDATA[<span style="font-size:12.0pt;font-weight:bold;">Core Architecture Upgrades</span>]]></one:T>
  
  <!-- Nested Children (Level 2 Sub-bullets) -->
  <one:OEChildren>
    <one:OE>
      <one:List>
        <one:Bullet fontColor="automatic" fontSize="12.0" />
      </one:List>
      <one:T><![CDATA[<span style="font-size:12.0pt;">Decoupled document log models from shared base class.</span>]]></one:T>
    </one:OE>
    <one:OE>
      <one:List>
        <one:Bullet fontColor="automatic" fontSize="12.0" />
      </one:List>
      <one:T><![CDATA[<span style="font-size:12.0pt;">Standardized <b>createdAt</b> timestamp handling across all environments.</span>]]></one:T>
      
      <!-- Nested Children (Level 3 Deep Sub-bullets) -->
      <one:OEChildren>
        <one:OE>
          <one:List>
            <one:Bullet fontColor="automatic" fontSize="11.0" />
          </one:List>
          <one:T><![CDATA[<span style="font-size:11.0pt;color:#555555;">Zero database migrations required; fully backwards compatible.</span>]]></one:T>
        </one:OE>
      </one:OEChildren>
    </one:OE>
  </one:OEChildren>
</one:OE>
```

---

### F. Native OneNote Tables

OneNote supports native XML grid tables via `<one:Table>`. Use `bordersVisible="true"` and `shadingColor` for crisp, professional headers:

```xml
<one:Table bordersVisible="true">
  <one:Columns>
    <one:Column index="0" width="160.0" isLocked="true" />
    <one:Column index="1" width="340.0" isLocked="true" />
  </one:Columns>
  
  <!-- Table Header Row -->
  <one:Row>
    <one:Cell shadingColor="#EBF2FA">
      <one:OEChildren>
        <one:OE>
          <one:T><![CDATA[<span style="font-size:12.0pt;font-weight:bold;color:#003366;">Metric / Header</span>]]></one:T>
        </one:OE>
      </one:OEChildren>
    </one:Cell>
    <one:Cell shadingColor="#EBF2FA">
      <one:OEChildren>
        <one:OE>
          <one:T><![CDATA[<span style="font-size:12.0pt;font-weight:bold;color:#003366;">Value / Description</span>]]></one:T>
        </one:OE>
      </one:OEChildren>
    </one:Cell>
  </one:Row>
  
  <!-- Table Data Row -->
  <one:Row>
    <one:Cell>
      <one:OEChildren>
        <one:OE>
          <one:T><![CDATA[<span style="font-size:12.0pt;font-weight:bold;">Working Day</span>]]></one:T>
        </one:OE>
      </one:OEChildren>
    </one:Cell>
    <one:Cell>
      <one:OEChildren>
        <one:OE>
          <one:T><![CDATA[<span style="font-size:12.0pt;">Wednesday, 30 September, 2026</span>]]></one:T>
        </one:OE>
      </one:OEChildren>
    </one:Cell>
  </one:Row>
  <one:Row>
    <one:Cell>
      <one:OEChildren>
        <one:OE>
          <one:T><![CDATA[<span style="font-size:12.0pt;font-weight:bold;">Total Commits</span>]]></one:T>
        </one:OE>
      </one:OEChildren>
    </one:Cell>
    <one:Cell>
      <one:OEChildren>
        <one:OE>
          <one:T><![CDATA[<span style="font-size:12.0pt;">7 commits across 3 active repositories</span>]]></one:T>
        </one:OE>
      </one:OEChildren>
    </one:Cell>
  </one:Row>
</one:Table>
### G. Multi-Language Code Block Formatting (PHP, JS, SQL, Shell)

To render code blocks in OneNote with clear syntax distinction and preserved indentation:
Wrap code in `<pre><code>` with `Consolas` monospace font, subtle background shading (`#F8F9FA` or `#F5F7FA`), and color accents:

```html
<!-- PHP Code Snippet -->
<p><b>PHP Backend Controller:</b></p>
<pre><code style="font-family: Consolas, monospace; font-size: 10.5pt; color: #003366;">
&lt;?php
namespace common\controllers;

use Yii;
use yii\web\Response;

class BaseApiController extends Controller
{
    public function beforeAction($action): bool
    {
        if (Yii::$app->params['maintenance_mode'] ?? false) {
            return $this-&gt;_sendMaintenanceResponse(5031);
        }
        return parent::beforeAction($action);
    }
}
</code></pre>

<!-- JavaScript / TypeScript Snippet -->
<p><b>Frontend Hook (useAttachmentSync.ts):</b></p>
<pre><code style="font-family: Consolas, monospace; font-size: 10.5pt; color: #8A4B00;">
import { useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';

export const useAttachmentSync = () => {
  const { user, isAttachmentEnabled } = useAuth();
  useEffect(() => {
    if (user && isAttachmentEnabled) {
      syncAttachmentsToIndexedDb(user.businessId);
    }
  }, [user, isAttachmentEnabled]);
};
</code></pre>

<!-- SQL Migration Query -->
<p><b>SQL Database Migration:</b></p>
<pre><code style="font-family: Consolas, monospace; font-size: 10.5pt; color: #006644;">
-- Add composite index for high-speed tenant attachment queries
ALTER TABLE `business_attachments` 
  ADD COLUMN `group` VARCHAR(64) NOT NULL DEFAULT 'default' AFTER `category`,
  ADD COLUMN `key` VARCHAR(128) NULL AFTER `group`,
  ADD INDEX `idx_tenant_group_key` (`business_id`, `group`, `key`);
</code></pre>
```

---

## 5. Visual Formatting Fallback (For Stock / Unmodified MCP Servers)

When working in an environment where the underlying OneNote MCP server code has not been patched to generate multi-OE XML, use **Unicode Visual Formatting**:

Because the stock sanitizer reduces blocks to `<br/>` within a single text block, you must use structural Unicode characters, indentation, and bold headers to guarantee clean readability:

```html
<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b><br>
<b>📅 DAILY WORK REPORT — Wednesday, 30 September, 2026</b><br>
<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b><br><br>

<b>🔧 SERVICE ARCHITECTURE — BACKEND / API</b><br>
<i>my-project · branch: main</i><br><br>

<b>▸ Document Logs Timestamp Canonicalization</b><br>
  • Standardized <b>createdAt</b> timestamp handling across all log models.<br>
  • Decoupled log models from base to allow independent schema updates.<br><br>

<b>▸ Settings Default Value Corrections</b><br>
  • Set <b>should_display_product_price_enabled</b> default to <b>0</b>.<br><br>

<b>💡 Impact</b><br>
  ✅ Consistent timezone-agnostic timestamps across all environments.<br>
  ✅ Product price display defaults correctly to disabled.<br><br>

<b>──────────────────────────────────────────────────</b><br><br>

<b>📊 SUMMARY METRICS</b><br>
<span style="font-family:Consolas, monospace;font-size:11.0pt;">
┌─────────────────────────┬──────────────────────────────────────────┐<br>
│ <b>Metric / Dimension</b>     │ <b>Value / Outcome</b>                        │<br>
├─────────────────────────┼──────────────────────────────────────────┤<br>
│ Working Day             │ Wednesday, 30 September, 2026            │<br>
│ Total Commits           │ 7 commits across 3 active repositories   │<br>
│ Repositories Active     │ Backend, Super Admin, Custom Web         │<br>
│ Production Status       │ Zero regression; all migrations verified │<br>
└─────────────────────────┴──────────────────────────────────────────┘<br>
</span><br>
<i>Report generated with OneNote MCP</i>
```

### Key Techniques for Fallback Formatting:
1. **Header Dividers**: Use double-width box drawing `━━━━━━━━━━━━━━━━━━━━━━━━━━` for major sections.
2. **Sub-dividers**: Use light horizontal box drawing `──────────────────────────` between repositories.
3. **Primary Section Bullets**: Use `▸` followed by bold titles (`<b>▸ Feature Name</b>`).
4. **Hierarchical Sub-Bullets**:
   - **Level 1 (Major feature)**: `  • Bold feature statement`<br>
   - **Level 2 (Nested sub-bullet)**: `      ◦ Indented implementation detail`<br>
   - **Level 3 (Deep technical note)**: `          ▫ Backwards-compatible schema detail`
5. **Alternative Sub-Bullet Indentation**: Use `    ↳ ` for nested child tasks:
   ```html
     • <b>Attachment API Endpoint:</b> Centralized storage upload handler.<br>
       ↳ <i>Gated by:</i> <code>is_attachment_enabled</code> business configuration.<br>
       ↳ <i>Validation:</i> Enforces 0755 directory and 0644 file permissions.
   ```
6. **Rich Visual Tables**: Wrap box-drawing characters (`┌─┬─┐`, `│ │ │`, `├─┼─┤`, `└─┴─┘`) inside `<span style="font-family:Consolas, monospace;font-size:11.0pt;">` so OneNote preserves monospace alignment without column drift.
7. **Impact Markers**: Use `  ✅ ` with explicit benefits.
8. **Spacing**: Use double `<br><br>` before new sections to force visual separation.

---

## 6. COM Automation Pitfalls & Architectural Troubleshooting

### 1. `0xc06d007e` (KERNELBASE.dll C++ Exception Crash)
- **Symptom:** PowerShell command crashes or terminates abruptly with NTSTATUS `0xc06d007e`.
- **Root Cause:** Attempting to pass `<br/>` or block-level elements (`<div>`, `<p>`) inside `<one:T><![CDATA[...]]></one:T>`. In OneNote 2013 schema, CDATA inside `<one:T>` strictly permits inline formatting tags (`<b>`, `<i>`, `<u>`, `<span>`, `<a>`, `<font>`).
- **Solution:** Never place `<br/>` inside CDATA. Every newline must be an independent `<one:OE>` element inside an `<one:OEChildren>` container.

### 2. `Required attribute 'bullet' is missing`
- **Symptom:** `UpdatePageContent` fails with `Required attribute 'bullet' is missing`.
- **Root Cause:** In `<one:List><one:Bullet ... /></one:List>`, the schema mandates the `bullet` attribute specifying the bullet style index (e.g., `bullet="1"` for standard bullet, `bullet="2"` for open circle, `bullet="3"` for square).
- **Solution:** Always emit `<one:Bullet bullet="1" fontSize="12.0" fontColor="automatic" />`.

### 3. `Error parsing '12.0pt' as double datatype`
- **Symptom:** `UpdatePageContent` fails with XML schema datatype validation error.
- **Root Cause:** The `fontSize` attribute on `<one:Bullet>` and `<one:Number>` is typed as `xs:double`, not a CSS length string.
- **Solution:** Use numeric double: `fontSize="12.0"`, never `"12.0pt"`.

### 4. `0x80080005` (CO_E_SERVER_EXEC_FAILURE) or PowerShell Hanging
- **Symptom:** `New-Object -ComObject OneNote.Application` hangs for 30s-120s or throws `0x80080005`.
- **Root Causes:**
  1. **Safe Mode / Startup Recovery Dialog Active:** After an unexpected crash (e.g. from invalid XML `0xc06d007e`) or aggressive force-killing (`Stop-Process -Force`) while notebook write locks are held, OneNote pauses on startup displaying a Safe Mode dialog:
     - *"Start normally"*
     - *"Delete notebook cache"*
     - *"Delete settings"*
     While this modal dialog is displayed, OneNote's COM interface is completely blocked. Windows COM waits 120s before returning `0x80080005 (CO_E_SERVER_EXEC_FAILURE)`.
  2. **Modal Dialog Open in UI:** OneNote desktop application has an open modal dialog (notebook sync error, password prompt, options window) blocking COM message dispatch.
  3. **Zombie Headless Instances:** Multiple orphaned background `ONENOTE.EXE` instances exist without a visible window.
- **Solution & Recovery Protocol:**
  - If the Safe Mode prompt appears, select **"Start normally"** to preserve existing notebooks and resume the interactive session.
  - Terminate only headless zombie instances (`MainWindowHandle -eq 0`) while keeping the active UI window intact:
    ```powershell
    Get-Process onenote -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -eq 0 } | Stop-Process -Force
    ```
  - **Never** blindly kill active UI instances with `Stop-Process -Force` during normal operation, as this triggers the Safe Mode crash-detection prompt on the next startup.

### 5. Research-First & Disciplined Execution Protocol
- **MANDATORY**: When troubleshooting OneNote COM or format errors:
  1. **Research Online First**: Verify error codes (`0x80080005`, `0x80042009`, `0xc06d007e`) against official Microsoft docs and developer community resources.
  2. **Inspect Process State**: Check process tree, elevation level, window handles (`MainWindowHandle`), and thread wait states before making changes.
  3. **Plan Before Modifying**: Draft the exact change, verify dependencies, and avoid trial-and-error cycles.

### 6. `pywintypes` Missing under Python Virtual Environments
- **Symptom:** FastMCP crashes on startup with `ModuleNotFoundError: No module named 'pywintypes'`.
- **Root Cause:** In Windows, `pywintypes.dll` resides in `site-packages/pywin32_system32`, which is added by `pywin32.pth`. When Python runs without `.pth` auto-processing (such as running via direct executable path without environment activation), `pywintypes` cannot be loaded.
- **Solution:** In `server.py`, use `site.addsitedir(str(_venv_site))` and explicitly add `pywin32_system32` to `sys.path` and `os.add_dll_directory()`.

