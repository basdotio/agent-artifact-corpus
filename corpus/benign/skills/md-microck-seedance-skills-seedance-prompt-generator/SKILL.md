---
name: seedance-prompt-generator
description: analyze a repo and generate seedance 2.0 montage packs (30s script + 5 segment mini-montage prompts) for software promos.
---

# seedance 2.0 repo prompt generator

generate seedance 2.0 prompts by analyzing the current repository (README, routes/screens, ui strings, assets) and turning that into a **30s montage pack**.

## when to use

use this skill when the user wants:

- motion graphics videos for their app / saas / program
- a repo-driven promo script + prompts (no manual prompt writing)
- a 30s cut built from "best of" generated clips

## core idea: seedance is the engine

seedance is best treated as the engine, not the vehicle. ship results by:

1) generating more than you need
2) selecting the best 1-2 seconds from multiple runs
3) cutting down to a tight final

## the op montage method (default)

- write a 30s script
- split into 5 segments x 6s (final)
- for each segment, generate a 15s mini-montage prompt (overshoot)
- keep the best of the best clips
- cut back down to 30s

keeper rule:
- put the hero moment in **00:00-00:06** of each 15s generation
- use 00:06-00:15 as coverage (alternate angles / salvageable micro-moments)

## repo analysis workflow (do this every time)

1) detect project type (web app, mobile app, cli, library)
- check for `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, etc.

2) extract product narrative
- read `README.md` (and `docs/`, `CHANGELOG*`)
- pull 3-7 crisp product claims: what it does, for whom, why it matters

3) identify showable surfaces
- web apps: pages/routes + nav labels + key components
- clis: key commands/flags + representative output strings
- libraries: public api + short usage snippet

4) locate existing visual assets
- prefer repo images: `assets/`, `public/`, `docs/`, `screenshots/`
- if none: output a screenshot checklist the user can capture in <10 minutes

5) choose a motion style that matches the repo
- if brand cues exist (palette/typography), align
- otherwise default: clean professional product film

## seedance constraints to respect

- inputs: max 9 images (`@Image1..@Image9`), max 3 videos, max 3 audio
- do not rely on tiny text / pixel-perfect ui
- avoid real-person faces and celebrity likenesses

## filter-aware prompting (37% fail rate)

the content filter is an LLM that reads context, not keywords:

- **lead with cinematic language**: "cinematic wide shot, 35mm film grain, 16:9" → creative context = higher pass rate
- **describe characters by role, never age**: "rider" not "young boy", "figure" not "child"
- **build context around sensitive elements**: wrap actions in narrative/film language
- **faces in image inputs = auto-reject**: crop to back of head/shoulders or use wide shots
- **every sentence earns its place**: either describe what camera sees OR anchor as cinematic

## output contract

return exactly this structure:

```
## seedance montage pack: <project name> (30s master)

### repo-derived notes
- product: ...
- audience: ...
- key features/screens to show: ...
- brand/style cues detected: ...

### asset plan (upload order)
@Image1: ...
@Image2: ...
@Image3: ...
@Video1 (optional): ...
@Audio1 (optional): ...

### 30s script (5 x 6s)
- segment 1 (0-6s): ...
- segment 2 (6-12s): ...
- segment 3 (12-18s): ...
- segment 4 (18-24s): ...
- segment 5 (24-30s): ...

### segment prompts (15s mini montages)

#### segment 1 prompt (recommended)
<paste-ready seedance prompt>

#### segment 1 prompt (alternate)
<paste-ready seedance prompt>

... repeat for segments 2-5 ...

### assembly notes
- generation plan: ...
- selection rubric: ...
- editing plan: ...

### variants
- 9:16 notes: ...
- 16:9 notes: ...
```
