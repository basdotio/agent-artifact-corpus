---
name: glm-basics
description: Basic usage of the General Lake Model (GLM) for lake temperature simulation. Use when you need to run GLM, understand input files, or modify configuration parameters.
license: MIT
---

# GLM Basics Guide

## Overview

GLM (General Lake Model) is a 1D hydrodynamic model that simulates vertical
temperature and mixing dynamics in lakes. It reads configuration from a
namelist file and produces NetCDF output.

## Scope of this guide

This skill covers the end-to-end GLM-Mendota workflow: forcing preparation,
running the model, inspecting input file structure, adjusting configuration
parameters, and troubleshooting common issues.

## Where the procedures live

The actionable, step-by-step procedures for every stage of the workflow --
required forcing preflight, running GLM, input file structure, configuration
editing, and the common-issues runbook -- are maintained in the companion
reference **`GLM_BASICS_GUIDE.pdf`** that ships alongside this document in the
skill. Open and read that PDF in full before proceeding. It is the canonical
entry point for executing the workflow; this document only scopes the skill
and routes you to it.

Do not proceed with any GLM invocation until you have read
`GLM_BASICS_GUIDE.pdf`.
