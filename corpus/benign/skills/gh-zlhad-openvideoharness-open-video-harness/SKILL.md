---
name: open-video-harness
description: Make videos with code (video-as-code / code2video) through the OpenVideoHarness workbench. Covers 3Blue1Brown-style math and science explainers, knowledge shorts (vertical or horizontal; 抖音, B站, 小红书, Shorts), product launch films and promos, lyric videos and music videos, data stories, paper explainers, hand-drawn or watercolour shorts, meme or fast-cut edits, and cutting the user's own footage (talking heads, interviews, vlogs; 剪口播). Also covers voiceover (Chinese or English), bilingual captions, code-composed music, sound effects, and reverse-engineering a reference video. Use it whenever the user asks to make, animate, render, remake or cut a video, 做视频, 做动画, 做科普视频, 做宣传片, 做 MV, 讲解视频, 片头, 剪用户自己录的素材, or 剪口播, even if they don't name the harness.
---

# OpenVideoHarness

Harness path (set by install.sh): ~/OpenVideoHarness

This skill is a thin pointer. All workflows, rules and tools live in the OpenVideoHarness repository.

## 1. Locate the harness

Use the first of these that exists and contains `bin/vh`:

1. `$OVH_DIR`
2. the path on the "Harness path" line above
3. `~/OpenVideoHarness`
4. the current working directory

If none exists, ask the user for permission, then install it:

```bash
curl -fsSL https://raw.githubusercontent.com/ZLHad/OpenVideoHarness/main/install.sh | bash
```

## 2. Follow the harness, not this file

Read `<harness>/CLAUDE.md` (Codex: `<harness>/AGENTS.md`, which is identical) and follow it exactly:

- route the request to one of the 9 `video-types/` docs (09, editing the user's own footage, is experimental);
- create the project with `<harness>/bin/vh new <type> <slug>`;
- stop for the user where effort and director mode say (CLAUDE.md "努力程度" and "导演模式"): `standard` and `studio` stop at the **three human review gates** (concept and outline → storyboard → first draft); `quick` renders straight through. Anything the user said they want to decide themselves (hook, main character, theme music, title and cover …) adds a stop before anything downstream needs it, or rides on the next gate if it can wait. Each stop is by default one local review page from `bin/vh review`, at most three decisions; send the user only the lines it prints, then wait;
- follow the hard rules: every frame is a pure function of t; when there is sound, audio sets the timing; storyboard before code; self-review every scene; fact discipline;
- keep work inside `<harness>/projects/`; when the user names another directory, create the project there with `<harness>/bin/vh new <type> <slug> --dir <that directory>` (or set `OVH_PROJECTS`).

Audio tools:
- `bin/vh tts` — voiceover, Chinese or English, local Qwen3-TTS by default;
- `bin/vh captions` — zh/en/bilingual subtitles;
- `bin/vh music` — code-composed soundtrack;
- `bin/vh sfx` — sound effects;
- `bin/vh mix` and `bin/vh mux` — mixing and muxing.

Run `bin/vh doctor` if anything looks missing.
