---
name: aso-review
description: Review App Store metadata (fastlane) across 14+ languages for ASO, naturalness, and messaging. Use when reviewing localized metadata before release. Triggers on "ASO review", "ASOレビュー", "ストアレビュー", "metadata review", "メタデータレビュー", "store review".
model: sonnet
context: fork
allowed-tools: Read Glob Grep Edit Write Task TeamCreate TeamDelete SendMessage TaskCreate TaskUpdate TaskList Bash(pnpm:*) Bash(fastlane:*)
argument-hint: "[path/to/fastlane/metadata]"
---

# ASO Review

Review App Store metadata across all locales from three perspectives: ASO optimization, naturalness, and messaging consistency.

Core principle: **Localize, don't translate.** Metadata must read as if a native speaker wrote it from scratch.

## How to Invoke

```
/aso-review
/aso-review path/to/fastlane/metadata
```

The skill auto-discovers metadata files. No arguments needed if fastlane metadata is in the standard location.

## Phase Tracking

**At workflow start, create tasks for each phase:**

```
TaskCreate: "Phase 0: Route — verify target is ASO metadata"
TaskCreate: "Phase 1: Discover target files"
TaskCreate: "Phase 2: Build shared context"
TaskCreate: "Phase 3: Form review team & run reviews"
TaskCreate: "Phase 4: Cross-review discussion"
TaskCreate: "Phase 5: Synthesize results"
TaskCreate: "Phase 6: Apply fixes (after user approval)"
```

Update status as you progress: `in_progress` when starting, `completed` when done.

## Workflow

### Phase 0: Route

Verify the review target is ASO metadata.

**Valid targets:**
- `**/metadata/**` — fastlane metadata (subtitle, keywords, description per locale)

**Redirect:** If `.tsx` LP files or `docusaurus.config.*` detected, tell user: "LP pages should use `/lp-review` instead."

**No metadata found:** If no fastlane metadata directory exists, ask the user for the path before proceeding.

### Phase 1: Discover Target Files

```
Glob("**/metadata/**")     → fastlane metadata
```

- Read ALL discovered files
- Build locale inventory (expect 14+ languages)
- Log discovered locales: `ja, en, ko, zh-Hans, de, es, fr, ...`

**If fewer than expected locales found:** Inform the user how many locales were detected and confirm whether to proceed or wait for missing locales.

### Phase 2: Build Shared Context

Gather before dispatching to reviewers:

1. Full metadata text per locale (subtitle, keywords, description)
2. Locale inventory with file paths
3. Brand voice reference (see `references/_localization-principles.md`)
4. App category and target audience

### Phase 3: Form Review Team & Run Reviews

**MUST call TeamCreate to create the review team:**

```
TeamCreate("aso-review-team")
```

**Then spawn ALL 3 agents in ONE message using Task tool. Do NOT launch sequentially.**

| Agent Name | subagent_type | Role |
|------------|---------------|------|
| aso-reviewer | labee-marketing-aso | **LEAD** — ASO optimization |
| naturalness-reviewer | general-purpose | Naturalness checking |
| messaging-reviewer | labee-pmm-fujimoto-ren | Value proposition & tone |

**Each agent receives:**
- Complete metadata text for all locales
- The checklist from `references/_checklist-aso.md`
- The localization principles from `references/_localization-principles.md`
- Instruction to produce per-locale findings grouped by locale

**CRITICAL:** Each agent MUST review EVERY detected locale independently. Not just JP and EN.

**Per-agent instructions:**

**aso-reviewer (LEAD):**
- Per-locale keyword research (keywords are NOT translated — research local search terms independently)
- Subtitle optimization within character limits (CJK ~15, Latin ~30)
- Competitive differentiation per market (competitors differ by region)
- Search volume analysis for primary keywords
- Makes final call on conflicts between ASO and naturalness

**naturalness-reviewer:**
- Detect "translated feel" per locale (source-language structure leaking through)
- Check formality alignment (consumer app = casual register in most locales)
- Flag literally translated idioms and keyword stuffing disguised as natural text
- Suggest specific rewrites for every flagged item

**messaging-reviewer:**
- Cross-locale value proposition consistency (core benefit must align)
- Tone alignment with brand voice across all locales
- Feature naming consistency (translated vs kept original)
- Flag contradicting claims between locales

### Phase 4: Cross-Review Discussion

**MUST use SendMessage between agents. Do NOT skip this phase.**

1. **SendMessage** aso-reviewer's keyword suggestions to naturalness-reviewer — "Are these keyword changes still natural?"
2. **SendMessage** naturalness-reviewer's findings to aso-reviewer — "Can we preserve keywords while fixing naturalness?"
3. **SendMessage** messaging consistency issues to all agents — "Locale X contradicts locale Y on value prop"

Each agent responds with agreements, disagreements, and proposed resolutions.

**The aso-reviewer (LEAD) makes final call on conflicts** — especially ASO keyword vs naturalness trade-offs.

### Phase 5: Synthesize Results

1. Collect final feedback from all agents after cross-review
2. Produce a consolidated report per locale

**Report format:**

```markdown
# ASO Review Report

## Summary
[Overall assessment across all locales]

## Per-Locale Findings

### ja (Japanese)
- [Finding with specific before/after suggestion]

### ko (Korean)
- [Finding with specific before/after suggestion]

[Repeat for every detected locale]

## Cross-Locale Issues
- [Issues spanning multiple locales]

## Conflicts Resolved
- [Conflict]: [Resolution by lead reviewer]
```

3. **MUST call TeamDelete("aso-review-team")** after synthesizing results.
4. Present report to user and **wait for approval** before applying fixes.

### Phase 6: Apply Fixes

**Only after user approval.**

1. Apply approved changes to metadata files
2. Run `pnpm run build` if applicable
3. Present diff summary

## Examples

### ASO Subtitle

**Bad (keyword stuffing):**
> タスク管理・時間管理・プロジェクト管理・チーム管理アプリ

**Good (natural with keyword):**
> チームのタスクと時間をまとめて管理

**Why:** The bad version crams every keyword into the subtitle, sacrificing readability. The good version includes the primary keyword naturally while communicating a clear benefit.

### Korean: Translated vs Localized

**Bad (translated from JP, sounds like a manual):**
> 작업을 관리할 수 있습니다

**Good (localized, casual and scannable):**
> 할 일, 한눈에 정리

**Why:** The bad version uses formal -습니다 endings and technical 작업 (work/task), reading like a translated manual. The good version uses casual 할 일 (to-do) with a noun-ending phrase natural to Korean App Store copy.

### German: Translated vs Localized

**Bad (subject omission from JP source):**
> Verwaltet Aufgaben und Zeit

**Good (addresses user directly):**
> Deine Aufgaben und Zeit im Griff

**Why:** The bad version omits the subject (natural in Japanese, awkward in German) and uses a bare verb. The good version addresses the user directly with "Deine" (du-form), standard for German consumer apps.

### Chinese: Translated vs Localized

**Bad (reads like a spec sheet):**
> 任务管理和时间跟踪

**Good (conversational, benefit-oriented):**
> 轻松搞定每日待办

**Why:** The bad version lists features in formal written register. The good version uses colloquial phrasing native to the Chinese App Store, leading with the benefit.

### English: AI Vocabulary in Metadata

**Bad:**
> Delve into comprehensive task management

**Good:**
> See your tasks. Check them off.

**Why:** The bad version uses AI vocabulary ("delve", "comprehensive") that signals machine-generated text. The good version is concrete, action-oriented, and sounds human-written.

## Anti-Patterns

1. **Do NOT launch agents sequentially** — all 3 in ONE Task call
2. **Do NOT skip cross-review discussion** — Phase 4 is mandatory
3. **Do NOT translate keywords** — research local search terms independently per locale
4. **Do NOT review only JP and EN** — MUST review ALL detected locales
5. **Do NOT merge results without discussion** — agents must cross-check findings
6. **Do NOT review LP pages** — redirect user to `/lp-review`
7. **Do NOT forget TeamDelete** — always clean up the review team after Phase 5

## Reference Files

| File | Load When |
|------|-----------|
| `references/_checklist-aso.md` | Auto-loaded: ASO review checklist |
| `references/_localization-principles.md` | Auto-loaded: Localization guidance and per-language red flags |
