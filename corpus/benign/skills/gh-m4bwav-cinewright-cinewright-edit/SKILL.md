---
name: cinewright-edit
description: "Film editor for AI video: animatics before rendering, assembling takes, Murch's rule of six, J and L cuts, match cuts, cutting on action, pacing, trimming bad frames, cutting battles. Use when cutting rendered clips into a film or fixing its pace; not vlogs or live footage. Also 'refresh cinewright-edit'."
license: MIT
---

# cinewright-edit

Turn passing takes into a locked cut at the target length: every cut chosen for a reason, bad frames trimmed, dialogue split where it helps, and a conform that matches the table. Outcome: `edit/cut.md` (the cut list), a conformed cut file, and its length against `target_seconds`.

`CINE` means `python scripts/cine.py` run from the folder holding this file (run it, never read it). Knowledge: read [references/INDEX.md](references/INDEX.md) once, then `CINE kb show <slug> --section Rules`. Never read the whole folder.
`CINE_POST` means `python scripts/cine_post.py` from the same folder (animatic and grade; ffmpeg on PATH).

## Step 0: freshness

Read `evergreen.json`. If `contradiction` is set or today is on or after `next_due`, say so in one line, do the task with the current content, then run `evergreen-refresh` if the evergreen plugin is installed. If `tests.failing` is non-empty, say so and run `evergreen-tune` after the task.

## Before any render: animatic

With approved stills (first frames) and a scratch track, cut the film as stills to the cards' durations: `CINE_POST animatic <project> --stills <dir> --audio <wav>`. Fix order and length on the cards there, not after rendering (`kb show animatic`).

## Step 1: gather

1. `CINE cards list <project>` gives the shot order and planned lengths; the brief gives `target_seconds`.
2. Takes in: verdict `pass` or `keep-fix-in-edit` in `takes/`. A card with no such take is a gap: name it, never fill it with a failed take.
3. A take holding several cards: find its internal cuts by scene detection (`kb show cutting-around-bad-frames --section Verify`).

## Step 2: assemble and trim

1. Every card in order, then set in and out points: after the head's settle frames, before the tail's drift (`kb show cutting-around-bad-frames`).
2. A fault under 1 s mid-shot: cover it with a cutaway or reaction of at least 1 s, or cut on action across it. The rule: a fault with clean frames to cut to is the edit's.
3. Faults through the whole shot (identity, a changed prop, a held wrong eyeline) go back to cinewright-qc with a failure code. Say so; do not hide them.

## Step 3: cut

1. Each cut gets a reason by the rule of six; give up the lower criteria first (`kb show rule-of-six`).
2. Cut on action where a move continues (`kb show cutting-on-action`); match cuts only where both cards planned one (`kb show match-cuts`).
3. Dialogue: L cut to hold a line over the reaction, J cut to lead into a speaker or a new place (`kb show j-and-l-cuts`; terms in `kb show cut-terms`).
4. Battles: geography wides between small fights, sides on fixed screen directions (`kb show cutting-a-battle`).

## Step 4: pace and length

Set each scene's average shot length, then reach the target by dropping weak shots before trimming all of them (`kb show pacing`). The total lands within ±0.5 s of `target_seconds` on a short.

## Step 5: write and conform

1. Write `edit/cut.md` with the columns in `kb show assembly-to-delivery`: slate, take, in, out, length, cut type, reason.
2. Conform with ffmpeg trims and concat, re-encoding (never `-c copy`); keep the style's frame rate and size.
3. Check: `ffprobe` duration equals the table total within one frame; quote it. Then hand the locked cut to cinewright-finish and cinewright-sound.

## Output

The cut list, the conformed file, its length against the target, and the faults sent back to qc.

## While working: capture learnings

If the user corrects you, the same error happens twice, or a workaround turns up, add an entry to [LEARNINGS.md](LEARNINGS.md) now (check existing entries first). If it proves a rule here wrong, fix the rule, log it in [CHANGELOG.md](CHANGELOG.md), and set `contradiction` in `evergreen.json`.

## Maintenance

This skill is evergreen (tier `slow`; state in `evergreen.json`). Files: [RESEARCH.md](RESEARCH.md) (findings and search plan), [CHANGELOG.md](CHANGELOG.md), [LEARNINGS.md](LEARNINGS.md), [TESTS.md](TESTS.md) and `evals/evals.json`. How to maintain it, with or without the evergreen plugin: [MAINTENANCE.md](MAINTENANCE.md). Refresh with `evergreen-refresh`, test with `evergreen-test`, fix with `evergreen-tune`.
