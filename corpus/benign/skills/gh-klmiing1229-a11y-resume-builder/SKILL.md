---
name: resume_builder
description: Refines a resume in four steps: scan the existing resume, ask a few follow-up questions, rebuild it in a proven one-page layout (header, education first, achievement bullets, skills last), then list what changed. Use when the message starts with "resume", or the user asks to improve, fix, rewrite or tailor their resume or CV. Not for cover letters or interview practice.
---

# resume_builder

This skill is a thin wrapper. The full method is in `PROMPT.md` beside this file.

## The trigger
- A message that starts with the word `resume`, e.g. `resume`, `resume for a consulting internship`.
- Natural phrases: "improve my resume", "rewrite my CV", "tailor my resume to this job".
- Not for cover letters, interview practice or job search advice. Say so and stop.

## What to do
1. Read `PROMPT.md` in this folder.
2. Follow it exactly, from Step 1 (Scan) to Step 4 (Report changes). Start with its Step 1 line.
3. Do not add rules that are not in `PROMPT.md`, and never invent a fact or number for the user.
