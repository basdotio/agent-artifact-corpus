---
name: github-contrib-import
description: Import the user's real commit history from private, work, or self-hosted git repos onto their GitHub contribution graph by mirroring commit dates and change sizes into a private mock repo — never source code. Use when the user asks to import their contributions to GitHub, show private or work commits on their GitHub graph, or fill their contribution graph with work done elsewhere.
---

# Import contributions to GitHub

Mirror the user's **real** commits from local repos into a private mock repo using
[git-import-contributions](https://github.com/miromannino/Contributions-Importer-For-Github).
Each mirrored commit keeps the original timestamp and a similar amount of changed lines per
file type, but the files contain placeholder text. Source code, file names, and commit
messages never leave the machine.

## Guardrails

- Only import commits the user actually made. Never create fake, padded, or backdated activity.
- Treat source repos as read-only. Never write to them.
- The mirror repo is always **private**.
- Never pass `--keep-commit-messages` (real messages can leak project details).
- Never pass `--commit-max-amount-changes` or `--changes-commits-max-time-backward` unless the
  user explicitly asks: together they split big commits and backdate the pieces by up to days,
  moving activity to times it did not happen. (`--max-commits-per-day` does **not** move
  commits; it only caps how many are kept per day, and the excess is dropped.)
- Never write tokens into files; rely on `gh auth` / the git credential helper.
- Never force-push the mirror.
- Always ask before pushing.
- If any source is a work repo, remind the user to check that their employer allows
  publishing activity metadata (dates and volume), even without code.

## 1. Collect inputs

Ask for anything missing. Do not guess.

1. **Source repo paths** on this machine.
2. **Author identities** the user commits as. Find candidates with
   `git -C <repo> log --format='%an <%ae>' | sort | uniq -c | sort -rn` and confirm with the user
   which ones are theirs.
3. **Mirror repo name** (default `contributions-mirror`).
4. **Commit email for the mirror**, which must be **verified on their GitHub account**
   (github.com/settings/emails), or GitHub will not count the contributions.

## 2. Preflight

```bash
git --version && python3 --version && gh auth status
```

Install the importer in an isolated environment (first that works):

```bash
uv tool install git-import-contributions
```
```bash
pipx install git-import-contributions
```
```bash
python3 -m venv ~/.local/share/contrib-importer && ~/.local/share/contrib-importer/bin/pip install git-import-contributions
```

Confirm with `git-import-contributions repo --help` (use the full venv path for the last option).

## 3. Prepare the mirror repo

If the repo does not exist yet:

```bash
gh repo create <mirror-name> --private --clone
```

Otherwise clone the existing one. Confirm it is private:
`gh repo view <mirror-name> --json visibility` must say `PRIVATE`. Then set the identity:

```bash
git -C <mirror-path> config user.name "<Name>"
git -C <mirror-path> config user.email "<verified-email>"
```

An empty repo is fine; no initial commit is needed.

## 4. Import

`--author` **must** use the `"Name <email>"` form. A bare email is silently ignored by the
tool, which then imports commits from *every* author.

```bash
git-import-contributions repo \
  --repos <repo1> <repo2> \
  --mock_repo <mirror-path> \
  --author "Name <email1>" "Name <email2>" \
  --max-commits-per-day 1000 1000 \
  --ignore-before-date "$(date -d '1 year ago' +%F)" \
  --start-from-last
```

Always pass these defaults:

- `--max-commits-per-day 1000 1000`: the tool otherwise keeps only a random 10–15 commits per
  day and **silently drops the rest**. 1000 keeps every real commit.
- `--ignore-before-date` one year ago: import only the last year, which is what the
  contribution graph shows. On macOS use `date -v-1y +%F`. Use a different date only if the
  user asks.
- `--start-from-last`: resumes after the newest mirrored commit, so re-runs add only new work
  instead of duplicating history. It also means commits older than the newest mirrored one
  are never picked up later; to backfill, rebuild the mirror (needs a force-push, so ask).

Optional, only if the user asks: `--ignored-file-types .lock .csv`,
`--collapse-multiple-changes`.

Check the output:

- `Commit skipped because the author is: …` should list only other people's emails.
- `Commit skipped because the maximum amount of commit for … exceeded` should not appear.
  If it does, report the dates and counts to the user before pushing.

## 5. Verify before pushing

1. **Count**: `git -C <mirror-path> rev-list --count HEAD` should equal the sum over sources of
   `git -C <repo> rev-list --count --all --author=<email>` (roughly; merges and filters can
   differ). Explain any big gap.
2. **Dates**: spot-check 3 source commits against the mirror with
   `git log --format='%ad' --date=iso`. Timestamps must match.
3. **Authors**: `git -C <mirror-path> log --format='%an <%ae>' | sort -u` shows only the user.
4. **No leaks**: `git -C <mirror-path> ls-files` should list only `README.md` and
   `content.<ext>` placeholder files, and `git -C <mirror-path> log --format=%s | sort -u`
   should show only generated messages ("add code in files types: …").

Show the user the count, date spot-check, and author list. **Ask for confirmation**, then:

```bash
git -C <mirror-path> push -u origin HEAD
```

## 6. Confirm re-runs are safe

Run the import command from step 4 again. The commit count must not change.

## 7. Finish on GitHub

Tell the user to enable **GitHub → Settings → Public profile → Contributions & activity →
"Include private contributions on my profile"**. Without it, the private mirror shows nothing
to other visitors. The graph can take a few minutes to update.

To keep the graph current later, re-run step 4 and push, e.g. weekly.
