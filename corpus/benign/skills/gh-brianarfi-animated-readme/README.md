# animated-readme

**Turn your README into a demo people watch.**

A Claude Code skill. Claude reads your project, writes README copy a visitor gets in ten seconds, and renders animated GIFs that show what it does. Same input, same GIF, every time. Nothing is pushed until you approve it.

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Version 0.1.0](https://img.shields.io/badge/version-0.1.0-green.svg)](CHANGELOG.md)
[![Made for Claude Code](https://img.shields.io/badge/made%20for-Claude%20Code-orange.svg)](#quick-start)

![Animated. On the left, the headline "Turn your README into a demo people watch". On the right, a Claude Code terminal types "Make an animated README for this repo.", then reads the project, writes the copy, fills three scenes and renders hero.gif. A card lands: README ready for review, with a headline and a Sound familiar section, three GIFs that each have alt text, and two claims flagged because the repo has no source for them. Last line: nothing is pushed until you approve it.](docs/hero.gif)

## Sound familiar?

- The first screen of your README is install steps. A visitor still doesn't know what the project does.
- Not one image shows it working, or the one screen recording you have is three versions old.
- Re-recording the demo means setting everything up again and clicking through it by hand.
- The tagline reads "a composable, extensible framework for..." and means nothing to the person you built it for.
- Screen readers get "demo.gif" and nothing else.

## Who it is for

**A good fit if you** maintain a project on GitHub, use Claude Code, and want a README that shows the thing working, without opening a video editor.

**Not for you if** you need a real screen recording of your app with live data. This renders animated illustrations from HTML. For a real recording, script your app with Playwright and keep the same `record_html.py` approach for the frames.

## Before and after

![Animated before and after. Before: six cards pile up. The first screen is install steps and nobody knows what the project does. Not one image shows it working. The tagline is jargon. The only screen recording is three versions old. Screen readers get demo.gif and nothing else. Re-recording means doing it all again by hand. A green wipe turns the label to After: a terminal runs "Make an animated README for this repo." and five outcomes appear: it opens with the problem users have, three GIFs rendered from HTML, alt text on every GIF, copy that lives in readme-scenes.json and re-renders in one command, and the same input always giving the same GIF.](docs/before-after.gif)

## How it works

![Animated diagram of four steps, left to right. 1, read the project: README.md, docs and code, who it is for and what it does, what is true today. 2, write the copy: problem first in plain words, before and after, every claim taken from the repo. 3, fill the scenes: readme-scenes.json, the hero, before-after and how-it-works templates, your colours through theme. 4, highlighted, render: python scripts/render.py, a GIF plus a still PNG, a size check and alt text. Below, a loop line: copy changed? Edit readme-scenes.json and render again, and the GIFs follow.](docs/how-it-works.gif)

1. **It reads your project first.** README, docs, code, changelog. Every claim in the new copy has to point at something in the repo.
2. **It writes the copy** to a short [writing guide](docs/writing-guide.md): problem first, plain words, no hype words, no em-dashes.
3. **It fills three scene templates** (hero, before and after, how it works) through one file, `readme-scenes.json`. The copy lives there, not in the HTML.
4. **It renders the GIFs** frame by frame: every animation is paused and seeked to each frame, then screenshotted. No screen recording, so the same input always gives the same GIF. It warns when a GIF goes over 4 MB, and writes the alt text next to each image line.

You review the README and the GIFs. Nothing is committed or pushed until you say so.

## Examples

Each has a hero, a before and after, and a how it works GIF, plus real recordings of the tool working.

| README | What it shows |
| :--- | :--- |
| [AI Second Brain](https://github.com/BrianArfi/ai-second-brain#readme) | A PM's Friday before and after, plus a real dashboard and inbox recording |
| [AI Prototype Kit](https://github.com/BrianArfi/ai-prototype-kit#readme) | Comments pinned on a prototype, and the revise-from-comments loop |
| [id-voice-gate](https://github.com/BrianArfi/id-voice-gate#readme) | Indonesian AI text that reads like a translation, caught and rewritten |
| [artifact-comments](https://github.com/BrianArfi/artifact-comments#readme) | Figma-style comments on any HTML page, and the owner tools |

## Quick start

See it render this README's own GIFs. You need Python 3.9+ and no account.

```bash
git clone https://github.com/BrianArfi/animated-readme
cd animated-readme
pip install playwright pillow && python -m playwright install chromium
python scripts/render.py
```

The GIFs land in `docs/`. ffmpeg on your PATH gives smaller, sharper GIFs; without it, Pillow builds them.

### Use it on your own project

```bash
cd your-project
mkdir -p .claude/skills .claude/commands
cp -r /path/to/animated-readme .claude/skills/animated-readme
cp .claude/skills/animated-readme/commands/animated-readme.md .claude/commands/
```

Then, in Claude Code:

> Make an animated README for this repo.

Or run `/animated-readme`. Changed the copy later? `/animated-readme render` re-renders the GIFs from `readme-scenes.json`.

## What you get

| File | What it is |
| :--- | :--- |
| `readme-scenes.json` | Your copy and colours for every scene, plus the alt text |
| `docs/*.gif` | The animated scenes, looping |
| `docs/hero.png` | A still of the hero, for places that do not play GIFs |
| `readme-snippets.md` | The markdown image line for each GIF, alt text included |

## Documentation

- [SKILL.md](SKILL.md): the steps and rules Claude follows.
- [Writing guide](docs/writing-guide.md): the README order, the voice, the words to cut, and how to write alt text.
- `python scripts/render.py --help` and `python scripts/record_html.py --help`: every option.

## Licence

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE). Made by [Brian Arfi](https://brianarfi.com/skills).
