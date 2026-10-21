# Prompt templates

This page is for people writing prompts. The skill itself does not need it. These patterns are distilled from public prompts people used with Claude (Opus 5.5 in particular, released 2026-09-22) and Claude Code to make code-rendered videos. Each source link below was opened and checked on 2026-09-27. "via compendium" means the text was taken from the curated list [joeseesun/opus-video-prompts](https://github.com/joeseesun/opus-video-prompts), which links to the original post.

## What the best prompts have in common

| Pattern | Seen in | video-gaga equivalent |
|---|---|---|
| **Direct, don't describe.** State the length, scene count, what each scene says, and the pace | Alex Prompter's 30-s explainer | the discovery questions + the storyboard |
| **Storyboard before code**, then revise per shot | Danny Stuart, om_patel5, zero | storyboard approval before building |
| **Ban list** (no bouncy easing, particle bursts, RGB split, lens flares, neon glow, dead time) | zero (@twoclipping) | `docs/craft.md` (*Not good* lists) |
| **Deterministic `seek(t)`**: no CSS transitions, no timers, no state between frames | zero, PDoomVideo guide (via compendium) | the runtime contract: `draw(ctx, s)` is pure |
| **Closed-form springs**, a sum of springs for re-targeted values | zero | `CV.spring`, `CV.springTrack` |
| **Sub-frame motion blur** (render sub-frames, blend with `tmix`) | zero | `gaga render --motion-blur 5` |
| **Probe frames before the full render** and fix clutter or overlaps | zero, compendium tips | `gaga still --sheet` + `docs/motion-design.md` §9 |
| **Beat grid**: every cut on a downbeat, every hit on a beat | zero | `s.when('word')` (narration) or `beat(n)` (BPM) |
| **One-liners work, but vary a lot.** "Go all out" showreels | Leon Abboud, Deedy, Stephan Livera | the questions fill in what the one-liner leaves out |
| **TTS + bilingual captions + export in one go** | WY (@akokoi1) | Edge TTS + cue builder + `gaga render` |
| **Use real assets.** Give the model a gallery of files and paths | om_patel5 | `CV.image()`, and brand assets in the project folder |

## Sources

| # | Author | What | Link |
|---|---|---|---|
| 1 | Rory Flynn (@Ror_Fly) | Negroni recipe explainer from one reference image, 30 s, HTML/JS (2026-09-23) | https://x.com/Ror_Fly/status/2102853258582880547 |
| 2 | Alex Prompter (@alex_prompter) | "Adopt the role of an expert motion designer…" 30-s, 5-scene business explainer template (2026-09-25) | https://x.com/alex_prompter/status/2103499977632997524 |
| 3 | Leon Abboud (@leonabboud) | One-sentence 15-s "motion designer showreel… go all out" (2026-09-25) | https://x.com/leonabboud/status/2103576084499358051 |
| 4 | Deedy (@deedydas) | "make a modern slick and punchy video for a modern startup that works on inference" (2026-09-23) | https://x.com/deedydas/status/2102787937482252537 |
| 5 | zero (@twoclipping) | Open-sourced XML-structured motion-design template (inputs, direction, ban list, structure, build, gotchas) (2026-09-25) | https://x.com/twoclipping/status/2103273003555402193 |
| 6 | WY (@akokoi1) | Chinese high-school geography explainer, line-art style, TTS narration + bilingual captions, ~5 min (2026-09-23) | https://x.com/akokoi1/status/2102606609574941028 |
| 7 | Chubby (@kimmonismus) | 3-min "history of AI" film, 100% code (Remotion + SVG/Canvas, open-source TTS, Python-synthesised score) (2026-09-23) | https://x.com/kimmonismus/status/2102844654169575547 |
| 8 | klöss (@kloss_xyz) | 90-s motion design + sound engineering demo with a model-composed piano score (2026-09-25) | https://x.com/kloss_xyz/status/2103557735086428547 |
| 9 | Om Patel (@om_patel5) | Remotion + Claude Code playbook: asset gallery, storyboard in plan mode, prompt set (2026-01-28) | https://x.com/om_patel5/status/2016364061617766905 |
| 10 | Ole Lehmann (@itsolelehmann) | Article: "How to create viral animated videos with Claude Code" (2026-01-23) | https://x.com/itsolelehmann/status/2014740993208188959 |
| 11 | Francesco (@francedot) | Article: "How We Built Our OSS Launch Video with Remotion + Claude Code" (2026-01-23) | https://x.com/francedot/status/2014536250037043459 |
| 12 | Danny Stuart | App promo videos with Claude Code + Opus + Remotion. "Storyboard the video and plan carefully before coding anything." (via compendium) | https://dannystuart.substack.com/p/claude-code-opus-remotion-agentic-promo-video |
| 13 | joeseesun | Compendium of 18 full prompts and 54 cases from Opus 5.5's first week | https://github.com/joeseesun/opus-video-prompts |
| 14 | HeyGen | HyperFrames: HTML → video framework with agent skills (a comparable approach) | https://github.com/heygen-com/hyperframes |

Prompt copyright belongs to the original authors. The templates below are our own syntheses of the patterns.

---

## Template A — Product launch teaser (16:9, 15–25 s)

```text
Use the video-gaga skill.
Make a {15–20}-second launch teaser for {PRODUCT}: {ONE-LINE PROMISE}.
Audience: {WHO}. Tone: confident, premium, calm — Apple-keynote restraint.
Structure (one idea per scene):
  1. Hook — a question or tension in ≤ 8 words.
  2. Reveal — the product/hero object appears; camera arrive-push; name lands on the spoken word.
  3. Proof — 3 numbers ({STAT1}, {STAT2}, {STAT3}); each counts up exactly when it is said.
  4. End card — name + tagline + {DATE/CTA}; hold 1 s.
Narration: English, en-US-AndrewNeural, rate -4%. Burn captions (boxed, small).
Style: Launch Keynote preset, accent {BRAND HEX}. One accent only.
Banned: bouncy easing, particle bursts, lens flares, crossfades between every scene.
Storyboard first (table: scene / voice line or music-only / visual / motion / exit / transition / music · sfx), then build, probe, render.
```

## Template B — Knowledge explainer / infographic (16:9, 20–60 s, ZH)

```text
用 video-gaga 做一个 {时长} 秒的知识讲解视频，主题：{主题}。
观众：{谁}，看完要记住一句话：{核心结论}。
结构：问题钩子 → 概念/公式（逐项出现，和旁白同步）→ 数据图表（坐标轴先画，曲线按时间方向画，关键点落在读到它的那个词上）→ 结论。
旁白：zh-CN-YunxiNeural，语速 +6%，每个场景一句话；字幕烧录，中文每行 ≤ 18 字，去掉句末标点。
风格：Clear Explainer（暖纸底 + 墨色字 + 珊瑚红强调“要点”+ 青绿色表示“证据”），顶部章节进度条。
数据必须准确，给出计算口径脚注。先给我分镜表确认，再写代码。
```

## Template C — Kinetic typography (1:1 or 9:16, 8–15 s, no voice)

```text
Use video-gaga. A {10}-second kinetic typography piece of the line: "{QUOTE}" — {AUTHOR}.
Swiss / International Typographic Style: 12-column grid, one red, Archivo, hard cuts on a {100} BPM beat grid,
masked reveals, tracking that closes in on the key word, a match cut (a shape becomes punctuation).
No fades, no glow, no bounce. End on a resolved still, held 1 s. Square 1080×1080. Add motion blur (5 sub-frames).
```

## Template D — Social vertical short (9:16, 12–20 s, ZH/EN)

```text
用 video-gaga 做一个 9:16 竖屏短视频，{时长} 秒，主题：{活动/产品}。
第一秒就要有钩子（大号数字或反常识的一句话）。节奏快：每 1–2 秒一个“命中”，命中时才用故障/RGB 分离，6 帧内衰减。
旁白 zh-CN-YunjianNeural（有冲劲），卡拉 OK 高亮字幕，字幕在画面 78–80% 高度，避开平台 UI 区域。
风格：Neon Circuit（品红=能量，青色=信息，扫描线 + HUD 角标），结尾霓虹灯牌亮起 + 日期/行动号召。
```

## Template E — Hand-drawn explainer (16:9, 15–40 s)

```text
用 video-gaga 做一段手绘风讲解：{主题}。
纸张质感背景，线条按“手会怎么画”的方向逐笔画出，并以每 3 帧抖动一次（boiling lines）营造手绘动画感；
只用铅笔黑 + 一支荧光笔 + 1–2 个水彩色块；每一页像纸片一样滑入。
旁白 zh-CN-XiaoxiaoNeural，温暖、慢一点；每个图形在旁白说到它时画出来。先出分镜。
```

## Template F — Pro spec (for power users; zero-style XML)

```xml
<inputs>Ask me for: {what you need from the user — brand color, 3–5 key messages, logo file, voice}.</inputs>
<direction>{style in 3 sentences}. Banned: {ban list}.</direction>
<structure>{duration}, {beat grid or narration}, scene-by-scene beats.</structure>
<build>
1. One HTML file using runtime/video-gaga.js; every pixel is a pure function of t inside draw(ctx, s).
2. Narration in narration.json (Edge TTS, WordBoundary); pin hits with s.when('word').
3. Probe with `gaga still --sheet` before rendering; fix overlaps, clutter, unreadable text.
4. Render with `gaga render --subs burn --motion-blur 5`; verify with `gaga check`.
</build>
<gotchas>Hold every info beat ≥ 1 s. Captions never collide with content. Last frame is a still.</gotchas>
<start>Ask me for the inputs, then show me the storyboard with every timing before writing code.</start>
```

---

## The brief

The skill writes its own brief before building; the template and what goes into it are in [craft.md](craft.md), *The brief*.
