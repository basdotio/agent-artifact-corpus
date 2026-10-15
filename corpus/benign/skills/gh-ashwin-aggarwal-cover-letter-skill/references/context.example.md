# Candidate context

<!--
HOW TO USE THIS FILE

1. Copy it:  cp references/context.example.md references/context.md
2. Fill in references/context.md. That copy is gitignored, so your data stays local.
3. This file is the ONLY source of facts the skill may use about you. Anything not
   written here will never appear in a letter.

Markers:
- [FILL]     means "not filled in yet".
- [CONFIRM]  means "written down but not verified".
The skill ignores every line that still contains [FILL] or [CONFIRM], so a partially
filled file is safe to use. Replace the marker with real content when you are sure.

Hints in parentheses after a marker are for you. Delete them when you fill the line.
-->

## Background

- Degree: [FILL] (e.g. B.S. in Computer Science, minor in Statistics)
- School: [FILL] (full name of your university or program)
- Year: [FILL] (e.g. rising senior, graduating May 2027)
- Affiliations: [FILL] (labs, project teams, clubs, fellowships you can name in a letter)
- Core stack: [FILL] (languages, frameworks, and tools you have actually shipped with)

## Archetypes

The role types you apply for. The skill infers one per job description, or you can name it in your prompt.

1. Applied AI
2. SWE/FDE
3. Data Eng
4. Data Science

You can rename, add, or remove archetypes. Keep three places in sync: this list, the columns of the routing matrix, and the Archetype voice section.

## Routing matrix

Put `x` in a cell when that experience is good evidence for that archetype. Unchecked entries are never used for that archetype, even if their keywords match the job description. Row names must match the `###` headings under Experience exactly.

| Experience | Applied AI | SWE/FDE | Data Eng | Data Science |
|---|---|---|---|---|
| Experience 1 | | | | |
| Experience 2 | | | | |
| Experience 3 | | | | |
| Experience 4 | | | | |
| Experience 5 | | | | |
| Experience 6 | | | | |

## Archetype voice

How each archetype's evidence paragraphs lead. These are working defaults. Edit them if you like.

- Applied AI: lead with the model or system, how it was evaluated, what improved.
- SWE/FDE: lead with what shipped, who used it, what you owned end to end.
- Data Eng: lead with the pipeline, data sources and volume, reliability, and what it fed.
- Data Science: lead with the question, the analysis, and the finding.

## Experience

Copy the entry block below once per experience. The heading must match the routing matrix row exactly.

### Experience 1

- What: [FILL] (one line: what this project or role was)
- Stack: [FILL] (named technologies only, e.g. Python, PyTorch, FAISS, PostgreSQL)
- Built:
  - [FILL] (concrete thing you built or did)
  - [FILL] (another concrete thing)
  - [FILL] (optional third)
- Outcome: [FILL] (a real metric, or literally "no metric". Never estimate.)
- Status: [FILL] (complete, in progress, planned, or not deployed, plus anything that must never be claimed, e.g. "never say it was used in production")
- Framing:
  - Applied AI: [FILL] (one line per checked archetype: how to angle this entry for that role type. Delete lines for unchecked archetypes.)
  - SWE/FDE: [FILL]
  - Data Eng: [FILL]
  - Data Science: [FILL]

### Experience 2

- What: [FILL]
- Stack: [FILL]
- Built:
  - [FILL]
  - [FILL]
  - [FILL]
- Outcome: [FILL]
- Status: [FILL]
- Framing:
  - Applied AI: [FILL]
  - SWE/FDE: [FILL]
  - Data Eng: [FILL]
  - Data Science: [FILL]

### Experience 3

- What: [FILL]
- Stack: [FILL]
- Built:
  - [FILL]
  - [FILL]
  - [FILL]
- Outcome: [FILL]
- Status: [FILL]
- Framing:
  - Applied AI: [FILL]
  - SWE/FDE: [FILL]
  - Data Eng: [FILL]
  - Data Science: [FILL]

## Situational mentions

Optional one-sentence add-ons. These are not evidence entries: they are never scored and never get their own paragraph. The skill uses at most one per letter, and only when the posting explicitly emphasizes the trigger. Copy an item block per mention.

### <Name>

- Trigger: [FILL: what the posting must emphasize, e.g. learning quickly, implementing research papers]
- Fact: [FILL: one concrete sentence with a number or named artifact]
- Status: [FILL: limits on what may be claimed]

### <Name>

- Trigger: [FILL: what the posting must emphasize, e.g. learning quickly, implementing research papers]
- Fact: [FILL: one concrete sentence with a number or named artifact]
- Status: [FILL: limits on what may be claimed]

## Not in the matrix

Optional. Experiences the skill should ignore entirely (too old, not relevant, or superseded).

- [FILL]

## Never mention

Optional. Anything that must never appear in a letter: internal system names, confidential projects, unfinished work you don't want surfaced.

- [FILL]
