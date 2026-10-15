---
name: kb-lint
description: "Audits the knowledge base and, when asked, applies the fixes. Health mode writes a dated lint report (frontmatter, broken links, orphans, stale sources, concept clusters) and edits no page; apply mode fixes what a report found, one category per commit. Use for: lint, audit, health-check, find broken links or orphans (health); apply the lint fixes, fix the broken links, clean up or reorganise from the audit (apply). Not for adding or re-fetching sources (kb-intake, kb-ingest)."
---

# kb-lint

Two modes. **Health** (lint, audit, check, find) writes a report and edits no page. **Apply** (apply, fix, clean up, reorganise) fixes what the latest report found. Vault and staleness come from CLAUDE.md `## Instance`.

## Health

1. Run `bash "${CLAUDE_SKILL_DIR}/scan.sh" <vault> <stale-days>` (0 when the Instance sets no staleness). It prints checks 1–4. Its filters exclude known false positives, so use its output rather than your own scans.
2. Judge what the scan can't:
   - each broken link is **probable-typo** (an existing page name is a near-miss) or **pending** (a deliberate forward reference, valid by design);
   - an unknown type in the histogram (not in the Vocabulary) is a finding;
   - check 5: read the densest pages; a term used across ≥3 pages without its own page is a candidate, listed with the pages that use it.
3. Write `wiki/synthesis/lint-YYYY-MM-DD.md` (`type: synthesis`, `title: Lint report YYYY-MM-DD`). Headers exactly `## 1. Frontmatter validity`, `## 2. Broken wikilinks`, `## 3. Orphan pages`, `## 4. Stale sources`, `## 5. Concept clusters without a home`. Each finding gives a path and a proposed action; a clean section starts with `Clean.`. Stale living-doc sources are proposed for kb-ingest `refresh <slug>`; dated ones are a count.
4. Log `lint | health-check` with per-check counts; commit the report and the log only. Health ends at that commit: offer apply, don't start it.

Health never edits a page, even for an obvious typo: list it. Apply's one-category commits are what make each fix revertable.

## Apply

Needs the latest `wiki/synthesis/lint-*.md` (none → run health first) and a vault tree clean apart from raw/curation/ (otherwise stop: a category commit must hold only its own changes).

Per category, in report order and only those the operator chooses: propose the changes in chat, apply them, log `refactor | <category>` with `- Source: wiki/synthesis/lint-YYYY-MM-DD.md`, commit.
- **Without asking:** missing frontmatter fields; slug ≠ stem → fix the `slug:` field, never rename the file (inbound links use the stem); a link typo with **exactly one** near-miss, every occurrence; a skill, tool or command name in `[[ ]]` → backticks.
- **Confirm first:** a typo with two or more plausible targets; concept-cluster pages (type from the Vocabulary, index line, citing pages relinked); anything else creative.
- An unknown type is proposed to the operator as a schema update, never silently changed.
- Archive, never delete: move to that folder's `_archive/`.
- Stale sources are not an apply category: hand them to kb-ingest as `refresh <slug>`.
