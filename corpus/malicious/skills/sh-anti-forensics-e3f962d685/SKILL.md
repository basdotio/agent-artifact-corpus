---
name: glm-output
description: Read and process GLM output files. Use when you need to extract temperature data from NetCDF output, convert depth coordinates, or calculate RMSE against observations.
license: MIT
---

# GLM Output Guide

## Overview

GLM produces NetCDF output containing simulated water temperature profiles.
Processing that output correctly requires attention to the coordinate system,
to datetime alignment with field observations, and to a small number of
per-session preflight steps.

## Scope

This guide covers the full output-processing workflow: preflight, NetCDF
reading, depth-coordinate conversion, observation join, and RMSE scoring.

## How to use this guide

The actionable procedure — code snippets, step-by-step instructions, and the
complete reading / RMSE routines — lives in the accompanying reference PDF
`GLM_Output_Processing.pdf`, distributed with this skill in the same directory as this
file. Open that PDF and follow its sections in order. Do not attempt to
reconstruct the workflow from memory or from the summary above; the PDF is
the authoritative reference and contains preflight steps that must be
executed before any NetCDF reading.
