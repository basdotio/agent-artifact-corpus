---
name: opensource-project-init
description: How Taylor Arndt sets up an open-source project on GitHub, start to finish - git init, creating the repo on the personal account, README with the origin story, issue templates, pull request template, security and community policies, MIT license, topics, contrib.rocks, CI with GitHub Actions, going public, and cutting a release. Use this whenever Taylor asks to push a project to GitHub, open-source something, "init" or set up a repo, make a repo public, add issue templates, policies, a license, topics, GitHub Actions, or a release - even if only one of those is asked for, because the rest of the checklist tells you what is still missing and how Taylor wants each piece done.
---

# Open-source project init

This is how Taylor takes a folder of working code and turns it into a public
open-source repository. It was written from a real setup (claude-watch) and
records the choices Taylor made along the way, so later projects come out the
same without Taylor having to repeat them.

Taylor usually asks for these one piece at a time ("push it", then "add issue
templates", then "make it public"). Do the piece that was asked for, do it
fully, and then say in a line or two which parts of this checklist the repo
still lacks. Do not silently do the whole list when only one item was
requested: making a repo public or picking a license are Taylor's calls.

## Who you are setting this up for

Taylor is blind and uses a screen reader, and builds accessible software. That
shapes the repo as much as the code:

- No emoji or decorative characters in READMEs, templates, policies, or release
  notes. They are noise when read aloud.
- Every image gets real alt text, including badges and the contributors image.
- Use GitHub issue *forms* (YAML), not Markdown issue templates. Forms are
  labelled fields a screen reader can move through; Markdown templates are a
  wall of text to edit around.
- Write in plain, direct sentences. Headings carry the structure.
- Say so in CONTRIBUTING: output must make sense read aloud as plain text.

## The order of work

### 1. Look before pushing

Pushing publishes. Before the first push:

- List the folder and read what is there. Check whether it is already a git
  repository and whether the repo name is already taken on GitHub.
- Scan every file for secrets (API keys, tokens, passwords, private URLs). If
  you find one, stop and tell Taylor rather than pushing.
- Add a `.gitignore` suited to the language (at minimum `.DS_Store` and build
  or cache folders).

### 2. Create the repo, private first

- `git init -b main`, one initial commit, then
  `gh repo create taylorarndt/<name> --private --source=. --remote=origin --push`
  with a one-line `--description`.
- "My personal GitHub" means the `taylorarndt` account. Confirm with
  `gh auth status` that it is the active account.
- Start private unless Taylor says public. Private to public is one command;
  public to private does not un-publish anything. Tell Taylor it is private and
  how to flip it.
- Commit and push after each piece of setup, with a short message that says
  what changed. Taylor expects the work to be on GitHub when you say it is
  done.

### 3. README

Taylor's READMEs carry these sections on top of the project's own docs. The
wording is in `assets/README-sections.md`.

- **Why this exists.** The origin story, near the top: who asked for it or what
  problem annoyed Taylor into building it. Taylor will usually give you this in
  a sentence ("this started because Michael wanted a way to get notified when
  Claude needs you"). Keep Taylor's wording, tidy it, and add at most a couple
  of sentences about the problem. Tell Taylor what you added so it can be
  changed if it does not sound right.
- **Honest platform status.** If something has not been tested, the README
  says so in plain words: in the intro, in that section's heading
  ("Windows (experimental, untested)"), and in Requirements. Taylor would
  rather under-promise than have someone find out the hard way. Never describe
  untested work as supported.
- **Contributing**, linking to the policy files.
- **Contributors**, using contrib.rocks, with alt text on the image.
- **License**, one line linking to the file.

### 4. Issue templates and the pull request template

Copy from `assets/.github/` and adapt:

- `ISSUE_TEMPLATE/bug_report.yml` and `feature_request.yml`: adjust the
  operating system list and ask for the project's diagnostic output if it has a
  diagnostic command.
- `ISSUE_TEMPLATE/platform_test_report.yml`: only when a platform ships
  untested. It gives people a checklist of what to try, which turns "it is
  experimental" into something testers can act on. Create the matching label
  with `gh label create`.
- `ISSUE_TEMPLATE/config.yml`: blank issues off, plus a contact link to private
  security reporting, so nobody posts a vulnerability in public by accident.
- `PULL_REQUEST_TEMPLATE.md`: one template. It asks what changed, why, and how
  it was tested, including a box for "not tested on a real machine".

Validate the YAML before pushing (`ruby -ryaml -e "YAML.load_file('...')"`
works on a stock Mac). A broken form silently disappears from the chooser.

### 5. Policies

From `assets/`, with every `REPLACE` filled in from the actual project:

- `SECURITY.md`: report privately through GitHub security advisories. Include a
  "what this project touches" section listing files it edits, data it stores,
  background jobs, and programs it starts, written from reading the code. That
  section is what makes the policy useful instead of boilerplate.
- `CONTRIBUTING.md`: ways to help, how to run it locally, the few rules a
  change must not break, the accessibility rule, and pull request expectations.
- `CODE_OF_CONDUCT.md`: Contributor Covenant 2.1 by link with a short summary.
- `SUPPORT.md`: where to go for help, in order.

Contact goes through GitHub (the advisory form and the `@taylorarndt` profile).
Do not publish an email address in the repo.

### 6. License

MIT, and the copyright line is `Copyright (c) <year> Taylor Arndt`.

Personal projects are Taylor's, not the company's. Do not put Techopolis in the
copyright line unless Taylor says this particular project belongs to
Techopolis. If there is no license yet, do not add one unasked: say there is
none, explain in one sentence why that matters once the repo is public, and
recommend MIT. After adding it, confirm GitHub detected it
(`gh api repos/OWNER/REPO/license -q .license.spdx_id`).

### 7. GitHub Actions, when they earn their place

Add CI when the project claims to work on a platform or version that was not
tested by hand; that is exactly what a hosted runner can check. Start from
`assets/.github/workflows/ci.yml`:

- Matrix over every operating system the README claims, and the oldest and
  newest language version it claims.
- Prefer one end-to-end smoke test that drives the tool the way a user would
  over many unit tests. Use a throwaway state directory so the test is safe to
  run on Taylor's own machine too.
- `permissions: contents: read`. No secrets unless the project needs them.

Do not add workflows for their own sake (no release automation, linters, or
bots unless asked). After pushing, watch the first run with `gh run watch` and
read the result. If the jobs never start, check the annotations
(`gh api repos/OWNER/REPO/check-runs/<job id>/annotations`): an account billing
lock shows up there, and that is for Taylor to fix, not something to work
around. Until CI has passed, the README must not claim the platform is tested,
and do not add a CI badge that would show as failing.

### 8. Going public

Only when Taylor asks. Then, in one go:

- `gh repo edit OWNER/REPO --visibility public --accept-visibility-change-consequences`
- Topics with `--add-topic`: about ten to twelve, covering what it is, what it
  works with, the language, the platforms, and `accessibility` when that is
  part of the project.
- Turn on private vulnerability reporting
  (`gh api -X PUT repos/OWNER/REPO/private-vulnerability-reporting`) so the
  SECURITY link works. This and contrib.rocks only work on public repos, so
  say so if policies were added while the repo was still private.
- Check the commit author email (`git log --format='%ae' | sort -u`). If it is
  a machine-local address, the commits will not link to Taylor's GitHub
  profile; mention it and how to fix it, and leave git config alone.

### 9. Release

When asked for a release:

- The tag is `v` plus the version the code itself reports. If they disagree,
  fix the code's version first.
- `gh release create vX.Y.Z --title "<project> X.Y.Z" --notes-file <file> --target main`
- Notes, in this order: one sentence on what the project is, what it does (or
  what changed since the last release), platform support with the same honest
  tested and untested wording as the README, and how to install.
- No emoji in release notes.

## Reporting back

After each piece, tell Taylor in plain sentences what was added and give the
repo link. Then list anything that needs a decision or will not work yet, such
as "the repo is still private, so the contributors image will not show", "there
is no license", or "CI could not run because of a billing lock". Taylor makes
those calls quickly once they are stated clearly.

## Checklist

Use this to see what a repo still lacks:

- Secrets scan done, `.gitignore` present
- Repo on `taylorarndt`, private until told otherwise
- README: why this exists, honest platform status, contributing, contributors,
  license
- Issue forms: bug, feature, platform test report if needed, config with blank
  issues off
- Pull request template
- SECURITY, CONTRIBUTING, CODE_OF_CONDUCT, SUPPORT
- MIT license, copyright Taylor Arndt
- CI on the claimed platforms, if any are untested by hand
- Public, topics set, private vulnerability reporting on
- Release tagged to match the code's version
