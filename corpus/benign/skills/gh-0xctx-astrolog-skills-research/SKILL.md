---
name: research
description: Astrology research across many charts with astrolog-skills — build chart sets (Astro-Databank samples, CSV, saved charts), sweep hundreds of harmonics against a proper chance baseline (midpoint structures by the old and new methods, two-planet aspects), compare the methods, compare groups, and save reproducible runs. Use when the user wants to test an astrological idea on a group ("are musicians strong in the 7th harmonic?"), compare professions or events, search a database for patterns, or asks about statistics, controls or significance.
---

# Research across chart sets

## 1. Turn the question into a set

- Data: the user's own charts (`astro --json chart list`), a CSV (`name,date,time,tz,lat,lon,place,rating,tags`), or
  Astro-Databank XML — their licensed copy or the free sample: `astro data fetch-sample` (≈5,700 timed charts; for their
  own research only — never publish or share ADB data or its category/biography text).
- Find categories for the question: `astro --json data categories --grep music`.
- Create the set, ideally AA/A-rated only:
  `astro --json set create musicians --adb ~/.astrolog-skills/data/c_sample.xml --rating AA,A --category "Vocation : Entertain/Music"`
  Anonymous research groups are excluded by default. Check it: `astro --json set show musicians` (size, ratings, genders,
  categories). Fewer than ~100 charts → warn that results will be noisy.

## 2. Sweep

`astro --json research sweep musicians --range 1-32` (or 1-180; `--shuffles 40` for finer p-values; `--seed` for
repeatability; `--control SET` to also show another group's means; `--measures new,old,aspects` to choose). It casts
the set and control groups in single Astrolog runs (seconds for hundreds of charts) and saves the run.

Each harmonic is measured three ways — the same as `astro harmonics` ranks one chart (see the harmonics skill):
- **new** — midpoint structures by the new natal-referenced method, each structure counted at its own vibration;
- **old** — midpoint structures by the old method (direct contacts in the harmonic chart);
- **aspects** — two-planet aspects (the pack's pair score).
The last line says which measure separates the set from chance: comparing **new** and **old** on the same set is the
controlled test the new method's proposer asks for — report it as such, and say plainly when neither stands out.

What the numbers mean:
- **observed** = the set's mean of that measure in that harmonic; **expected** = the same on **control charts built from the
  set's own years, days, times and places recombined** (real skies at comparable moments — astronomy preserved,
  people removed). **ratio** = observed/expected; **z** = distance from expected in control-group spreads.
- **adjusted p** accounts for testing every harmonic in the range at once (max-statistic over the control groups).
  ≤ 0.05 "notable", ≤ 0.2 "suggestive", otherwise chance. With 20 control groups the smallest possible p is ~0.05.

## 3. Report honestly

- Lead with the adjusted p, not the raw z. "Nothing stands out beyond chance" is a valid, useful finding — say so.
- Everything is exploratory (the method's own caveat): a notable harmonic is a lead to examine (look at its strongest
  charts, read their patterns, replicate on another sample), not proof.
- Don't fish: if the user tries many sets/ranges until something is notable, point out the multiple testing.
- Name the set, its filters and size, the range, pack and run id (`astro research list`, `astro research show RUN`).
