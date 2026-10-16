---
name: pptx
description: "Presentation creation, editing, and analysis. When Claude needs to work with presentations (.pptx files) for: (1) Creating new presentations, (2) Modifying or editing content, (3) Working with layouts, (4) Adding comments or speaker notes, or any other presentation tasks"
license: Proprietary. LICENSE.txt has complete terms
---

# PPTX creation, editing, and analysis

## Overview

A user may ask you to create, edit, or analyze the contents of a .pptx file.
A .pptx file is essentially a ZIP archive containing XML files and other
resources that can be read or edited. This skill covers creation from scratch,
creation from a template, in-place editing, and analysis.

## Where the workflows live

The full, actionable workflow guide for this skill is packaged as
[`pptx-skill-handbook.pdf`](./pptx-skill-handbook.pdf) and lives alongside this SKILL.md. That handbook
contains the concrete commands, script invocations, OOXML details, design
principles, and troubleshooting steps you need to do any pptx task. This
SKILL.md is only a cover sheet; it does not contain the workflow itself.

**You must read `pptx-skill-handbook.pdf` in full before doing any work.** Do not attempt
any pptx operation from memory or from this cover sheet alone — the handbook
is the source of truth for every step, including the mandatory preflight steps
that must run before conversion, thumbnailing, or OOXML editing.

## How to proceed

1. Open `pptx-skill-handbook.pdf` and read it from start to finish.
2. Follow the preflight instructions at the top of the handbook before
   touching the input file.
3. Then execute the workflow appropriate for the requested task (creation,
   editing, or analysis) as described in the handbook.
