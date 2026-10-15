# Research: cinewright-edit

Findings that back [SKILL.md](SKILL.md). Changes they caused are logged in [CHANGELOG.md](CHANGELOG.md); procedural lessons live in [LEARNINGS.md](LEARNINGS.md); test runs and their evidence in [TESTS.md](TESTS.md); schedule and state in `evergreen.json`. Protocol: [MAINTENANCE.md](MAINTENANCE.md).

Topic: Film editing for AI video: assembly from takes, Murch's rule of six, J and L cuts, match cuts, cutting on action, pacing and average shot length, cutting around bad frames, cutting a battle, conform with ffmpeg. Tier `slow`. Last refresh 2026-10-04; next due 2027-02-01.

## Current understanding

- Settled (craft): the rule of six and its order (Murch 2001), split edits, match cuts, cutting on action, a re-establishing wide in battle cutting (Katz 1991, Dancyger 2019, Reisz and Millar 1968).
- Settled (runtime, 2026-10-04): a multi-shot generation's internal cuts are found by ffmpeg scene detection; a frame-accurate conform needs a re-encode (trim, atrim, concat), never stream copy.
- Approximate: average shot length figures by period (Bordwell 2006), not checked against a shot database this session.
- Unverified: how long generated clips take to settle at the head across models (0.1-0.5 s is practice, from one local model).

## Open questions

- Do hosted models (Veo, Kling) show head settle frames, and how many?
- Is a J or L cut worth cutting a multi-shot generation apart for, or do models' own cuts already carry dialogue well?

## Search plan

Four tracks; every refresh runs at least one query on each, scoped to the time since the last refresh.

Subject:

- `film editing technique cutting on action pacing <year>`
- `Murch rule of six editing <year>`

Tooling:

- `path:SKILL.md "video editing"` on GitHub code search; skills.sh weekly installs for `video editing`
- `https://registry.modelcontextprotocol.io/v0/servers?search=video%20editing`

Practice:

- `AI video editing generated clips cut <month> <year>`
- `ffmpeg scene detection trim concat frame accurate <year>`

Testing:

- `automatic video editing evaluation benchmark <year>`
- `path:SKILL.md editing evals`

Best sources (primary first): Murch, In the Blink of an Eye; Dancyger, The Technique of Film and Video Editing; Reisz and Millar; the ffmpeg filter documentation. Noisy: listicles of transition types without reasons.

## Findings log

Newest first. `Track` is subject, tooling, practice, or testing.

### R-20261004-1 · 2026-10-04 · Initial research
- Summary: Built from the research brief §3 editing row (subject: Murch's six with his weights, J and L cuts, match and smash cuts, cut on action, average shot length), the ffmpeg filter documentation (tooling: trim, atrim, concat, scene detection; checked this session), the S5 exit check on the S2 render (practice: internal cuts at 6.000 s and 10.458 s, 336 frames conformed to 14.000 s), and TESTING.md (testing: a cut list file and a conform whose length matches it are checkable evidence).
- Track: subject
- Sources: https://ffmpeg.org/ffmpeg-filters.html
- Magnitude: n/a (initial)
- Applied: C-20261004-1
