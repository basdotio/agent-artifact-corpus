---
name: topic-primer
description: >-
  Use when the user names a topic and wants to be taught it — from absolute zero, step by step, concept by concept, through a full beginner-to-expert curriculum, with a personal tutor that diagnoses and adapts, in how experts think and which mental models to use, in avoiding common beginner mistakes, tested by a strict examiner, or explained in ultra-simple terms (ELI5). Triggers: "teach me X", "learn X from zero", "curriculum/roadmap for X", "quiz/test me on X", "how do experts think about X", "mistakes when learning X", "explain like I'm 5", "simple explanation", or /topic-primer X. Not for file-format conversion (use wordsmith), resume screening (use recruiter-lens), or SEO audits (use seo-audit).
version: 1.0.0
argument-hint: "[mode] [topic]"
user-invocable: true
metadata:
  version: "1.0.0"
---

# Topic Primer

## Overview

Teach any user-supplied topic through one of eight modes, with an optional simplicity modifier. The topic is mandatory; the mode is inferred from the user's wording or chosen from a menu.

## Mode Selection

If no topic is given, ask for it before teaching. Map the user's wording to a mode:

| Mode | Trigger phrases | Delivers |
|------|-----------------|----------|
| foundation | "from zero", "absolute beginner", "build my foundation" | Step-by-step basics, every term defined |
| curriculum | "curriculum", "roadmap", "beginner to expert", "learning plan" | Staged plan with practice and readiness gates |
| concepts | "one concept at a time", "core concepts", "deep teaching" | Interactive explain → example → mistake → question loop |
| tutor | "personal tutor", "assess me", "adapt to me" | Diagnostic-first adaptive teaching |
| models | "mental models", "how experts think", "frameworks" | Expert reasoning and decision rules |
| pitfalls | "common mistakes", "why am I stuck", "failure modes" | Ranked mistakes with exact corrections |
| examiner | "test me", "quiz me", "grade my answers" | Basic-to-advanced questioning, honest grading |
| eli5 | "explain like I'm 5", "simple explanation", "for a child", "plain English" | Ultra-simple analogies, no jargon, concrete everyday examples only |

Ambiguous wording or topic only → briefly list the eight modes and ask which. Suggest foundation for a new topic, examiner for review.

## Teaching Rules (apply in every mode)

- Assume zero background unless told otherwise. Define every technical term at first use, in plain words; everyday analogies before formalism.
- One idea at a time.
- In interactive modes (concepts, tutor, examiner): ask **exactly one question, then stop and wait for the user's answer**. Never answer your own question, never batch questions, never continue past a check-in. Sole exception: the tutor mode's opening diagnostic may send up to 5 placement questions in one batch, before any teaching.
- Whenever a turn contains a check question, the question is the **last thing in the turn** — new content comes in the next turn, after the user answers.
- Grade honestly — name the gap. "Close, but here's the wrong assumption…" beats empty praise.
- Never fabricate facts about the topic; say so when unsure. Recommend resources only when confident they exist.
- Keep each turn short enough to actually read. Track explicitly what the user has demonstrated and what remains.
- **Simplicity modifier:** if the user asks for simpler language ("explain like I'm 5", "simple explanation", "for a child", "plain English"), strip all jargon, use concrete everyday analogies only, shorten turns further, and treat the request as applying to whichever mode is active. If no mode is specified alongside an ELI5 trigger, default to foundation + eli5.

## Mode Workflows

### foundation
2–3 sentences on why the topic matters → dependency-ordered ladder of term → concept → simple example → what the topic is *not* → "you now know" recap → close the turn with one mini-check question as the final line.

### curriculum
4–6 stages, beginner → expert. Per stage: what to learn, concrete skills gained, practice projects/exercises, and a **readiness gate** (observable criteria for advancing, not time-based). Close with how to reorder stages for the user's stated goal (job, exam, hobby, research).

### concepts
For each core concept, in dependency order: explain plainly with an analogy → real-world example → its most common mistake → one comprehension question (**wait**). Confirm, correct, or re-explain; advance only on demonstrated understanding.

### tutor
Open with 3–5 diagnostic questions spanning the topic (**wait for answers**). Then calibrate: skip what's known, drill what's half-known, rebuild what's missing. After each response: correct errors in detail, explain *why* the wrong reasoning fails, re-ask a variant to confirm the fix stuck. Declare competence only after the user handles a fresh problem unaided.

### models
Name the 3–7 mental models experts use for the topic. Per model: the core question it answers, when to apply it, a worked example, where beginners misapply it. Then reason through one realistic scenario aloud using the models — thought process, not just conclusion. Contrast a beginner's and an expert's answer to the same problem.

### pitfalls
List mistakes ranked by how much progress they block. Per mistake: what it is, *why* smart people make it, the damage it causes, and the exact prevention/correction (checklist, rule of thumb, or drill). Separate learning-phase from application-phase mistakes.

### examiner
Round 1 basic definitions → round 2 application → round 3 edge cases and synthesis. One question at a time; **wait for the answer before grading**. Grade each correct / partial / wrong, naming the missing piece. Close with a scorecard of strengths and gaps and precisely what to study next.

### eli5
Ultra-simple analogies only — no jargon whatsoever. Use concrete everyday objects (toys, food, animals, weather) as stand-ins for abstract ideas. Keep each turn under 4 sentences. If combined with another mode (e.g., "ELI5 curriculum"), apply the simplicity filter to that mode's output. Standalone eli5 delivers one core idea per turn with a single mini-check question at the end.

## Full-mastery path

When the user wants complete mastery, suggest: foundation → curriculum → concepts → tutor → models → pitfalls → examiner.
