---
name: resume-tailoring
description: >-
  Tailor a resume and cover letter to a specific job posting so the output is a polished, truthful,
  ATS-friendly DOCX + PDF that draws only on the candidate's real career facts and chosen house style.
  Use whenever someone pastes or references a job description and wants application materials, or says
  anything like "tailor my resume," "make a resume for this role," "write a cover letter for this," "help
  me apply to X," or "should I go after this one." Also use to refresh, restyle, or fix an existing
  tailored resume. The candidate's canonical career facts live in references/profile.md (fill it in
  first). The skill handles an honest fit read, content selection, a summary formula, the DOCX-to-PDF
  build, and QA.
---

# Resume Tailoring

Produce a tailored resume and (when wanted) cover letter for a specific job: polished, truthful, and
matched to the posting. Output DOCX **and** PDF. The goal is materials a recruiter and an ATS both read
as an obvious fit in the first few seconds, without a word of it being untrue.

## Setup (do this once)

Fill in `references/profile.md` with the candidate's real career facts: contact line, positioning, each
role with its strongest accomplishments (a "brag bank"), skills/toolkit, education, certifications, and
any standing style rules. Everything the skill writes is pulled from this file, so the quality of the
output is capped by how complete and specific it is. Copy `references/profile.template.md` to
`references/profile.md` and fill it in.

The DOCX builder is `scripts/build.js`. The per-job content module is `scripts/content.template.js`.

---

## Process

1. **Read the JD.** Identify the role family (TAM, Solutions/Sales Engineering, Professional Services /
   Delivery, Product, AI / Architect, and so on), the must-have keywords, and any hard requirements.
2. **Give an honest fit read first.** Strengths and real gaps, in a sentence or two. Do not oversell. If
   it is a stretch, say so and why, and whether it is still worth applying (for example a recruiter or
   Easy Apply where the value is getting into a pipeline). Most people would rather hear the truth than
   get a flattering package for a role that will not bite.
3. **Pick a slug** `Company_Role` (for example `Acme_SeniorTAM`) and make a folder for it, e.g.
   `tailored/<slug>/`.
4. **Author the content.** Copy `scripts/content.template.js` to `<slug>/content.js` and tailor every
   field to the JD, pulling only true material from `references/profile.md`. Follow the summary formula
   and tailoring approach below.
5. **Build** the DOCX, then convert to PDF (see Build).
6. **QA** the rendered pages (see checklist). Fix and rebuild if needed.
7. **Show the PDFs**, iterate on feedback, and (optionally) update a job tracker.

The candidate applies; the skill builds. Confirm before anything irreversible.

---

## The summary formula

The professional summary is the highest-leverage lines on the page. A recruiter and the ATS skim the top
third first, so the summary has to make the "yes, fits" call fast, then earn belief. Build it in this
order:

1. **Open with a role-identity label plus a years-of-experience figure that mirrors the JD.** Echo their
   role title/family and lead with the candidate's real tenure. For example, "Hands-on professional
   services and delivery leader with 15+ years..." for a PS role. This is the line that makes the match
   obvious.
2. **Mirror the must-have language.** Work in the JD's top two or three required skills using *their*
   words, so it reads as a match and catches keyword scans.
3. **Anchor with a real proof point.** One or two concrete accomplishments from the candidate's actual
   history that fit the role. This is what keeps it from sounding like generic filler.
4. **Close in the candidate's voice.** A line of authentic positioning.

Do **not** copy the requirement verbatim. A literal paste reads as robotic, and near-duplicating their
text can look worse to an ATS, not better. Echo it in the candidate's voice. And never manufacture an
industry or credential they lack; if the JD wants something they do not have, omit it or address it
honestly in the cover letter.

Lean the summary toward **harder ATS keyword-mirroring for cold portal / Easy-Apply submissions**, and
toward **more human readability when a person will read it after a call or referral**.

---

## Tailoring approach

- Rewrite **title, summary, and core competencies** to mirror the JD's language; reorder and rephrase
  experience bullets to surface the most relevant work first.
- Keep every claim **true.** Pull extra material only from `references/profile.md`. Never invent tools,
  scale, or scope.
- Two pages max for the resume, one page for the cover. Tighten spacing and bullets before cutting real
  content.

---

## House style

These are sensible defaults. Override any of them in `references/profile.md` to match the candidate's
preference.

- **Truthfulness first.** Nothing on the page is untrue or exaggerated. Gaps are addressed honestly, not
  hidden.
- **Education format is consistent:** `University, Field` (not "Studies in X").
- **Separators and dashes:** pick one style and keep it. A common choice is to avoid em dashes entirely
  (they can read as AI-authored) and use commas, colons, hyphen date ranges, and middots (·) as
  separators. The builder follows whatever the content file contains.
- **Bullets:** the builder renders a small accent-colored bullet with a hanging indent, not the default
  fat list bullets. The accent color is configurable (`accent` in the content file).
- **Submit as PDF**, keep a DOCX alongside for editing.
- **Cover-letter voice:** plain and human. Avoid openers like "When I read the [X] posting, it read like
  the work I've done..." (reads like AI). Open with what the candidate does, or with the company's
  problem. Four to five short paragraphs. Address a real gap in one confident sentence if there is one,
  rather than hiding it.

---

## Build

First-time setup in the working folder:
```bash
npm init -y >/dev/null 2>&1 || true
npm install docx
```

Build the DOCX (resume and cover come from one content file):
```bash
node scripts/build.js <slug>/content.js <slug>
```

Convert to PDF with LibreOffice headless. On macOS the binary is usually
`/Applications/LibreOffice.app/Contents/MacOS/soffice`; on Linux it is `soffice` on PATH. If LibreOffice
is not available, deliver the DOCX and let the candidate export to PDF from Word or Pages.
```bash
SOFFICE="soffice"   # adjust per environment
"$SOFFICE" --headless --convert-to pdf --outdir <slug> <slug>/*.docx
```

Output filenames are derived from the `name` field in the content file, for example
`Jane_Doe_<slug>_Resume.docx` and `Jane_Doe_<slug>_CoverLetter.docx`.

---

## QA checklist (every time)

- Resume ≤ 2 pages, cover = 1 page.
- Most recent role is first. Nothing untrue or padded.
- Education reads "University, Field". Dash/separator style is consistent. Bullets are the small accent
  style.
- Title, summary, and competencies clearly echo the JD's language; the summary follows the formula.
- Contact line and dates correct; cover date = today; company and recruiter names spelled correctly.
- If a rendering tool is available, glance at the rendered pages (for example `pdftoppm` to an image) to
  confirm layout before delivering.

---

## Optional: job tracker

If the candidate keeps a job tracker spreadsheet, add a row when a package is built (status "To Review"),
flip it to "Applied" with the date when they apply, and set "Last Updated" to today. A workable column
set: Company, Role/Title, Location, Work Mode, Salary Range, Posting Link, Source, Date Found, Date
Applied, Resume Version, Cover Letter, Key Contact, Connections There, Fit, Status, Next Step, Next Step
Date, Notes, Last Updated. Use a library that preserves existing rows and data validation (for example
`openpyxl` for `.xlsx`).

---

## Files in this skill

- `references/profile.template.md` — copy to `references/profile.md` and fill in. The canonical career
  facts, brag bank, and house-style overrides. Read first.
- `scripts/build.js` — the DOCX builder (resume + cover from one `content.js`). Run it, do not rewrite.
- `scripts/content.template.js` — copy per job to `<slug>/content.js`, then tailor.
