# motion-director

**A Claude Code skill that turns one line into a keynote-grade motion graphics film.**
Say *"make a launch video for this"* — it researches the product, writes a shot-by-shot treatment, builds the
film as deterministic code with real motion blur, composes the score and designs every sound from scratch,
can cast and word-sync a voiceover, reviews every frame, and hands you the MP4.

![The 12-second reference film, rendered by the skill's engine](assets/demo.gif)

*The reference film ("Lumen", a fictional product) — kinetic type on living light, a panel slide-over into a
real-feeling product UI, a chart that counts up, a typed question, a highlighted answer, a camera dive into the
hero bar, a circle wipe to night, a lockup. Real shutter motion blur, synthesized score and sound design.*
[Full-quality MP4](assets/demo.mp4) · [Frame sheet](assets/demo_sheet.png)

---

## Install

**macOS / Linux**
```bash
git clone https://github.com/Rohith2989/motion-director ~/.claude/skills/motion-director
```

**Windows (PowerShell)**
```powershell
git clone https://github.com/Rohith2989/motion-director "$env:USERPROFILE\.claude\skills\motion-director"
```

Only for one project? Clone it into `<your-repo>/.claude/skills/motion-director` instead.
Update later with `git pull` in that folder.

**Requirements:** Node 18+, Python 3.10+, git. The first film installs everything else into its own project
folder (headless Chrome for rendering, ffmpeg, fonts, brand icons — about 300 MB) and the Python packages in
`engine/requirements.txt`. Check a machine with `python scripts/doctor.py`.

**Optional keys** (environment variables, never files): `GEMINI_API_KEY` for voiceovers (Gemini 3.8 TTS,
300+ voices) and AI review; `OPENAI_API_KEY` or `ELEVEN_API_KEY` for alternative voices.

## Use

Just ask Claude Code — no brief, no long prompt:

```
Use motion-director to make a launch video for this app.
/motion-director onboarding video for our product, with a voiceover
Make a 15-second teaser of the new dashboard, vertical for Reels.
Motion graphics logo sting for our brand.
Cut the launch film down to 30 seconds.
```

It infers the subject (your repo, README, site copy, design tokens, logo — or a URL you mention), picks the
format and length, and decides everything else itself. It asks at most one question, and only if there is
literally nothing to make a film about.

## What you get

```
<project>/out/<Name>_v1.mp4           1080p60 (or 9:16 / 1:1 / 4:5), H.264 CRF 13, AAC 320k, −14 LUFS
<project>/out/<Name>_v1_preview.mp4   720p preview
<project>/out/<Name>_v1_cover.png     a designed cover frame
<project>/out/<Name>_v1.srt           captions (narrated films)
<project>/docs/PLAN.md                the treatment it followed
<project>/…                           the whole film as code + its score plan, to re-edit any section later
```

## How it works

| Phase | What happens |
|---|---|
| **Read the room** | Finds the subject and its own words, flows, colours, type and logo. Chooses film type, format, length, voice or not. |
| **Research** | Reads the product's copy and design system, walks its real user flow, studies premium films in the category. |
| **Treatment** | `docs/PLAN.md`: logline, sections on a musical bar grid, a shot list per section, motion language, sound plan, voice script. |
| **Build** | A deterministic HTML/JS film: the product's real UI rebuilt at real size, a camera that leans into the action, a cursor with intent, typing, panel slide-overs, circle wipes, card morphs, charts, highlights, living light, particles — section by section, stills checked before animating. |
| **Sound** | A score composed for this film (BPM chosen so sections start on bars; risers, impacts, a final chord under the lockup) and dry, tactile UI sounds caused by the picture — all synthesized from scratch. Mixed to −14 LUFS. |
| **Voice** *(narrated films)* | Auditions 20–50 TTS voices, casts by blind A/B duels heard in both orders, picks the best reading of every line, and keys every click and highlight to the spoken word. Captions for muted viewing. |
| **Review** | Contact sheets every second, strips through every transition, loudness/peak/click measurements, an AI watcher that must answer a proof question first. Fix, re-render, repeat. |
| **Deliver** | Full-quality render with true motion blur, frame-exact assembly, verified frame count and loudness. |

## Why the films look expensive

- **The product is the hero, shown literally** — its real UI, copy and flow, in clear sections. Innovation goes into craft, not into hiding the product behind a metaphor.
- **Every frame survives a pause** — composition, hierarchy and type hold at any frame.
- **Professional, never childish** — restrained easing, calm character acting, refined type, depth from light; no clip-art, no glassmorphism slabs, no "AI slop".
- **Film-grade picture** — everything is a pure function of time; real shutter motion blur averaged in linear light; 60 fps lossless masters.
- **Sound from scratch** — no stock music or sample packs; no bells on UI, no cartoon bloops, no noise whooshes.
- **Nothing ships unreviewed** — measured, strip-checked and critic-reviewed before you see it.

## Drive the engine yourself

```bash
python scripts/new_project.py my-film --format 16:9 --duration 45 --bpm 120 --title "Acme"   # --keep-demo for the reference film
cd my-film
node tools/render.js --stills 1,4,8 --dir renders/stills/a      # look before you animate
npm run serve                                                    # → http://127.0.0.1:5177/comp/index.html?debug  (scrub live)
node tools/probe.js 0 "window.getCues()" > audio/cues.json && python audio/score.py && python audio/mix.py
npm run preview && python tools/sheet.py --video renders/preview.mkv --every 1 renders/sheet.png
npm run render
python tools/assemble.py renders/master.mkv --audio audio/out/mix.wav --name Acme --v v1 --cover 3
```

```
SKILL.md                 the director's method (what Claude follows)
references/              craft · engine · sound · voice · review · formats · playbooks · plan template
engine/                  the project template
  comp/core/             runtime (scenes, cues, cuts, bar grid), easing, seeded noise, film finish
  comp/sys/              camera · cursor · typing · reveals · stages & transitions · living light · particles
                         charts · highlights & spotlight · windows · card morph · captions · voice clock · logos
  comp/scenes/           the 12 s reference film
  tools/                 render.js (headless Chrome + shutter blur) · assemble.py · sheet.py · strip.py · probe.js
  audio/                 synth.py (from-scratch DSP) · inst.py · sfx.py · score.py · mix.py · analyze.py
  voice/                 tts.py (Gemini / OpenAI / ElevenLabs) · cast.py (duels) · align.py · vo_build.py
  review/                watch.py · listen.py (AI critics with proof questions)
scripts/                 new_project.py · doctor.py
```

## FAQ

**How long does a film take?** Planning and building take the bulk; rendering runs at about 0.2–0.4 s per
frame with motion blur on 4 workers (a 60 s film at 60 fps ≈ 15–25 min), previews ~10× faster.

**Does it cost anything?** No. Only optional TTS/AI-review API calls cost what the provider charges.

**Can it use my brand?** That's the default: it reads your tokens, fonts and logo from your code. Or put them
in `comp/css/theme.css`.

**Vertical?** `--format 9:16` (also 1:1, 4:5) with platform safe zones; vertical cuts are re-laid, not cropped.

**Why code instead of After Effects?** Agents can write, diff and re-render code; every frame is exactly
reproducible; motion blur, sound cues and the voice clock come from the same source of truth.

## Credits and licences

Code: MIT. Fonts load from npm (Bricolage Grotesque, Geist — SIL Open Font License). Brand icons from
[simple-icons](https://simpleicons.org) (CC0 data; the marks are their owners' trademarks — show only tools a
product really supports). All music and sound effects are synthesized; no samples are bundled.
