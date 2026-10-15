---
name: help-me-review
description: Turn a pull request into a review checklist Artifact where each reviewer marks every item Looks good, Change needed, Question or Skip, then read the verdicts back and write a review summary. Use when the user says "review checklist for PR 123", "split this review between us", "what should reviewers check", or "summarise the review".
---

# Help me review: PR to review checklist to summary

Two phases. Phase 1 reads one pull request and publishes a review guide as an Artifact. Each reviewer ticks their areas and marks every item. Phase 2 reads every reviewer's verdicts and writes a review summary with the changes and questions first.

The page is a fixed template. Do not redesign it per PR. Only the data arrays and placeholders change.

Requirements:
- Claude Code signed in to claude.ai, with the `Artifact` and `ArtifactData` tools, and the `artifact-design` and `artifact-capabilities` skills. The page saves verdicts with the artifact `db` capability. If these tools are missing, stop and tell the user. Do not fake the page with a static file: it could not collect verdicts.
- Reviewers can open the artifact and have Contributor or Editor access.

Files in this skill (read them from the skill folder):
- `template.html`: the page. Fill the placeholders and the data arrays.
- `review-template.md`: the summary layout.
- `check.mjs`: checks the filled page before publish.
- `examples/sample-review.md`: a filled set of arrays for a made-up PR.

## Step 0: inputs

Ask for what is missing. Do not invent any of it:
1. The PR (number or link) and the repo. If there is more than one PR, make one page for each.
2. The deadline for verdicts.
3. The reviewers, and how they split the work (for example server, UI, security). If nobody splits it, use one area for everyone.
4. The timezone and locale the reviewers use.
5. The tracker repo for issue links, or "none".

If the PR is trivial (a typo, a version bump), say so and offer to review it directly. A page costs the reviewers time.

## Phase 1: build and publish the review page

1. **Read the PR yourself.** Read the description, the linked issues, the full diff, and the CI result. Note what the PR does, what it deliberately leaves out, and where the risk is (security, data loss, migrations, public APIs, concurrency). Verify against the diff. Do not trust a helper agent's summary for this step.
2. **Write the items.** One item per thing a reviewer can judge by reading a bounded part of the diff.
   - A short title, 1 to 4 things to `look` at, a `good` line ("Fine if") and a `raise` line ("Ask for a change if"). Reviewers read `raise` to decide Change needed.
   - Give a `ref` (`path`, `path:12` or `path:12-40`) for any item tied to code. Give `sev` as `blocker`, `should` or `nit`. A blocker would cause harm if merged as is.
   - Write the item so a reviewer can answer without opening anything else. Short sentences, one idea each.
   - Group items by area in `AREAS`, for example server, UI, security, docs. Put the items everyone checks in one area with `mine:1`. Give each area a rough time in minutes.
   - Give each item a stable `id` (`r1`, `r2`, …) and a number `n`. Never reuse an id for a different item, even when you renumber: verdicts are stored by id.
   - Put the issue number in `iss` (`'#123'`) when there is one.
   - Cover the risk first. Do not write an item for every file. Do not add items for what CI already proves.
3. **Write the rest.**
   - `PREP`: what the PR author does before reviewers start (push, say which commit the guide covers, how to run it). Use `pre` for a command. Reviewers can skip this box.
   - `SUMMARY`: "What this PR does" in plain words, grouped by kind. Include what is left out on purpose, so nobody reviews it.
   - `CONTEXT`: scope and rules (for example "generated files are out of scope", or "Question is not a rejection").
   - `HOWTO`: how verdicts reach the author, and what to report at once (for example a security problem).
4. **Fill the template.**
   - Replace `{{TITLE}}`, `{{EYEBROW}}` (for example `NOTELY · PR #231 · VERDICTS BY WED 7 OCT 2026`), `{{LEDE}}` (two sentences: what the PR is, and who reviews what), `{{SOURCE_LINE}}` (for example "Covers commit `4f2a9c1`, 2 Oct 2026") and `{{ISSUE_BASE}}` (for example `https://github.com/OWNER/REPO/issues/`, or an empty string).
   - Replace `{{TIMEZONE}}` (an IANA name such as `Asia/Kolkata`), `{{TZ_LABEL}}` (for example `IST`) and `{{LOCALE}}` (for example `en-IN`).
   - Replace every `EXAMPLE:` entry in `PREP`, `SUMMARY`, `CONTEXT`, `AREAS`, `ITEMS` and `HOWTO`. Text may use `` `code` `` and `**bold**`; nothing else renders as markup.
   - Check real dates with `date`. Never guess a weekday.
5. **Check and publish.** Run `node check.mjs <filled-page.html>` from the skill folder. Fix every failure. Before writing, load the `artifact-design` and `artifact-capabilities` skills. Publish with the Artifact tool and `capabilities: {"db": {"rules": [{"path": "reviews", "read": "view", "write": "owner"}, {"path": "reviews/{self}", "write": "interact"}, {"path": "audit", "read": "view", "write": "owner"}, {"path": "audit/{self}", "write": "interact"}]}, "user": {"scopes": ["profile"]}}`. The rules let every reviewer read all verdicts and the change log, and let each reviewer write only their own. Each reviewer's verdicts live in one document, `reviews/<person id>`. Each save also adds one event to `audit/<person id>`.
   - Publish a new artifact for each PR, so verdicts never mix. After the author pushes new commits, publish a new page for the new commit. Do not move old verdicts onto changed code. To fix a mistake in the same round, read the page first and republish to its `url`. Keep item ids the same.
6. **Tell the user how to share it.** Reviewers need Contributor or Editor access. Viewer and Commenter access cannot save, and the page may only find out on the first save. The message names the Contributor role.
7. **Check once.** Read the `reviews` collection with `ArtifactData` (`action: list`). It should be empty. Ask the user to open the page. The bar must read "0 of N reviewed", where N is the number of items in the `mine:1` areas. "0 of 0" means the page script failed. Say what you could not test: a real tap needs a signed-in reviewer.
8. **Send the link and the deadline.** Prepare a short message the user can forward to reviewers.

## Phase 2: read the verdicts and write the summary

1. **Read the verdicts and the change log.** Use `ArtifactData` with `action: list` on `reviews`, then on `audit`. Each `reviews` document id is a person id; its `items` map holds, per item id, `{n, status, label, note, at, rev}`, where `status` is `ok`, `fix`, `question` or `skip`. Each `audit` document id is a person id; its `events` list holds `{id, item, n, action, from, to, at}`, where `action` is `verdict` or `change`, and `from` and `to` have the shape `{status, label, note}`. Remove duplicate events with the same `id`. Use `action: profiles` on the person ids to get names.
2. **Tally each item.** Count ok, fix, question and skip. An item is **Change needed** if any reviewer's current verdict is `fix`, **Question** if none asked for a change but someone has a question, **Looks good** if at least one reviewer marked ok and nobody has a change or a question, and **Not reviewed** if it has no verdict other than skip. Say how many reviewers covered each area.
3. **Write the summary** from `review-template.md`, in the place the user names (default `docs/reviews/pr-<number>.md`):
   - Changes first, blockers before the rest, each with the reviewers' notes quoted word for word, the reviewer's name and time, and the `ref`.
   - Then questions, then items not reviewed, then the "Looks good" items in one short table.
   - A "Changed verdicts" list from the `change` events, one line each, in time order.
   - Name only, never email. If two people share a name, add the first 6 characters of their id.
   - Do not say the PR is ready to merge. List what blocks it and let the user decide.
4. **Close the loop, only if the user asks.** Offer to post the changes and questions as review comments on the PR, one comment per item, on the `ref` line when there is one, quoting the reviewer's note and naming them. Do not approve, request changes or post anything without the user's word.
5. **Report** in a short table in chat: item | verdict | reviewers | posted to PR. List anything still not reviewed.

## Rules

- Never put secrets, tokens, phone numbers or email addresses on the page or in the summary. Quote code only as short lines, and never quote a secret that a reviewer finds in a diff. Say where it is and who must rotate it.
- Do not invent a verdict. An item with no verdict is "Not reviewed", never "Looks good".
- Do not mark an item Looks good for a reviewer who skipped it.
- Do not overwrite a page that already has verdicts without saying so. Artifact versions are kept, but say it.
- Keep each item checkable in a few minutes. Split a long item.
