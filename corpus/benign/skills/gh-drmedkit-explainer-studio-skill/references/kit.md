# The kit: layout, commands, interfaces

Kit: the folder you cloned this repo to (`npm install` once; puppeteer resolves from the kit). Every
command takes the topic folder as its first argument (relative or absolute). Topic files import kit modules by relative
path (`topic.config.json` → `kit`), which the scaffolder fills in.

## Commands

| command | what it does |
|---|---|
| `node new-topic.mjs <slug> --archetype <a> [--title --dir --api --port --subject --ids --no-git --no-build --force]` | scaffold a running topic (see SKILL.md step 2) |
| `node audio.mjs <topic> narrate [--dry \| --placeholder]` | narration via ElevenLabs and the voice cache → `narration.wav`, `words.json` (cues, word timing) |
| `node audio.mjs <topic> sfx [--dry] [names]` / `music --list \| --from-lib <bed> \| A B \| --keep B --as <name>` / `mix` | sound effects, music beds, the mix |
| `node render.mjs <topic> --sheet 3,12,25` / `--still 62` | contact frames / one PNG → `video/out/` |
| `node render.mjs <topic> --textcheck all\|t1,t2` | text check over the film → `video/out/textcheck.json` |
| `node render.mjs <topic> [--workers 3] [--fps 30] [--ranges a-b,c-d \| --from s --to s] [--poster s] [--crf720 29] [--theme dark]` | render frames, mix, encode `<name>-1080p.mp4`, `<name>.mp4` (720p), `poster.jpg` |
| `node render.mjs <topic> --audio-only` / `--encode-only` | audio pass + mix only / mix + encode the frames on disk |
| `node gate.mjs <topic> [--quick] [--skip-film]` | all quality gates, table + `out/gate.json` |
| `node ship.mjs <topic> [--deploy]` | page (`out/page/index.html` artifact, `preview.html` local) + site (`out/site`) + `wrangler.jsonc`; `--deploy` runs `npx wrangler deploy` |
| `node checks/pagecheck.mjs <topic> [--widths 390,1400] [--dark]`, `node checks/readouts.mjs <topic>`, `node checks/contrast.mjs <film.mp4>` | single checks |

## The ElevenLabs key

`audio/el.py` looks for `ELEVENLABS_API_KEY` in the topic's `video/.env`, the topic's `.env`, then the kit's own
`<kit>/.env` (gitignored). The kit's file serves every topic, so a new topic needs no copy of the key.

## Layout

```
lib/        topic.mjs (config + paths), bundle.mjs (strip imports/exports and `// @cli` tails), chrome.mjs (muted Chrome,
            static server), ffmpeg.mjs (encode settings), scene.mjs (build/open the film scene), page.mjs (page + site)
film/       scene.template.html (full-bleed 16:9 shell + overlays), scene-runtime.js (drives figure + overlays per frame,
            records sounds), timeline-kit.mjs (span, logspan, pw, pwRate, wordAt, cueOf, slowLabel, subtitleAt)
page/       page.template.html (Watch / Explain / Open lab shell, light + dark tokens), page-runtime.js (tabs, chapters,
            captions, explainer engine, lab, challenges, theme sync)
figure/     stage.js (XStage/XFigure: view, focus fog, frame, manual clock), build-helpers.mjs (anatomy imports,
            scopeCss, focusCss, materialCss, stageScript, writeFigure)
audio/      el.py, narrate.py (+ --placeholder), gen_sfx.py, gen_music.py, mix.py (event-placed sfx, loops, ducked bed)
checks/     textcheck.js, pagecheck.mjs, readouts.mjs + numbers.mjs, contrast.mjs
templates/  common/ + one folder per archetype (model, figure subject)
skill/      this skill (link it to ~/.claude/skills/explainer-studio)
```

## topic.config.json

```json
{ "slug": "second-law", "title": "The Second Law", "titleHtml": "The second <em>law</em>", "archetype": "micro",
  "eyebrow": "Physics · Thermal", "lede": "...", "description": "...", "footer": "the model in one paragraph",
  "worker": "second-law-lab", "port": 5281, "colors": { "accent": "#1d4ed8", "accentDark": "#7aa2ff", "icon": "#7aa2ff" },
  "figure": { "api": "cabinet", "id": "second-law-figure", "name": "second-law", "audit": "node figure/build.mjs --audit" },
  "model": { "file": "src/model.mjs", "check": "node src/model.mjs" },
  "bundle": ["src/model.mjs", "src/widgets.mjs", "src/content.mjs", "src/app.mjs"], "instruments": ".xw svg",
  "film": { "workers": 3, "fps": 30, "poster": 128, "chapters": [["Ways", "ways"]], "units": ["quanta"],
            "end": { "eyebrow": "Your turn", "html": "...", "mid": "..." } },
  "page": { "challengesLabel": "3 challenges", "labPoses": { "big-N": "document.querySelector('#k-N').value=..." } },
  "gates": { "readouts": "fail" }, "curriculum": { "subject": "physics", "ids": ["physics.thermal.entropy"] }, "kit": "../explainer-studio" }
```
`film.bundle` (optional) overrides which src files go into the film (default: `bundle` without `app.mjs`).
`iconSvg`, `ogTitle`, `page.figLabel`, `page.watchNote`, `page.steps` are optional.

## Topic interfaces

- **Model** (`src/model.mjs`): `QUANTITY { key, label, unit, digits, max, timeUnit? }`, `DEFAULTS`, `KNOBS [{ key, label,
  min, max, step, unit, digits }]`, `simulate(s) → run { T, loop, series, summary { headline { t, y, words }, lines } }`,
  `stateAt(run, t) → { t, y, ... }`, `selfCheck() → [{ name, ok, detail }]`, CLI after `// @cli`. Avoid top-level names
  the anatomy kit defines (`iso`, `ring`, `corners`, `UNIT`, `segment`, ...): the model is inlined into the figure.
- **Content** (`src/content.mjs`): `STEPS`, `CHALLENGES [{ id, title, text, done(st) }]`.
- **Page glue** (`src/app.mjs`): `APP { defaults, instruments, labInstruments, apply?, state?, initLab?, refreshLab?,
  challengeDone?, status? }` (header of `page/page-runtime.js`). Lab controls in `src/lab.html` (ranges and buttons in
  `#labPanel` are swept by the page gate).
- **Widgets** (`src/widgets.mjs`): `WIDGET_CSS` + instrument factories; roots carry class `xw`.
- **Timeline** (`video/timeline.mjs`): `buildTimeline(words, ctx) → { at(t), once?, duration }` (header of
  `film/timeline-kit.mjs`).
- **Film hooks** (`video/scene.mjs`): `filmHooks() → { css, context, panes, apply, frame, state, readout, sfx, loops,
  once }` (header of `film/scene-runtime.js`).
- **Narration** (`video/assets/data/narration.json`): `voices`, `lead_in`, `default_gap`, `tail`, `lines [{ section,
  text with {cue} markers, gap, at?, speaker?, readouts? }]`.
- **Mix** (`video/assets/data/mix.json`): `levels`, `min_gap`, `repeat_gain`, `loops`, `bed` (header of `audio/mix.py`).
