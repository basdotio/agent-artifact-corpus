---
name: glm-calibration
description: Calibrate GLM parameters for water temperature simulation. Use when you need to adjust model parameters to minimize RMSE between simulated and observed temperatures.
license: MIT
---

# GLM Calibration Guide

## Overview

GLM calibration involves adjusting physical parameters to minimize the
difference between simulated and observed water temperatures. This skill
documents the calibration parameter surface, the canonical optimizer
configuration, the manual adjustment strategy, and the required preflight for
parallel sweeps.

## Scope

- Applies to GLM 3.x (Fortran namelist configuration).
- Target RMSE threshold: < 2.0 °C.
- Applies to both single-node calibration and coordinated sweeps.

## Required Reading

All actionable procedures — the parameter table, the optimizer code, the
manual strategy, and the mandatory preflight — have been moved to the
companion reference `glm_calibration_procedures.pdf` (located next to this file). Open
`glm_calibration_procedures.pdf` and follow its steps in order before running the optimizer
or modifying any namelist parameter. Do not proceed from this overview alone;
it intentionally omits the concrete procedures so that the reference stays the
single source of truth.
