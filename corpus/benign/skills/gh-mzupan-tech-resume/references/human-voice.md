# Human-voice pass (humanizer + unslop, adapted for resumes)

Run this on every resume and cover letter draft before building files. Goal: the hiring manager should not think "AI wrote this." The evidence says the real penalty is for writing that is generic and unverifiable, more than for AI use as such: polished claims with no named systems or numbers, stock verbs, uniform bullets. So this pass is mostly about specificity, with pattern removal second.

## Steps

1. **Lint.** `python3 "$SKILL_DIR/scripts/lint.py" <file> [--type cover]`. Resolve `SKILL_DIR` as described in the main skill. It flags HARD (stock AI resume vocabulary, chatbot phrasing, dashes), SHAPE (uniform bullet lengths, repeated openers, -ing riders, triads, too few or too many numbers), and SOFT (context-dependent words). It also merges hits from unslop's scanner when installed.
2. **Humanizer pass.** If installed, locate `humanizer` through the agent's skill catalog or beside this skill, read its `SKILL.md`, and apply it in embedded mode (return only final text) to the summary, each bullet, and the whole letter. Its §1-§8 (staging, contrasts, closers, triads, dashes) and §12-§18 (AI vocabulary, inflation, -ing riders, sales language) apply directly.
3. **Unslop check.** If installed, locate `unslop` the same way, read its `references/core-contract.md`, and follow its rewrite contract: edit only confirmed defects, preserve every fact, number, name, and date, and add no claims. For cover letters with voice samples available, its `references/commands/mimic.md` flow can be used to match the user's voice.
4. **Re-lint** until 0 HARD. Every remaining SHAPE/SOFT item gets a decision: fix it, or keep it because it is accurate in context (e.g. "robust" describing a statistical method, "orchestration" meaning Kubernetes).
5. **Fact diff.** Compare the final text to the profile and `gaps.md`: no number, tool, title, team size, or outcome appears that the user didn't give you. Remove anything that crept in.
6. **Read-aloud test.** Read the summary and the letter as if you were the user saying it to a peer. If they wouldn't say it out loud, rewrite it.

If either skill is not installed, apply this file's rules and lint.py alone, and tell the user once.

The linter looks for unslop beside this skill first, then in standard project skill folders above the source file, then in personal skill folders (`~/.agents/skills`, `~/.codex/skills` or `$CODEX_HOME/skills`, `~/.bob/skills`, `~/.claude/skills`, `~/.copilot/skills`, `~/.gemini/skills`, and `~/.config/opencode/skills`). It runs only the first scanner found, so shared installations do not duplicate hits.

## Resume-genre exceptions

The humanizer and unslop were written for prose. Resumes have their own conventions, so do not "fix" these:

- **Bullets drop the subject.** "Built X" with no "I" is the standard resume form; humanizer §11 (missing subjects) does not apply to bullets or the summary.
- **Skills rows are lists.** Comma lists of technologies are not triads.
- **Technical words in their technical sense stay**: robust (statistics), orchestration (containers), pipeline, scalable when followed by a number, critical (severity levels), key (cryptographic).
- **Numbers are wanted** in bullets, but not every bullet.
- **Bold** is only for the name, section headings, job titles, and skill-row labels (the builder handles this). Nothing in bullet text is bolded.

## What a human resume looks like

- Bullet lengths vary. Some are one line, a few are two.
- Verbs are plain and repeat occasionally, the way people write. "Built" twice in a resume is fine; three bullets in a row starting "Led" is not.
- Specific nouns: system names, the actual tools, the actual number of teams, the customer type.
- An occasional detail only the person would know ("the billing service nobody wanted to touch", "after the 2023 us-east-1 outage").
- Results stated as results, not dressed up: "on-call pages dropped from ~40 a week to ~10", not "dramatically enhancing operational resilience".

## What a human cover letter looks like

- First sentence is about their problem or a concrete connection, not about the writer's feelings.
- Sentences vary in length; some start with something other than "I".
- One real story with a specific detail, not three abstract claims.
- Contractions are fine. Plain words. No em dashes. No "Furthermore". No closing line that restates the letter.
- Ends with a plain next step.

## Word swaps that come up constantly

| Instead of | Write |
|---|---|
| spearheaded | led, started, set up, built |
| leveraged | used, built on (or drop the clause) |
| orchestrated (non-technical) | ran, coordinated, organized |
| streamlined | say what got faster or shorter, and by how much |
| utilized | used |
| enhanced, optimized | improved X from A to B |
| collaborated with stakeholders | worked with product and finance on |
| drove impact / drove results | the result itself |
| responsible for | what you did |
| passionate about | a fact that shows it |
| fast-paced environment | the actual pace (weekly releases, 4-person team) |
| proven track record | cut |
| cutting-edge | the technology's name |
