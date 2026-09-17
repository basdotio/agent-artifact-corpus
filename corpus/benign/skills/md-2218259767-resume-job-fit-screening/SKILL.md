---
name: resume-job-fit-screening
description: Screen and rank the best-fit jobs from a careers search-results URL using either a local account or a plain-text resume. Reuse local, synced, or bundled site notes, keep private user data local, and optionally queue public-safe site methods for community sharing.
---

# Resume Job Fit Screening

## Overview

Turn a recruitment search-results URL plus either a local account or a plain-text resume into a strict, evidence-backed shortlist of roles worth applying to.

This v2 workflow separates:

- installed skill resources
- local private runtime state
- optional community-synced site notes
- workspace report outputs

Use the bundled scripts when they fit. Prefer deterministic scripts over re-explaining the same runtime logic every run.

## Required Inputs

- Require these inputs before starting:
  - Recruitment search-results URL
  - One of:
    - account id already stored in local runtime
    - plain-text resume
- Accept these optional inputs:
  - Explicit skip or preference rules
  - `topk` to return; default to `5`
  - Whether to expand search keywords; default to `true`
  - Whether community site note sync is enabled for this run
  - Whether newly discovered public-safe notes should be queued for sharing
- If both account and resume are available, the explicit resume overrides the account for the current run only unless the user asks to persist it.
- If no account exists and no resume is provided, ask only for the missing resume and offer to create an account after the run.

## Workflow

### 1. Initialize Runtime State

- Run:
  ```bash
  python <skill_dir>/scripts/init_runtime.py
  ```
- Runtime state lives outside the installed skill by default:
  - `~/.codex/data/resume-job-fit-screening/`
- Use the runtime for:
  - local accounts
  - synced community notes
  - local repaired or newly discovered notes
  - publish queue artifacts

### 2. Resolve the Candidate Profile

- If the user specifies an account, use it.
- If the user has a default account and does not override it, use that.
- If no account is available, require a plain-text resume.
- Use:
  ```bash
  python <skill_dir>/scripts/account_store.py list
  python <skill_dir>/scripts/account_store.py show <account_id>
  ```
- Read `references/account_template.md` only if you need the canonical account layout.

### 3. Establish Site Context

- Run:
  ```bash
  python <skill_dir>/scripts/job_site_context.py "<search_url>"
  ```
- Use the returned fields to identify:
  - `site_slug`
  - selected note source and path
  - runtime roots
  - suggested report path
- Treat `site_slug` as the canonical name for:
  - local note: `<runtime_root>/site_notes/local/<site_slug>.md`
  - synced note: `<runtime_root>/site_notes/synced/<site_slug>.md`
  - bundled note: `references/bundled_site_notes/<site_slug>.md`
  - report: `<site_slug>_resume_match_<YYYYMMDD>.md`

### 4. Sync Community Site Notes Only When Configured

- If runtime config enables registry sync and the run should use it, run:
  ```bash
  python <skill_dir>/scripts/sync_site_notes.py --site-slug "<site_slug>"
  ```
- Sync is optional and must never block the core workflow if the registry is unavailable.
- Do not auto-overwrite local notes.
- At runtime, prefer note sources in this order:
  1. local
  2. synced
  3. bundled

### 5. Handle the Data-Access Layer

- If a selected note exists:
  - read it first
  - follow the recorded method before inventing a new one
  - if the method breaks, repair it into the local note path, not into the bundled copy
- If no note exists:
  - discover a stable way to retrieve job listings and details
  - prefer this order:
    1. official JSON APIs behind the page
    2. network request reconstruction
    3. frontend bundle or sourcemap tracing
    4. browser automation
    5. HTML scraping as last resort
  - save the final working method to the local note path
  - use `references/site_note_template.md` as the note contract
- Never store:
  - tokens, cookies, personal headers, or secrets
  - dead ends or failed explorations
  - ambiguous guesses presented as confirmed method

### 6. Validate and Queue New Public-Safe Notes

- For a repaired or new local note, run:
  ```bash
  python <skill_dir>/scripts/validate_site_note.py "<note_path>"
  ```
- Only if the note is explicitly public-safe and the user agrees, queue it for sharing:
  ```bash
  python <skill_dir>/scripts/publish_site_note.py --note-path "<note_path>"
  ```
- Queueing is preferred over direct publication when credentials or network access are uncertain.

### 7. Normalize Job Data

- Map every retained posting to this minimum schema:
  ```json
  {
    "job_id": "string",
    "title": "string",
    "detail_url": "string",
    "department": ["string"],
    "locations": ["string"],
    "job_duty": "string",
    "job_requirement": "string",
    "source_site": "string",
    "captured_at": "YYYY-MM-DD",
    "raw": {}
  }
  ```
- Prefer full JD details over list-page summaries.
- Keep enough raw fields to support later auditing.

### 8. Structure the Candidate Profile

- Extract only resume-grounded signals:
  - core strengths
  - explicit weaknesses
  - hard constraints such as degree, graduation time, or required stack gaps
- Keep the profile strict. Do not upgrade the candidate based on plausible but unstated experience.
- If account preferences exist, treat them as defaults that can be tightened by current-run instructions.
- Read `references/jd_matching_methodology.md` if you need the full screening rubric.

### 9. Expand Search Keywords Only When Enabled

- If keyword expansion is `true`, derive adjacent search terms from the resume's real evidence.
- Expand only into closely related wording.
- Deduplicate aggressively.
- Do not expand into directions the user explicitly wants to skip.
- Record which keywords produced useful jobs if multiple searches are combined.

### 10. Run Rule-Based Prescreening

- Apply user preferences and obvious hard filters first.
- Classify each job into one of:
  - `跳过`
  - `不建议`
  - `备选`
  - `推荐`
- Save a one-sentence reason for every job, even if it is rejected.
- Prioritize eliminating clear mismatches over optimistic ranking.

### 11. Run Strict Secondary Review

- Read `references/strict_reviewer_prompt.md` before the detailed evaluation pass.
- Re-evaluate only the jobs that survive prescreening.
- If subagents are available and explicitly authorized, use independent subagents with the same strict prompt for JD-by-JD review.
- Otherwise simulate independence:
  - review each JD in isolation
  - avoid looking at prior scores while writing the current review
  - rank only after all detailed reviews are complete
- Base every judgment on resume facts and JD text, not on optimistic interpolation.

### 12. Deliver the Report

- Read `references/output_format.md` before writing the final document.
- Default output path:
  - `<workspace_root>/<site_slug>_resume_match_<YYYYMMDD>.md`
- Include:
  - search scope and capture date
  - account or preference summary
  - Top-k table
  - detailed analysis for each shortlisted job
  - full screening table or grouped lists
- If the search had gaps, state them explicitly.

### 13. Persist Local Knowledge and Feedback

- Keep repaired or discovered notes in the local runtime note directory.
- Keep bundled notes read-only.
- If the user gives feedback that should affect future runs, append it to the account as pending preference updates rather than silently rewriting confirmed preferences.
- Use:
  ```bash
  python <skill_dir>/scripts/account_store.py append-entry <account_id> --section pending --line "<summary>"
  ```

## Resources

- Read `references/jd_matching_methodology.md` for the reusable screening workflow and ranking rules.
- Read `references/strict_reviewer_prompt.md` before the secondary review stage.
- Read `references/output_format.md` before writing the Markdown deliverable.
- Read `references/site_note_template.md` before creating or repairing a site note.
- Read `references/account_template.md` before creating or repairing an account.
- Read `references/bundled_site_notes/` for bundled site-specific retrieval methods.
- Run `scripts/job_site_context.py` to standardize site naming, note lookup, and report naming.

## Operating Rules

- Prefer exact dates in reports and notes.
- Prefer direct evidence over summary claims.
- Prefer stable data-access methods over brittle page parsing.
- Keep private user data local by default.
- Do not auto-publish site notes without explicit user approval.
- Keep all Markdown artifacts copy-pasteable.
