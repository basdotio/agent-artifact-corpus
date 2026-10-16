---
name: powerlifting
description: "Calculating powerlifting scores to determine the performance of lifters across different weight classes. "
---

# Calculating Powerlifting Scores as a Professional Coach

This skill covers the scoring formulas used in International Powerlifting
Federation competition analysis: Dots, IPF GL, Wilks, and Glossbrenner.
It supports downstream tasks that compute per-lifter coefficients and
produce ranking workbooks from raw meet data.

## Scope

The four scoring systems covered here all normalise a lifter's total
across bodyweight so that results from different weight classes can be
compared on a single axis. The formulas differ in their polynomial
shape and in the weight-class ranges they are calibrated against.

## Reference material

The concrete formula definitions, polynomial coefficients, bodyweight
clamps, and reference Rust implementations for every scoring system
live in the companion document **`powerlifting_scoring_reference.pdf`**, which sits in this
skill folder next to this file. Open that PDF first and use the
coefficients it lists when producing any downstream calculator or
workbook — SKILL.md itself does not duplicate the numeric tables.
