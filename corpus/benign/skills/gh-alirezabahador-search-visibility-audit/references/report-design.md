# Report Design & Generation

Full detail behind Step 4 of SKILL.md — the downloadable `.docx`/`.pdf`
deliverable. Read this once you're ready to actually build the report, not
before.

---

## Setup

`docx` should already be available. Check before installing, in one
combined command so it's a single tool call:

```bash
node -e "require('docx')" 2>/dev/null || npm install docx
```

Write the full generation script to a file and run it in one shot — don't
pause partway through.

Output everything to `/mnt/user-data/outputs/` (this is the directory the
user can actually access; nothing written elsewhere is visible to them).

---

## Design system

**Palette**
| Role | Hex |
|---|---|
| Header / cover background | `1B2A4A` |
| Accent | `2563EB` |
| Score — strong (8–10) | `16A34A` |
| Score — needs work (5–7) | `D97706` |
| Score — critical (1–4) | `DC2626` |
| Alternating row background | `F8F9FA` |
| Border gray | `E2E8F0` |
| Body text | `1E293B` |
| Section tint | `EFF6FF` |
| Strength-table tint | `F0FDF4` |

**Type**: a single clean sans-serif throughout (Arial or, if available,
a more distinctive system sans like Calibri — pick one and use it
consistently). Title 34pt bold · H1 22pt bold · H2 16pt bold · H3 13pt bold
· body 11pt · footer/caption 9pt.

**Page**: US Letter, `12240 x 15840` DXA, 1-inch margins, content width
`9360` DXA.

Keep the visual system consistent but don't over-decorate — every color and
table should be doing work (signaling status), not just filling space.

---

## Page order

1. **Cover** — own section, no header/footer, full navy background.
   - Vertically centered block: site domain (36pt bold white, the hero
     element) · "Search Visibility Audit — SEO / GEO / AEO" subtitle (light
     blue `93C5FD`, 18pt) · audit type badge ("QUICK AUDIT" / "FULL AUDIT")
     · a 3-column score strip (one cell per dimension: label, big score
     number, status word, background colored by score tier).
   - Small footer block: audit date, one line identifying this as an
     automated audit generated with Claude (keep this factual, not a brand
     name belonging to someone else).
   - Page break after.

2. **Executive summary** — a tinted box (`EFF6FF`) with 3–5 sentences
   specific to this site: what's strong, the single most urgent issue, and
   one clear opportunity. Below it, the scores table (SEO / GEO / AEO /
   Combined out of 30), score cells color-coded by tier.

3. **Head-to-head comparison** *(only if a competitor URL was audited)* —
   a table with one row per key signal and two columns (this site vs.
   competitor), plus a one-paragraph summary of where the gap matters most.
   Put this early — it's often the most-read page when a competitor was
   involved.

4. **Pages audited** — every URL fetched, with page type and a one-line
   note ("Homepage", "Missing H1", "Strong FAQ schema"). Alternate row
   shading.

5. **SEO analysis** — subsections: On-page Technical, Content Quality,
   Structured Data, Site-level Technical. Each finding as a 3-column row
   (Signal | Finding | Status), Status cell color-coded (green "Good" /
   amber "Needs Attention" / red "Missing").

6. **GEO analysis** — subsections: E-E-A-T, Content for AI Synthesis,
   AI-Crawler Access (this subsection should stand out — if any AI crawler
   is blocked, lead with it in bold, not buried in the table).

7. **AEO analysis** — subsections: Snippet Eligibility, Structured Answer
   Formats, Voice/Conversational Readiness.

8. **Priority roadmap** — 5-column table: Priority | Issue | Dimension |
   Effort | Impact. Order rows by priority, not by dimension.
   - 🔴 Critical — `DC2626`, white text
   - 🟠 High — `EA580C`, white text
   - 🟡 Medium — `D97706`, white text
   - 🟢 Quick win — `16A34A`, white text (low effort, real impact — these
     earn their own tier because they're the easiest thing for a client to
     act on first)

9. **What's already working** — tinted table (`F0FDF4`), genuine strengths
   with the specific evidence that supports each one.

10. **What this audit can't tell you** — the table from
    `signals-reference.md`'s final section, so the client knows exactly
    what to check next and where.

11. **Glossary** *(Full Audit only)* — one or two plain-English sentences
    each for SEO, GEO, and AEO.

**Header** (all pages but cover): domain left-aligned, "Search Visibility
Audit" right-aligned, navy bottom border.
**Footer** (all pages but cover): audit date left-aligned, page number
right-aligned, gray top border.

---

## Generating the DOCX

```javascript
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
        ShadingType, VerticalAlign, PageNumber, PageBreak } = require('docx');
const fs = require('fs');

// ... build the document following the page order and design system above ...

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(
    '/mnt/user-data/outputs/search-audit-{domain}-{date}.docx',
    buffer
  );
  console.log('DOCX written');
});
```

Follow the `docx` (npm) gotchas from the docx skill if it's available in
this environment (dual table/cell widths, `ShadingType.CLEAR` not `SOLID`,
`PageBreak` must sit inside a `Paragraph`, no literal `\n`, etc.) — read
that skill's own guidance rather than duplicating it here, since it may be
updated independently of this skill.

## Validate, then convert to PDF

If a docx validation script is available in this environment, run it and
fix any reported errors before moving on:

```bash
python <path-to-docx-skill>/scripts/office/validate.py \
  /mnt/user-data/outputs/search-audit-{domain}-{date}.docx
```

Convert to PDF:

```bash
python <path-to-docx-skill>/scripts/office/soffice.py --headless \
  --convert-to pdf /mnt/user-data/outputs/search-audit-{domain}-{date}.docx \
  --outdir /mnt/user-data/outputs/
```

If no such scripts are available in this environment, fall back to any
docx→PDF conversion tool you do have access to; don't skip the PDF unless
truly no conversion path exists, in which case say so and deliver the DOCX
alone.

## Deliver

Call `present_files` with both the `.docx` and `.pdf` paths so the user can
open, download, or share them directly — don't just describe where they are.
