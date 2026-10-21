# feature-triage

A **template** skill for Claude Code that triages a planning cycle's feature requests for
relevance to your specialty, using a fleet of classifier subagents with quality gates - then
learns from your corrections every cycle.

## What problem it solves

If you are the analytics / security / accessibility / performance / privacy person on a large
product organization, every quarter starts the same way: hundreds of feature requests land in the
tracker and you have to find the ones that concern you. Reading everything takes days; skimming
misses real work. This skill turns that into a supervised pipeline: subagents classify every
request against YOUR written rules, every uncertain call is surfaced to you instead of silently
dropped, and the retro folds your corrections back into the rules so the next cycle is measurably
better.

The method shipped here ran in production for a real quarterly cycle of ~700 feature requests and
reached ~0.9 precision at recall ~1.0 (no silent misses) by its second quarter. The parts that
made that possible are all in the template:

- a **canary gate** (locked test features with known verdicts) that must pass before any fleet spend
- **tiered two-pass triage** - a cheap title-only pass, then full-detail reads only for the maybes
- an **ownership question asked up front** - the most expensive failure was a family of tickets
  built by an external team in a separate product; they read as textbook Yes and were all wrong
- an **arbitration ladder** - contested rows get progressively more context (AC sections, parent
  epic, sibling tickets, comments) instead of a guess
- **verification gates** that distrust the subagents (diff the written output's IDs against the
  assignment; never trust a subagent's own "n classified" summary)
- a **replace-not-append feedback loop** with a performance log per cycle

## Why this ships as a template, not a ready skill

"Relevant" has no generic definition - it is your domain, your products, your organization's tag
conventions, and your tracker's field names. Shipping the seed skill's real rules would be
useless to you (and would leak someone's internal backlog). So this folder ships the pipeline
complete and the rules as a fill-in skeleton.

## Layout

```
feature-triage/
  SKILL.md                              # the pipeline: phases, gates, contracts, feedback loop
  README.md                             # this file
  references/
    classification-template.md          # FILL IN: your rules, examples, and locked canaries
```

## How to adapt it

1. Fork this folder (copy it into your own `~/.claude/skills/`, rename it if you like).
2. Open `references/classification-template.md` and replace every `<placeholder>`: your core
   principle, tag rules, kill rules, positive triggers, ~12 locked canaries, and a starter
   example store. Seed them from your last cycle's manual triage if you have one.
3. Wire your tracker into `SKILL.md`'s subagent contract: the read-only fetch tool, the field
   names, the batch sizes that fit your tracker's API.
4. Run one cycle in SHADOW MODE: classify a past cycle you already triaged by hand, diff the
   output against your own verdicts, and fix the rules until the canaries and the diff look
   right. Set your calibration band (expected Yes %) from that run.
5. Go live the next cycle, and run the retro after your human review - the feedback loop is where
   the real quality comes from.

## Dependencies

Needs read-only tool access to your work tracker (e.g. an Azure DevOps / Jira / Linear MCP
server) and, for the write-back step, your docs tool (e.g. Notion or Confluence MCP). The
subagent fleet uses Claude Code's built-in Agent tool - no extra setup.
