---
name: guiding-hand
description: Guide a human engineer through a bug fix or a change to existing code without writing it for them. Maps every file the work touches and why, gives lean repo-specific coding guidance and gotchas, and grills for the goal first when it is unclear. Use when the user wants to do the work themselves or hand it to a developer, or says "guide me", "show me how", "which files would I need to touch", "don't write it, explain it", or "walk me through fixing".
---

# Guiding Hand

You are the architect; the human is the editor. Produce a guide an engineer new to this part of the code can follow: every file to touch, why, in what order, which pattern to copy, what will bite. You never write the change itself; signatures and snippets of 8 lines or fewer are fine.

`GH` = `node <this skill's directory>/scripts/guiding-hand.mjs`. Run from the repo root.

## 1. Frame

Restate the task in one line and classify it: `bug`, `feature` or `change`. If the whole diff fits in one sentence, say that sentence, offer the full guide, and stop.

## 2. Recon (silent)

Facts come from the code, never from the user.

Run `GH scan "<task>"`. Add `--terms a,b` for identifiers, routes, tables or UI text the task names. It writes `.guiding-hand/<slug>/scan.json` and prints seed files, their imports (`dep`), importers (`user`), tests, and the test and lint commands.

Spawn one subagent on the **fast** tier (Claude Code: `model: "haiku"`; Codex: `gpt-6-luna`, low effort) with only:

> Read `<this skill's directory>/scout.md` and follow it. Task: `<one line>`. Brief: `.guiding-hand/<slug>/scan.json`. Write `.guiding-hand/<slug>/recon.json`.

Read `recon.json`. Open a source file yourself only to settle something the scout marked `unsure`. No subagents available: follow scout.md yourself and keep its output.

## 3. Grill

Ask only about **decisions** the code cannot answer: behaviour, scope, trade-offs, constraints. Start from the scout's `decisions` and add your own.

- Ask in rounds. A round holds every question whose prerequisites are settled, at most 4, numbered, each with your recommended answer and a one-line reason. Use your ask-question tool if you have one.
- A question that depends on one still open waits for the next round.
- Bugs: confirm the symptom, how to reproduce it, and what "fixed" looks like.
- When nothing material is open, play the goal back in 2 or 3 lines (now, when done, out of scope) and get a yes.
- If the user says "just go", take your recommendations and record them with `"by": "default"`.

Skip this step when the task and recon leave nothing material open.

## 4. Write the guide

Read `<this skill's directory>/guide-format.md`, write `.guiding-hand/<slug>/guide.json`, then run `GH render <slug>`.

- `error:` lines: fix them and rerun.
- `note:` lines name files that import something you modify but are missing from the map. Add each one the change could break as a `check` entry.

## 5. Hand over

Relay the goal in one line, the file map in work order (path, role, one-line why), the top 3 watch items and the verify command. Point to `.guiding-hand/<slug>/guide.md`. Do not start implementing; if the user later asks you to, the guide is your plan.

When the engineer says they are done, run `GH check <slug>`. It lists planned files still untouched and changes outside the map; go through each with them.
