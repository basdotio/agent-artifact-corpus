# resume-tailoring

A Claude skill that tailors a resume and cover letter to a specific job posting and builds polished,
ATS-friendly **DOCX + PDF** output. It draws only on your real career facts, so nothing it writes is
invented or exaggerated.

## What it does

- Reads a job description and gives an honest fit read (strengths and real gaps) before writing anything.
- Rewrites the title, summary, and competencies to mirror the posting's language.
- Selects the most relevant accomplishments from your profile for each role.
- Builds a two-page resume and a one-page cover letter as DOCX, then converts to PDF.

## Setup

1. Copy `references/profile.template.md` to `references/profile.md` and fill in your real career facts,
   brag bank, and any house-style preferences. This file is the single source of truth.
2. Install the build dependency:
   ```bash
   npm install docx
   ```
3. (For PDF output) install LibreOffice, or export the DOCX to PDF from Word / Pages yourself.

## Usage

Point your Claude session at this skill and give it a job description. It will create a
`<Company_Role>/content.js` from `scripts/content.template.js`, tailor it, then build:

```bash
node scripts/build.js <slug>/content.js <slug>
soffice --headless --convert-to pdf --outdir <slug> <slug>/*.docx
```

Output filenames are derived from the `name` field in your content file, e.g.
`Jane_Doe_<slug>_Resume.docx`.

## Layout

```
resume-tailoring/
  SKILL.md                      # the skill instructions
  README.md
  references/
    profile.template.md         # copy to profile.md and fill in
  scripts/
    build.js                    # DOCX builder (resume + cover from one content.js)
    content.template.js         # copy per job to <slug>/content.js, then tailor
```

## Notes

The builder is intentionally self-contained (one Node dependency). The visual style (accent color, font)
is configurable per job via the content file. See `SKILL.md` for the full method, including the summary
formula and QA checklist.
