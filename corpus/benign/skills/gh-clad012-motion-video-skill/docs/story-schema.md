# story.json reference

A video is one `story.json` in a project folder. The engine turns it into a
timeline, renders every frame, builds the soundtrack and encodes an MP4.

```
my-video/
  story.json      the whole video
  media/          your videos and images (any names)
  voices/         generated voice lines + voices.json (commit them)
  build/          generated, safe to delete
  out/            the final MP4 and a contact sheet
```

## Top level

| Field | Type | Default | Meaning |
|---|---|---|---|
| `title` | string | folder name | Used for the output file name. |
| `format.width`, `format.height` | px | 1080 × 1920 | 1080×1920 portrait (TikTok, Reels, Shorts), 1920×1080 landscape, 1080×1080 square. |
| `format.fps` | number | 60 | Render frame rate. Use `--fps 30` for fast drafts. |
| `language` | ISO code | none | Passed to ElevenLabs (`"en"`, `"fr"`, `"es"`…). |
| `style.font` | Google Font name | `"Geist"` | Loaded from Google Fonts. |
| `style.fontWeights` | number[] | `[500,600,700,800]` | Weights to load. |
| `style.paper`, `style.ink` | hex | `#f4f3ef`, `#1c1c1b` | Base background and text colour. |
| `style.accent` | colour name or hex | `"violet"` | Default highlight colour. |
| `style.palette` | `{name: hex}` | 8 built-ins | Adds or overrides named colours. Built-ins: `blue violet green amber rose teal copper slate`. |
| `style.decor` | boolean | `true` | Soft floating circles behind scenes. |
| `music.style` | name | `"playful"` | `playful`, `lofi`, `upbeat`, `cinematic`, `chiptune`, `tropical`, `corporate`, `ambient`. Hear them in [sounds.md](sounds.md). |
| `music.file` | path | none | Your own music track instead of a style (looped, faded, ducked under voices). |
| `music.bpm` | number | the style's | Scene lengths snap to this beat. |
| `music.key` | `C`…`B` (`F#`, `Bb`…) | `"C"` | Transposes all music and melodic effects. |
| `music.progression` | chord names | `["C","Am","F","G"]` | One chord per groove scene, cycling. Written in C; transposed to `key`. |
| `music.volume` | 0–1 | 0.55 | Music level (sound effects and voices are separate). |
| `music.enabled` / `music.sfx` | boolean | `true` | Turn music or sound effects off. |
| `autoSfx` | boolean | `true` | `false` keeps only the sounds scenes place by hand (see `sounds`). |
| `voices` | `{who: voiceId}` | | Notes for you: the voice id each speaker uses in your text-to-speech tool, so every take matches. The engine does not read it. |
| `media` | `{id: path}` or `{id: {full, avatar}}` | | Videos (mp4/mov/webm/gif), images (png/jpg/webp) or folders of frames. `full` is used on cards, `avatar` (square) in grids; each falls back to the other. |
| `labels` | `{now, number, prompt, assistant, quiz, myth, fact}` | `{now: "now", number: "No.", prompt: "PROMPT", assistant: "AI assistant", quiz: "Quiz", myth: "Myth", fact: "Fact"}` | Small UI words, for other languages (e.g. `{"now": "maintenant", "number": "N°", "assistant": "Assistant IA", "myth": "Idée reçue", "fact": "En vrai"}`). |
| `scenes` | array | | The video, in order. |

## Readability (enforced)

The engine checks every text it draws, over the whole video, before it renders:

- **Contrast:** every text reaches 4.5:1 against what it sits on. A colour too
  light to read as text (yellow, pastels) becomes a highlighter band behind
  dark text; a fill too light for white text gets dark text, or a darker fill.
  Each fix is listed as a NOTE by `stills`: better to pick colours that need
  none. Ink on paper must reach 7:1.
- **Size:** no text below 40 px at 1080 wide. Bubbles, captions, list items,
  prompts and messages wrap onto more lines rather than shrink. A title line
  shrinking below 72 px is a PROBLEM: split it into two lines.
- **Safe zones** (vertical formats): text reaching into the top 6.5% or the
  bottom 14% of the frame is a PROBLEM. That's where TikTok, Reels and Shorts
  draw their buttons and caption.
- **Voices:** every line is brought to the same speech loudness; under speech
  the music drops to a fifth and the effects to a third, then further under
  any line that still doesn't stand 15 dB above them. The `audio` step prints
  each line's level and stops when one is under 12 dB (a safety net).

PROBLEMS stop `frames` and `all` until they are fixed (`--force` overrides,
never for a video you deliver). The first scene shows at frame 0 what it would
show in its first 0.8 s, because frame 0 is the thumbnail.

## Every scene

| Field | Meaning |
|---|---|
| `type` | `pileup`, `title`, `chat`, `cards`, `stats`, `checklist`, `compare`, `prompt`, `quiz`, `timeline`, `chart`, `ranking`, `flip`, `definition`, `profile`, `quote`, `fan`, `card`, `list`, `grid`, `logo`. |
| `id` | Optional name; also the voice file name. Default `s1`, `s2`… |
| `voice` | `{ "who": "narrator", "text": "What is said.", "at": 0.35 }`. `at` is when speech starts, in seconds from the scene start. |
| `duration` | Minimum length in seconds. With a voice, the scene is at least as long as the line plus `pad` (0.55 s). Always rounded up to whole beats. |
| `background` | Colour name or hex. Tinted towards paper unless `"tint": false`. `"paper"` for plain. Changes wipe in as a circle. |
| `mood` | Music for this scene: `tension`, `calm`, `groove`, `run`, `outro`, `none`. Defaults: pileup and quiz tension; title, fan, quote and definition calm; ranking and grid run; logo outro; the rest groove. |
| `sounds` | Extra sound effects: `[{ "at": "word", "kind": "whoosh", "gain": 1, "pitch": 1, "dur": 0.5 }]`, or `{ "at": 1.2, "file": "sounds/hit.wav" }` for your own. 43 kinds, listed with audio in [sounds.md](sounds.md). |
| `autoSfx` | `false` turns off the effects this scene type plays by itself. |

### Voice files

The engine does not generate speech. Make each scene's line with any
text-to-speech tool (for example an ElevenLabs account connected through
Composio) or record it, and save it as `voices/<scene id>.mp3` (or `.wav`,
`.m4a`, `.ogg`). The `voices` step times its words: from
`voices/<scene id>.alignment.json` when present (the ElevenLabs
with-timestamps response), else with faster-whisper when installed
(`WHISPER_MODEL`: a model name such as `small`, or a local model folder), else
by estimating across the speech it detects. `voice.text` must hold exactly
what is said: word sync and checks rely on it. A scene without a file gets
estimated timings and stays silent. `--import` re-times every file.

### Timing values (`at`, `until`)

Anything called `at` accepts:

- a number: seconds from the scene start (`1.2`);
- a spoken word: `"Relax"` is when that word starts in the scene's voice line
  (prefix match, case and accents ignored); `"fruit#2"` is the second match;
  `"Relax:end"` is when the word finishes.

A word that is not found falls back to a default time and is reported as a
warning by `make.mjs stills`.

## Scene types

### `pileup`: too much, then relief
Cards (notifications, tasks, bills) rain down and shake harder and harder,
words slam in on the beat of the voice, a headline lands, then everything is
blown away in the last half second.

```json
{ "type": "pileup",
  "voice": { "text": "Bills, emails, meetings... too much?" },
  "items": [ { "icon": "B", "title": "Electricity", "body": "Due Friday", "color": "amber", "time": "now" } ],
  "slams": [ { "text": "Bills", "at": "Bills" } ],
  "headline": { "text": "too much?", "at": "too", "color": "rose" } }
```
8 to 16 items reads as "overwhelming". Up to 4 slams.

### `title`: big kinetic words
Lines stack in the middle; each pops in letter by letter at its `at`.

```json
{ "type": "title", "lines": [
  { "text": "Relax.", "at": "Relax", "until": "Meet", "breathe": true },
  { "text": "Meet the", "at": "Meet" },
  { "text": "team.", "at": "team", "big": true, "color": "violet", "confetti": true } ],
  "badge": { "text": "Acme", "at": "Acme" } }
```
Line fields: `text`, `at`, `until` (leaves early), `big` (huge, bouncy),
`breathe` (slowly grows in the centre, for calm words; not stacked),
`color`, `size` (design px), `weight`, `confetti`, `y` (0–1 of height, breathe lines only).

### `fan`: a hand of cards
Everything from `title`, plus `cards` (media ids) that fan in from the bottom
at `cardsAt`. If the next scene is a `card` showing `cards[0]`, that card grows
into it: a seamless hand-off.

### `card`: one character, product or photo
A big media card flies in from alternating sides and lands with a squish.

| Field | Meaning |
|---|---|
| `media` | Media id (uses its `full` variant). |
| `color` | Sticker, progress and bubble accent. |
| `name` | Sticker over the bottom edge. |
| `caption` | One line under the card. |
| `bubble` | Speech bubble above the card; pops when the voice starts, with a live "speaking" meter. Keep it shorter than the spoken line (8 words at most). |
| `prompt` | Text to copy (a prompt, a command, a formula): a panel under the card that types out within 1.2 s of the voice, then stays readable. The card gets smaller to make room. 30 words at most. |
| `number` | `false` hides the "No. 01" badge, or a string replaces it. |
| `progress` | `false` hides the dots shown across a run of consecutive cards. |

The card squashes slightly on every spoken word.

### UI cards (no media needed)

These scenes are drawn UI: white cards, icon tiles, numbers, checkboxes. They
need no images or videos. Title lines (same as `title`, in `lines`) sit above
them. Icons are drawn line icons (any other short text, 1 to 3 characters, is
shown as a letter or number in the tile):

- UI: `check x up down search settings link file pencil list chat mail bell lock shield eye info question warning`
- Time and data: `clock calendar hourglass chart target star trophy flag`
- Things: `home car plane food cup music camera play phone code money cart gift book school idea rocket bolt fitness`
- Nature and people: `globe pin leaf sun moon cloud drop fire heart users`

#### `cards`: feature cards
Cards slide in one by one at their `at`; the one being talked about lifts,
with an outline in its colour. They stack in one column on vertical formats,
and sit in a grid of up to 3 or 4 (`columns`) on 16:9.

```json
{ "type": "cards", "lines": [ { "text": "Why it works", "at": 0.1 } ],
  "items": [ { "icon": "bolt", "title": "Plans your morning", "text": "From your calendar and inbox.", "at": "plans", "color": "coral" } ] }
```
Title: one line on vertical formats, two on 16:9. Text: two or three lines. 2 to 4 cards.

#### `stats`: metric cards
Each number counts up from `from` (default 0) to `value` when its card lands;
an optional bar fills, and an optional change chip (`delta`) pops.

```json
{ "type": "stats", "items": [
  { "icon": "clock", "value": 6, "prefix": "+", "suffix": " h", "label": "focus time", "at": "six", "bar": 0.7, "delta": "+38%", "color": "coral" },
  { "icon": "calendar", "value": 0, "from": 5, "label": "missed deadlines", "at": "zero" } ] }
```
`decimals` (default: as written), `bar` (0 to 1, or `true` for value/100),
`deltaColor` (default green), `columns`. Numbers use the story's `language`
for separators (`2,4` in French). 2 to 4 stats.

#### `checklist`: a to-do card
A card with a title, a live `done/total` counter and items; each item ticks
at its `at` (checkbox fills, check draws, the text is struck through), the
progress bar grows, confetti when all are done.

```json
{ "type": "checklist", "title": "Today", "color": "coral",
  "items": [ { "text": "Answer the 3 emails that matter", "at": "emails" }, { "text": "30-minute walk", "at": "walk" } ] }
```
One short line per item; 3 to 5 items.

#### `compare`: before and after
A `before` card (muted, with ✗ marks), then an `after` card (in the accent,
with ✓ marks) that wins: the before card settles back, confetti on the after.
Stacked on vertical formats, side by side on 16:9.

```json
{ "type": "compare", "color": "mint", "badColor": "slate",
  "before": { "title": "Without context", "items": ["Vague answer", "Three back-and-forths"], "at": "without" },
  "after": { "title": "With context", "items": ["Precise answer", "Right first time"], "at": "With" } }
```

#### `prompt`: a tip card
A number pill (`labels.number` + position among the prompt scenes, or
`number` as text, or `false`), a big title, and the prompt panel that types
out within 1.2 s of the voice, then an optional `caption` under it. The block
is centred in the frame.

```json
{ "type": "prompt", "color": "idee", "title": "Le vide-cerveau",
  "prompt": "Voici tout ce que j'ai en tête : […]. Trie en 4 listes.", "caption": "Tu vides ta tête, l'IA range." }
```

### Explainer cards (any topic, no media needed)

More drawn UI, made for explaining anything: history, science, money, health,
a recipe, a place, a person. Title lines (`lines`) sit above the ones that
take them. Text that appears as it is said (`quote`, `definition`) follows the
voice word by word when the voice reads the same words.

#### `quiz`: a question with an answer reveal
The question card, options popping in one by one (A, B, C…), a countdown ring
while the viewer thinks (when there is more than a second before the reveal),
then the right option turns green with confetti, the others grey out, and an
optional explanation card slides in. A strong hook: ask in the first scene.

```json
{ "type": "quiz", "question": "Which country drinks the most coffee per person?",
  "options": [ { "text": "Brazil", "at": "Brazil" }, { "text": "Finland", "at": "Finland" }, { "text": "Italy", "at": "Italy" } ],
  "answer": 1, "revealAt": "Finland#2", "explain": "About 12 kg per person, every year." }
```
`options` may be plain strings. `answer` is the index of the right one (from
0). `revealAt` defaults to 62% of the scene. `goodColor` (default green),
`color` (letters, icon), `timer: false`, `label` (default `labels.quiz`).
2 to 4 options, one short line each; on 16:9 they sit in two columns.

#### `timeline`: dates or steps on a line
A card with a line that draws itself from stop to stop; each stop's dot fills
and its label, title and text slide in at its `at`. Vertical on 9:16 (or with
`"vertical": true`), horizontal on 16:9.

```json
{ "type": "timeline", "lines": [ { "text": "A short history", "at": 0.1 } ],
  "items": [ { "label": "1554", "title": "Istanbul's first coffee house", "text": "Optional detail", "at": "Istanbul", "color": "leaf" } ] }
```
`label` is short (a year, "Step 1", "9:00"). 3 to 5 stops; titles two lines
at most, texts two (three on 16:9).

#### `chart`: bar, line or donut
A card with an optional `title` and `caption` (a source, "approximate
figures"). Values format like `stats` (`prefix`, `suffix`, `decimals`, set on
the scene or per item).

- `"kind": "bar"`: bars grow at their `at` (default one after the other from
  the scene's `at`), values count up above them, labels under. Mark one with
  `"highlight": true` and the others dim. 2 to 6 bars on 9:16, up to 8 on 16:9.
- `"kind": "line"`: the line draws from left to right from the scene's `at`,
  dots pop as it passes, the highlighted points (default: the last one) get a
  value pill. `min`/`max` set the scale (default from 0).
- `"kind": "donut"`: the ring sweeps round, the highlighted item (default the
  first) shows big in the centre, a legend lists every slice with its value.
  Slices take the palette in turn unless they set `color`. 2 to 5 slices.

```json
{ "type": "chart", "kind": "bar", "title": "Coffee per person, per year", "caption": "Approximate figures", "suffix": " kg",
  "items": [ { "label": "Finland", "value": 12, "highlight": true, "at": "Finland" }, { "label": "Norway", "value": 9.9, "at": "Norway" } ] }
```

#### `ranking`: a top list
Rows in rank order (number one first). By default they are revealed from the
bottom up (`"order": "down"` reveals number one first), with a drumroll before
number one, which lifts with an outline and confetti. Ranks 1 to 3 get gold,
silver and bronze tiles (`"medals": false` for plain). With `value`, each row
has a bar and a number that count up.

```json
{ "type": "ranking", "lines": [ { "text": "Biggest growers", "at": 0.1 } ], "decimals": 1,
  "items": [ { "label": "Brazil", "value": 3.4, "at": "Brazil" }, { "label": "Vietnam", "value": 1.8, "at": "Vietnam" } ] }
```
Items may set `icon` and `color`. 3 to 6 rows on 9:16, 5 on 16:9.

#### `flip`: myth and fact, question and answer
A card shows its `front`, then flips over at the `back`'s `at` to show the
back, with confetti. Default labels `labels.myth` / `labels.fact`, default
icons ✗ / ✓, default colours rose / green.

```json
{ "type": "flip",
  "front": { "label": "Myth", "text": "Coffee dehydrates you.", "at": "Myth" },
  "back": { "label": "Fact", "text": "A normal cup hydrates you almost as well as water.", "at": "Actually" } }
```
Each side: `label`, `text` (6 lines at most), `icon`, `color`, `at`. Use it
for myths, "what people think / what is true", a question and its answer, or
a riddle.

#### `definition`: a dictionary card
The word pops in with a highlighter under it, then how to say it and what
kind of word it is, then the definition word by word, then an example under a
coloured bar.

```json
{ "type": "definition", "word": "Crema", "phonetic": "/ˈkreɪ.mə/", "kind": "noun",
  "text": "The golden foam on top of a fresh espresso.", "example": "No crema? Your beans are probably stale.", "exampleAt": "No" }
```
`textAt` (default: when the voice starts), `exampleAt`, `color`. Also good
for a term, an acronym, a law or a rule.

#### `profile`: a person, place or thing
A card with a round avatar (initials, an `icon`, or a photo with `media`),
the name, a role, then facts that slide in one by one with their icons.
Facts sit under the name on 9:16 and beside it on 16:9.

```json
{ "type": "profile", "name": "Kaldi", "role": "Goat herder, Ethiopia (legend)", "icon": "leaf", "color": "leaf",
  "facts": [ { "icon": "eye", "text": "Saw his goats dance after eating red berries", "at": "dancing" } ] }
```
`initials` overrides the automatic ones. 2 to 4 facts, two lines each.

#### `quote`: a quote card
A big quote mark, the quote appearing word by word as it is said, words
listed in `highlight` getting a highlighter band, then the author with their
initials.

```json
{ "type": "quote", "text": "A cup of coffee commits one to forty years of friendship.",
  "highlight": ["forty", "friendship"], "author": "Turkish proverb", "role": "Optional line" }
```
`at` (card), `textAt`, `authorAt`, `color`, `initials`. 8 lines at most on
9:16, 5 on 16:9. Quote real people only with a quote they really said.

### `chat`: a chat window
A chat window whose messages appear one by one: the user's in the accent colour
on the right, the answers typed out on the left. An optional stamp slams
under the last answer. Title lines (same as `title`) above. Good for "you use it
like this… (bad answer)" hooks and before/after demos.

```json
{ "type": "chat", "name": "Assistant IA",
  "lines": [ { "text": "Tu utilises l'IA", "at": "Tu" }, { "text": "comme Google ?", "at": "comme", "color": "brand" } ],
  "messages": [ { "from": "user", "text": "fais-moi un planning", "at": 0.5 },
                { "from": "ai", "text": "Voici un planning type : 1. Se réveiller…", "at": 1.2 } ],
  "stamp": { "text": "BOF.", "at": "passes", "color": "rose" } }
```
`name` is the window title (default `labels.assistant`). 2 to 4 short messages.

### `list`: steps, tips, agenda
A title and rows that slide in from alternating sides at their `at`.

```json
{ "type": "list", "title": "How it works",
  "items": [ { "text": "Pick a plan", "at": "Pick", "icon": "1", "color": "teal" } ] }
```
3 to 5 items. `icon` defaults to the item number.

### `grid`: everyone together
Round avatars pop in one by one (each plays a marimba note, rising), then do a
wave. Title lines (same as `title`) above, `footer` below.

```json
{ "type": "grid", "lines": [ { "text": "Six fruits.", "at": "Six" } ],
  "members": [ { "media": "banana", "color": "banana" } ],
  "footer": { "text": "Mix your own.", "at": "Endless" }, "columns": 3 }
```
If the previous scene is a `card` whose media is a member, it shrinks into its seat.

### `logo`: the ending
A mark, the name, a tagline and a URL. If the previous scene is a `grid`, the
members fly into the mark first.

| Field | Meaning |
|---|---|
| `name`, `nameAt` | Wordmark and when it pops. |
| `monogram` | Letter in the default rounded-square mark (default: first letter of `name`). |
| `image` | Media id of a logo image instead (PNG keeps transparency). |
| `color` | Mark colour. |
| `markSize` | Mark size in design px (300). |
| `tagline` | Parts of one line, each popping at its own `at`, each with its own `color`. |
| `url`, `urlAt` | Small line under the tagline. |

## Adding a scene type

Scene types live in `engine/engine.js` in the `SCENES` registry. Each has
`render(sc, t)`, which appends SVG to `front`/`back` and media draw calls to
`media`, and `cues(sc, add)`, which adds sound-effect cues. Everything must be
a pure function of `t`: no timers, no randomness except `hash(n)`.
