# Fix Pass

This pass re-verifies one audit report and fixes its findings. The session running it must not be the one that wrote the report.

1. **Find the report.** Use the newest `<skill>-<YYYY-MM-DD>.md` in the report folder that has `## Findings` and no `## Disposition` heading. If there is none, say the audit is already closed and stop. If the project is a git repository, note the current commit (`git rev-parse HEAD`) so the user can review or revert the fixes as one diff.
2. **Re-verify each finding.** Line numbers move, so search the whole file for each quote. Then read the quote in context. Give each finding one outcome:
   - fixed as written;
   - fixed with a correction;
   - not a finding;
   - already fixed;
   - pending the user.
3. **Fix what is clear.** Fix it yourself if it is reversible and has one sensible answer: a dead pointer, an orphaned file's rule moved into the load path, or a stale step number.
   - **Contradictions:** resolve toward the newer side by default, using the report's dates. Resolve toward the older side only when you can state why. If either side is undated, or either file has uncommitted changes (`git status --short <file>`), treat it as a preference call instead.
   - **Preference calls:** when the fix has no dated newer side to default to, or otherwise depends on something only the user knows, ask them. Give lettered options, the tradeoffs of each, and your recommendation.
   - **Keep edits minimal.** Prefer deleting or correcting the stale text over adding new text. A contradiction is usually fixed by removing one side, not by adding a third rule that explains the other two.
   - **Skills you don't own:** if the skill came from another author (a `LICENSE` or notices file naming someone else, or a git remote that is not the user's own), record the findings and edit nothing. That author's next update would overwrite local edits, so a report upstream is the durable fix.
4. **Close the report** once no finding is pending the user. Until then the report stays open, and re-running this skill with `<skill> fix` resumes it after the user answers. To close it, append `## Disposition (<YYYY-MM-DD>)` to the report. Give each finding's number and outcome on one line, with the correction or reason where the outcome needs one. List every file you changed.
5. **Report to the user.** Summarize what changed, what was dismissed, and what waits on them.
