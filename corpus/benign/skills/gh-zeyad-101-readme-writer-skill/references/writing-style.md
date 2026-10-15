# Writing Style Rules

A README that reads like it was generated is worse than a rough one a human
wrote. Apply these when drafting, and again as a pass over the finished
draft.

## Ban list (don't write these unless the repo evidences the claim)
- Throat-clearing openers: "In today's fast-paced world...", "This project
  aims to...", "Welcome to..."
- Unearned superlatives: "blazing fast", "seamless", "robust", "powerful",
  "cutting-edge", "state-of-the-art", "enterprise-grade", "next-generation"
  — only usable if a real benchmark, spec, or design doc in the repo backs
  the specific claim, and then say the number instead of the adjective.
- Generic feature bullets that just restate the tech stack ("Built with
  modern technologies", "Easy to use and extend", "Highly customizable").
- Closing filler ("Happy coding!", "We hope you enjoy...", "Feel free to
  reach out with any questions!") unless the repo owner's own voice
  elsewhere in the repo does this.
- Padding a section to look complete: if there's one real config option,
  say the one; don't invent two more one comment.

## Positive rules
- Use the project's own names: real function/class/module names, real file
  paths, real command names — not paraphrases like "the main module" when
  the file is called `sensor_fusion.cpp`.
- Vary sentence openers across bullets. Don't start every line with
  "Provides..." / "Enables..." / "Supports...".
- Pull numbers from manifests and config, not estimates: dependency
  versions, supported language/runtime versions, actual measured values if
  present in code comments, benchmarks, or commit messages — never invented
  ones.
- Write for the audience implied by the repo: a firmware repo's README
  should read like an engineer who's flashed a board explaining it to
  another engineer, not a marketing one-pager.
- Badges: only add ones with real evidence — a CI badge only if a workflow
  file exists, a license badge only if a LICENSE file exists, a version
  badge only if there's a real version string (package.json/Cargo.toml/tag).
  No coverage/quality badges without a coverage tool actually configured.
- If the repo already has a README, don't copy its wording — read it for
  facts (real usage examples, real gotchas) worth carrying over, then write
  fresh. If it states something the new inventory can't verify, leave it
  out and don't silently invent a replacement.
- Prefer short, declarative sentences over compound ones stacked with
  commas — this is documentation, not prose.

## Omission over fabrication
Every section in the draft must trace to something you actually found:
a file, a config value, a function signature, a comment, a commit message,
a CI step. If you can't point to the evidence, don't write the line —
cut the section instead of leaving a bracket, a "TBD", or a guess.
