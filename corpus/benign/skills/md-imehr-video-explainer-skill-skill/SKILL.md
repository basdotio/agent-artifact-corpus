---
name: video-explainer
description: Use when creating explainer videos, video content for YouTube/TikTok/Instagram/LinkedIn, or when user mentions /video command. Creates multi-platform explainer videos with intelligent orchestration, learning memory, and brand management.
---

# Video Explainer Skill

Create professional explainer videos across multiple platforms with consistent branding and intelligent automation.

## Commands

### Setup & Configuration

**`/video setup`** - Configure video_explainer path and initial settings
- Prompts for video_explainer installation path
- Validates the tool is accessible
- Creates initial config.yaml

**`/video brands`** - List available brands
**`/video brands create`** - Interactive brand creation wizard
**`/video platforms`** - List available platform profiles
**`/video styles`** - List available style overlays
**`/video config [project]`** - Show/edit configuration

### Project Management

**`/video new [name]`** - Create new video project
- Without name: Interactive wizard (asks brand, platforms, style, languages)
- With `--quick`: Skip wizard, use defaults
- Creates project directory with config.json

**`/video list`** - List all video projects
**`/video status [project]`** - Show project progress, outputs, versions

### Pipeline Control

**`/video script [project]`** - Generate script from source document
- Runs in foreground (user review expected)
- Applies brand voice, platform pacing
- Uses storytelling techniques from learned skills

**`/video scenes [project]`** - Generate scenes from script
- Orchestrator decides parallel execution per aspect ratio
- Applies brand visual system

**`/video render [project]`** - Render all outputs
- `--only main,tiktok` - Specific outputs only
- `--lang en` - Specific language only
- `--version v3` - Specific version number
- Orchestrator runs renders in parallel background

### Iteration & Feedback

**`/video feedback [project] "message"`** - Apply feedback and re-render
- Creates new version automatically
- Captures feedback for learning

**`/video compare [project] [output] [v1] [v2]`** - Side-by-side version review
**`/video promote [project] [output] [version]`** - Promote version to final

### Learning & Skills

**`/video learn "instruction"`** - Teach a new preference or technique
- `--from-url URL` - Learn from web content
- `--from-file path` - Learn from local file

**`/video memory`** - Show learning summary
- `--patterns` - Discovered patterns
- `--preferences` - Inferred preferences
- `--effectiveness` - Technique scores

**`/video forget "technique"`** - Remove a learned technique
**`/video prefer "preference" --always`** - Set strong preference

**`/video skills`** - List loaded technique skills
**`/video skills sync`** - Pull updates from skill sources

### Export

**`/video export [project] --zip`** - Package final outputs for delivery

## Orchestrator Behavior

The intelligent orchestrator analyzes each task and decides:

1. **Foreground vs Background** - User-interactive steps (script review) run foreground; heavy processing runs background
2. **Parallel vs Sequential** - Independent tasks (different aspect ratios, languages) run in parallel
3. **Dependencies** - Tracks what each step needs and schedules accordingly

**Example execution plan:**
```
/video render my-project (YouTube + TikTok, en/es)

1. [FOREGROUND] Script generation (user may review)
2. [BACKGROUND PARALLEL]
   - Scene generation (16:9)
   - Scene generation (9:16)
   - Voiceover (en)
   - Voiceover (es)
3. [BACKGROUND PARALLEL] (when dependencies ready)
   - Render YouTube-en
   - Render YouTube-es
   - Render TikTok-en
   - Render TikTok-es
```

## Quality Gates

Every output passes through validation:

- **Concept coverage**: Key concepts from source appear in script
- **Audio sync**: Voiceover duration matches scenes, no awkward pauses
- **Narrative flow**: Hook present, transitions smooth, CTA at end
- **Fact check**: Claims supported by source material

## Configuration Matrix

Three independent axes combine:

```
Output = Brand × Platform × Style
```

- **Brand**: Voice, colors, typography, assets (comprehensive design system)
- **Platform**: Aspect ratio, duration limits, pacing, safe zones
- **Style**: Mood overlay (energetic, minimal, corporate)

## File Locations

```
~/.config/video-explainer/
├── config.yaml           # Global settings
├── brands/               # Brand definitions
├── platforms/            # Platform profiles
├── styles/               # Style overlays
├── skills/               # Technique definitions
└── memory/               # Learning data
```

## Sub-Skills

This skill automatically loads technique modules:

- `techniques/hooks.md` - Opening techniques for engagement
- `techniques/narrative.md` - Story structure patterns
- `techniques/platform-optimization.md` - Platform-specific tips

## Integration with video_explainer CLI

This skill wraps the video_explainer Python CLI tool:

```bash
# Under the hood, commands map to CLI calls:
/video script → video_explainer script
/video scenes → video_explainer scenes
/video render → video_explainer render
```

The orchestrator handles config translation, parallel execution, and output management.
