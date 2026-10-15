---
name: motion-video
description: Make playful, polished motion-graphics videos (explainers on any topic, product promos, teasers, announcements, tutorials, social clips for TikTok/Reels/Shorts or 16:9) from a single story.json. Kinetic typography and drawn UI cards (quizzes, timelines, charts, rankings, myth/fact flips, definitions, profiles, quotes, feature cards, stats, checklists), voices synced word by word from any text-to-speech tool (such as an ElevenLabs account connected through Composio), 8 synthesized music styles and 43 sound effects, rendered frame-exact to MP4. Use when someone asks for an animated video, a motion graphic, a short vertical video, or a narrated explainer.
---

# Motion video

You write a `story.json`: the scenes, the words, the look. The engine turns it
into a timeline, draws every frame, synthesizes music and sound effects on the
same cues, mixes in the voices and encodes an MP4. A frame is a pure function
of its time, so a still is exactly the frame that ships.

```
engine/make.mjs      every command below
docs/story-schema.md every story.json field: read it before writing one
docs/sounds.md       the 8 music styles and 43 sound effects
docs/voices.md       real ElevenLabs voice ids (English and French) and models
examples/            app-launch (EN, 9:16), astuces-ia (FR, 9:16), feature-launch (16:9, no voice),
                     coffee-explainer (EN, 9:16, any-topic explainer): all drawn UI cards
```

## Get the engine

Work from a clone of this repository. Clone it only when it is not there yet,
otherwise update it, then check the machine:

```bash
E=~/motion-video-skill
if [ -d "$E/.git" ]; then git -C "$E" pull -q --ff-only || true; else git clone -q --depth 1 https://github.com/Clad012/motion-video-skill.git "$E"; fi
[ -e "$E/node_modules" ] || (cd "$E" && npm ci --omit=dev --silent)
node "$E/engine/make.mjs" doctor
```

`npm ci` only fetches the engine's one Node package (it downloads no browser:
the engine uses the Chrome, Chromium or Edge already installed). If your
environment ships the engine's `node_modules` elsewhere, link it instead.

## Commands

Run them from anywhere; `$E` is the clone (write its full path when your
shell does not keep variables between commands).

| Command | What it does |
|---|---|
| `node $E/engine/make.mjs doctor` | Checks that everything the engine needs is there. |
| `node $E/engine/make.mjs <project> voices` | Times the voice files in `<project>/voices/`. |
| `node $E/engine/make.mjs <project> stills [t…]` | Prints the timeline, NOTES (fixed automatically) and PROBLEMS (block the render); saves stills and `build/contact-sheet.jpg`. |
| `node $E/engine/make.mjs <project> all --fps 30` | Renders the MP4 to `<project>/out/`. Refuses while PROBLEMS remain or a voice is buried under the music. |
| `node $E/engine/make.mjs <project> check` | Transcribes each voice line where it plays in the final mix: OK, or CHECK with what was heard. |

If `doctor` reports something missing, tell the user what (it prints the fix);
don't install system software yourself.

## Workflow

### 1. Brief
Find out what the video is for, who watches, where it goes (format: 1080×1920
for TikTok/Reels/Shorts, 1920×1080 for YouTube or slides, 1080×1080 for feeds),
the language, the length (15 to 45 s), the call to action, the brand (colours,
font, logo) and what media exists. Ask only what you cannot default.

### 2. Script as beats
One idea per scene, one short spoken line per scene:

| Beat | Scene type | Job |
|---|---|---|
| Hook: the problem | `pileup`, `chat` or `title` | Make the pain visible in 3 to 6 s. |
| Turn | `title` or `fan` | Relief, the reveal. |
| Proof, one by one | `cards`, `prompt`, or `card` × 3 to 7 | Each feature, tip or person, one at a time. |
| Results | `stats`, `compare`, `checklist` | Numbers, before/after, what gets done. |
| How it works | `list` | 3 to 5 steps or tips. |
| All together | `grid` | The whole range. |
| Ending | `logo` | Name, tagline, URL. |

Explainers on any topic (history, science, money, health, a place, a person)
use these beats instead:

| Beat | Scene type | Job |
|---|---|---|
| Hook: a question | `quiz` or `flip` | Make the viewer guess in the first 3 to 6 s. |
| Who, what, when | `profile`, `timeline`, `definition` | A person or thing, its story, a key term. |
| Numbers | `chart` (bar, line, donut), `ranking`, `stats` | Data, shares, a top list. |
| Surprises | `flip` | Myths and facts, questions and answers. |
| Takeaway | `quote`, `checklist`, `title` | A line to remember, what to do. |

Drop what you don't need: an announcement can be `title` → `list` → `logo`.
Never repeat the same scene type more than twice in a row.

- Spoken lines: 1.5 to 4 s (4 to 12 words). A scene lasts as long as its line.
- On-screen text is shorter than speech: a bubble echoes the line in fewer
  words, a caption says what the thing is.
- Sync on words: `"at": "Relax"` lands an element when "Relax" is said.
- One call to action, at the end. Never ask to save, like or follow in the hook.
- Avoid words with an unfortunate near-homophone in the target language.
- A name the voice says wrong: spell it phonetically in `voice.text` (keep the
  real spelling on screen); `at` references use the spoken spelling.

### 3. Media
Most videos need none: `cards`, `stats`, `checklist`, `compare`, `prompt`,
`quiz`, `timeline`, `chart`, `ranking`, `flip`, `definition`, `profile`,
`quote`, `chat`, `list`, `pileup`, `title` and `logo` are drawn UI. Prefer them.
`card`, `fan` and `grid` need media: a video, an image or a folder of frames.
Portrait art (about 9:16) for cards, a square close-up (`"avatar"`) for grids;
loops of 2 to 4 s are ideal. Use the user's screens, product shots and photos,
or media they have the rights to. Without any, use the UI-card scenes.
Media must show what the scene says. A decorative character, or another
product's mascot, next to an unrelated tip is worse than no media: use a
`chat`, `list` or `title` scene instead.

### 4. story.json
Copy the closest example and read `docs/story-schema.md`. Then make it theirs
with the next section.

### 5. Make it look like the brand

Readability comes first, and the engine enforces it:
- Every text reaches 4.5:1 contrast with what it sits on. A colour too light
  for text (yellow, pastels) is drawn as a highlighter band behind dark text;
  a fill too light for white text gets dark text. Each fix is a NOTE: better to
  choose colours that need none.
- No text below 40 px (at 1080 wide); long text wraps. Text that still does not
  fit, and text in the top 6.5% or bottom 14% of a vertical frame (where the
  platform's buttons and captions sit), are PROBLEMS: the render refuses until
  you shorten or move them.
- Never write your own visual components (caption strips, typing boxes, chat
  windows) in `engine/engine.js` for a video: use the built-in scene fields
  (`prompt`, `bubble`, `caption`, `chat`, `list`). They already meet these rules.

Colours: name them once, use the names everywhere.
```json
"style": {
  "font": "Poppins", "fontWeights": [500, 700, 800],
  "paper": "#fffaf2", "ink": "#1b1b1f", "accent": "brand",
  "palette": { "brand": "#FF5A1F", "sky": "#3BA3FF", "leaf": "#2FB36D" }
}
```
- `font`: any Google Fonts family, with the weights you use.
- `paper`: the base background; `ink`: all text; `accent`: the default highlight.
- `palette`: your colour names (built-ins: `blue violet green amber rose teal copper slate`).
- One accent, plus at most two support colours. Keep backgrounds `paper` or one
  light tint of the accent for the whole video. Don't give each scene a new
  colour, and never use grey backgrounds: they look dull and carry no meaning.
- A scene's `background` takes a name or hex and is softened towards paper;
  add `"tint": false` for the full colour, `"paper"` for plain.
- Colour one word: give it its own title line with `"color": "brand"`, or a
  tagline part with its own `color`.
- Card stickers, bubbles and progress dots follow the card's `color`; grid rings
  follow each member's `color`; list rows each take a `color`.
- `"decor": false` in `style` removes the soft floating circles.

Size and rhythm:
- Title lines: `"size": 150` (design pixels at 1080 wide; text still shrinks to
  fit), `"big": true` for a huge bouncy word, `"weight": 700`.
- Pace: `music.bpm` sets the beat all scenes snap to (higher is snappier);
  `duration` sets a scene's minimum length; `pad` (default 0.55 s) is the
  breath after its voice; `voice.at` is when speech starts in the scene.
- Grid: `columns`. Logo: `markSize`, `monogram` (a letter in the brand colour)
  or `image` (a media id; PNG keeps transparency).
- Other languages for the little UI words: `"labels": {"now": "maintenant", "number": "N°"}`.

Sound (hear everything in `docs/sounds.md`):
- `"music": {"style": "lofi", "key": "D", "volume": 0.5}`. Styles: playful,
  lofi, upbeat, cinematic, chiptune, tropical, corporate, ambient. A track the
  user owns: `"music": {"file": "music/track.mp3"}`.
- A scene's `mood` changes what plays in it: `tension`, `calm`, `groove`,
  `run`, `outro`, `none`.
- Scenes play their own effects; add a few where a moment deserves one:
  `"sounds": [{"at": "price", "kind": "cash"}, {"at": 1.2, "kind": "whoosh", "dur": 0.6}]`.
  2 to 6 hand-placed sounds in a 30 s video, one `impact` at most.

A new scene type (only when no built-in scene fits, and never for a single
video) goes in `engine/engine.js`: a `render(sc, t)` and a `cues(sc, add)` in the
`SCENES` registry, using `readable`, `onFill`, `wrap` and `safe` for every text.

### 6. Voices
The engine doesn't generate speech: you make each line with the text-to-speech
tools you have, and it times them.

With ElevenLabs connected through Composio:
1. Pick voices from `docs/voices.md` only: every voice there is checked for the
   language and its accent. A voice speaks only its own language: an English
   voice never reads French, a Québécois or Acadian voice never reads a video
   for France. `ELEVENLABS_GET_VOICES` lists voices "that can speak French"
   with American, British and Canadian accents: don't pick from it. Never write
   an id from memory. One voice per speaker, clearly different for characters,
   warm and steady for a narrator; keep the ids in `story.json` under `voices`.
   A voice from the list that the account lacks is added with
   `ELEVENLABS_ADD_SHARING_VOICE` (its `public_user_id` is listed).
2. For each scene with a `voice`, run `ELEVENLABS_TEXT_TO_SPEECH`
   (fetch its schema first) with `voice_id`, `text` = the scene's `voice.text`,
   `model_id` and `output_format` = `mp3_44100_128`. Always set `model_id` (the
   default is English-only): `eleven_multilingual_v2` for French and every
   language other than English (the voices are checked with it; others drift
   in accent); `eleven_v3` only for English lines that use tags like `[excited]`.
3. The result's `data.file.s3url` is the audio. Download it where the engine
   runs: `curl -sfL "<s3url>" -o <project>/voices/<scene id>.mp3`.

With another tool, save each line the same way: `voices/<scene id>.mp3`.
Then:
```bash
node $E/engine/make.mjs <project> voices    # times every file (faster-whisper)
node $E/engine/make.mjs <project> stills    # timeline + warnings
```
A scene whose file is missing gets estimated timings and stays silent, so you
can build and check before the voices exist. Replaced a file? `voices` notices;
`--import` re-times everything.

### 7. Check
- `stills` prints the timeline (each scene's start, length, voice), NOTES and
  PROBLEMS (a word in `at` not found, missing media, text too long, text in the
  platform's zones). Fix every problem in `story.json` in one edit, then run it
  again until none is left; fix the notes too by choosing better colours.
- If you can look at images, open `build/contact-sheet.jpg` and check: text
  colliding or leaving the frame, stickers or confetti over faces, an empty
  first frame (it becomes the thumbnail), key text outside the vertical safe
  zone (clear of the top 8% and bottom 15%). If your instructions say not to
  look at images, rely on the text output alone.

### 8. Render and verify
```bash
node $E/engine/make.mjs <project> all --fps 30
node $E/engine/make.mjs <project> check
```
Rendering takes a few minutes on a small machine: run it in the background
when you can. The `audio` step prints how far each voice line stands above
the music (it must be 12 dB or more, or the render stops). `check` must show
every voice line OK. Then
`ffprobe -v error -show_entries format=duration:stream=codec_type,width,height -of json <project>/out/<title>.mp4`:
planned duration and size, and an audio stream.

## Deliver
The MP4 path, length and format, the voice cast, and the lines you wrote that
make claims (prices, numbers, promises), so the user can confirm them.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `doctor` shows ✗ | Tell the user what is missing; it prints the fix. |
| Warning `word "x" not found` | The `at` word is not in that scene's `voice.text` (spelling, or its phonetic version). |
| A card or avatar is grey | Its media id is missing from `story.media`, or the path is wrong. |
| A voice sounds wrong | Re-generate that one line, save over its file, run `voices` again. |
| `check` says CHECK | The line is inaudible or different: lower `music.volume` (0.35), or re-generate the line. |
| "voice buried under the music" | Lower `music.volume`, or remove hand-placed `sounds` under that line. |
| A voice sounds foreign in French | It is not a French voice, or not on `eleven_multilingual_v2`: pick one from `docs/voices.md`. |
| PROBLEM "only fits at …px" / "needs … lines" | Shorten the text or split the title into two lines. |
| Video too long | Shorten the spoken lines; scenes follow their voices. |
