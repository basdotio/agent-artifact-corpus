# Visuals: diagrams, pages, and explainers

Use a visual when a reader understands a point faster by seeing it than by reading it.
Use only free tools that are already installed. Do not add paid tools or subscriptions.

## When a visual helps

- A flow across 3 or more parts (services, steps, or people)
- A state machine or lifecycle
- A comparison of 3 or more options
- Architecture or data-model changes
- A review of a large proposal

## Which form to use

| Form | Where | How | Who decides |
| --- | --- | --- | --- |
| Diagram | Docs, specs, issues, PRs | Mermaid in a fenced `mermaid` block. GitHub renders it. | The agent adds it. No need to ask. |
| Diagram | Terminal chat | A small ASCII sketch. If it is too large, use a page. | The agent adds it. No need to ask. |
| Web page | A private hosted page (for example a claude.ai Artifact) | One HTML page. It must work in light mode, dark mode, and at phone width. | The agent offers it in one line first. |
| Explainer | A private hosted page, and its source in the repo's docs folder | An animated page with step-through scenes, SVG, and optional browser narration (Web Speech API). | The agent offers it in one line first. |
| Explainer video | An MP4 file | Only on request. See the recipe below. | The user asks for it. |

## Diagram rules

- Show one idea in each diagram. Use 12 nodes or fewer.
- Use the terms in the [dictionary](ste.md#dictionary) for labels.
- Write a one-sentence caption that gives the main point.

## MP4 recipe (on request only)

This recipe uses Playwright, macOS `say`, and ffmpeg. If one of them is not installed, tell the
user. Do not install a paid tool.

1. Open the explainer page in auto-play mode, and record it with Playwright `recordVideo`.
2. Write the narration of each scene to an audio file with `say -o`.
3. Merge the video and the audio into one MP4 with ffmpeg.

At the first request in a repo, put these steps in `scripts/explainer-to-mp4.sh`.
