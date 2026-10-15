---
name: audio-production
description: Generate and integrate local sound effects and other audio. Use when asked to build, finish or improve a game, edit a video, animate a scene, or create an interactive application or website where sound contributes to the requested result, even if audio is not mentioned. Also use for explicit audio requests. Do not use for unrelated analysis, documentation or refactoring, intentional silence, or when suitable audio already exists.
compatibility: Requires the Agent Audio MCP server and an installed local runtime. Project integration also requires access to the project's editing tools.
---

# Audio Production

Use Agent Audio as the local generation tool, and finish the requested work
rather than leaving the user a separate audio-production task. The current
installation uses Stable Audio 3 Medium. Small-SFX is a separate benchmark
option, not a model selectable through this Skill's MCP workflow.

## Decide and inspect

Do not wait for an explicit audio request when an intended audible event is
missing from the requested deliverable. Appropriate cases include impacts,
collisions, movement, UI feedback, transitions and environmental ambience.
Music can be appropriate when the task calls for it; do not add a soundtrack
merely because a generation tool is available.

Before generating, inspect the project for suitable audio assets, existing
audio systems, timing, style and output conventions. Reuse suitable assets.
Do not generate for documentation, analysis, cleanup or refactoring; where
silence is intended; when sound would change rather than complete the user's
design; or when the user has asked for no audio.

## Autonomy and boundaries

Make routine decisions about sound, prompts, candidates and integration within
the requested task. Do not introduce a mandatory sound-plan approval or ask the
user to choose candidates before completing the work. Honor an explicit request
for review or alternatives, and never override the user's scope.

This does not authorize bypassing host permissions, accepting model terms,
accessing unrelated files, or paying for external services. If installation,
credentials or new permissions are required, report the blocker and obtain the
required authorization; do not silently install a different backend or use a
cloud provider. No routine creative checkpoint is needed after authorized setup.

## Prompt design

Use concrete acoustic descriptions: source/material, action, weight, texture,
space and timing. Match the existing sonic style rather than requesting generic
"epic" sound. For example, specify a dry, close metallic impact with a sharp
transient and a short decay. Include "no voice" or "no music" in the positive
prompt when appropriate.

The current tool rejects nonempty `negative_prompt`; put desired characteristics
and exclusions in `prompt`. See [prompt examples](references/prompting.md) when
useful. A request for a seamless loop does not establish that the generated
file actually loops cleanly.

## Generate within a bounded task

1. Call `audio_status` when runtime readiness is unknown. File readiness is not a
   successful generation test. Inspect the selected backend and reported limits.
2. Start with the shortest practical asset for the event. A roughly 3-second
   source is a useful starting point for a short effect, not a speed guarantee.
   The meaningful event may occupy only part of the generated file.
3. Call `generate_audio` with `prompt`, `seconds` and, when useful, a new `.wav`
   `output_path` in the intended project asset directory. Omitting the path uses
   Agent Audio's output folder; move/copy and integrate the asset when required.
   Never overwrite existing outputs or assume a failed call produced a new file.
4. Generate only the distinct assets the task needs. Reuse assets where
   appropriate; do not request large candidate batches by default. When another
   candidate is justified, change the acoustic direction deliberately. Stop
   repeated attempts on a persistent error and report the limitation.

The current interface is text-to-WAV. It does not expose audio editing,
inpainting, continuation, loop construction or mixing as MCP operations.
Use the project's existing tools for trimming, timing, fades or mixing when
available and authorized. Do not invent tool parameters or install new editing
software without the appropriate authorization. Long CPU requests can time out.

## Integrate and verify the deliverable

When the larger request requires integration, generating a file is not the end
of the task. Use the existing project tools and audio system:

- In games, connect the asset to the intended event and check triggering,
  repetition, restart behavior and the project's existing volume/mute controls.
- In videos, place the useful sound event at the intended timeline position,
  balance it against existing dialogue/music, and check the rendered result.

These are host-project tasks, not built-in Agent Audio engine/editor adapters.
Preserve unrelated behavior and assets. Match the useful transient or audible
event, not just the beginning or nominal duration of the generated file. Verify
loop boundaries when looping is required; do not infer a clean loop from a prompt.

Check file existence, actual duration, sample rate and channels. With available
tools, check silence, non-finite samples, peaks/clipping and the final mix. Such
checks do not prove prompt adherence or artistic quality. Use actual listening
or audio-analysis capabilities when available; never claim to have listened
when only metadata was inspected. Without that capability, state the quality
limit in the final report rather than inventing a listening assessment or
forcing an intermediate user selection.

If generation or integration is blocked, do not silently substitute a paid
service or procedural beep and present it as model-generated audio. Preserve
completed work and report the specific missing part. Do not claim the whole
sound workflow passed when only a WAV or a code reference was produced.

## Final report

Report the finished result, where the audio was integrated, important asset
paths, checks actually performed and remaining blockers or unverified quality.
Do not expose hardware details unless relevant to performance or troubleshooting.
Never claim CUDA, XPU or Apple acceleration unless the reported backend supports
that claim. Model-license acceptance always remains a user action.
