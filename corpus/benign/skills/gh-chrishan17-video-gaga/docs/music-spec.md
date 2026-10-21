# The pattern spec (the older way to score)

A score can also be declared as a **spec** instead of written as a piece: layers of one- or two-bar patterns that an arranger repeats bar by bar, switched on and off by each scene's `energy`, with a melody composed for the gaps. It is quick and safe, and the preset example videos still use it, but it sounds like what it is: a loop that changes when the scene changes. For a new video, write the score as one piece ([music-and-sound.md](music-and-sound.md)); use the spec for a draft, or when a loop is what the video wants.

The instruments, the voice ducking, the levelling, the sound effects and the listening checks are the same either way ([music-and-sound.md](music-and-sound.md) §3–§6).

## 1. The spec

The composition declares it in full:

```js
CV.create({
  music: {
    // the grid and the harmony
    bpm: 104, key: 'A', mode: 'major', progression: [0, 4, 5, 3], seed: 3, kit: 'room',
    // what plays, and from which scene energy up
    layers: [
      { name: 'piano', inst: 'piano', notes: [0, 2, 1, 2], pattern: 'X.x.X.x.', vel: [0.1, 0.14] },
      { name: 'strings', inst: 'strings', notes: 'chord', pattern: 'X---', vel: [0.05, 0.09], from: 0.35 },
      { name: 'bass', inst: 'bass', notes: ['root', 'root', 'fifth'], octave: -1, pattern: 'X..x..X.', vel: 0.26, from: 0.3 },
      { name: 'kick', inst: 'kick', pattern: 'X...X...', vel: 0.45, from: 0.45 },
      { name: 'clap', inst: 'clap', pattern: '..X...X.', vel: 0.2, from: 0.45 },
      { name: 'shaker', inst: 'shaker', pattern: 'xXxXxXxXxXxXxXxX', vel: 0.06, from: 0.6 },
    ],
    // the melody that plays only where nobody speaks
    lead: { inst: 'bell', kind: 'glock', range: [76, 91], rhythm: 'melodic', vel: 0.11 },
  },
  scenes: [
    { id: 'hook', voiceDelay: 2.1, energy: 0.45, draw … },            // a bar of music before the first word
    { id: 'curve', energy: 0.6, sfx: [{ at: 'ten', type: 'tick' }], draw … },
    { id: 'breath', narration: false, beats: 6, energy: 0.85, draw … }, // music-only beat: let the result land
    { id: 'end', tail: 1.6, energy: 0.55, draw … },                    // the final chord rings out with the end card
  ],
});
```

`gaga render` renders the score (cached in `build/music.wav`), mixes it with the voice and checks the balance. `gaga music <project>` renders only the score, so the preview player can play it, and prints the arrangement: key, BPM, chords, layers, energy per bar, **how loud each part of the mix is** (`mix: bed · keys · drums · lead · reverb`, dB of the whole), the cut times, every sound effect and any **warnings** about the spec. A spec that breaks a limit (§2.4) is refused with a list of exactly what to fix.

| `music` key | Default | Meaning |
|---|---|---|
| `bpm` | — (required) | The beat grid. Every cut and the first syllable of every line snaps to it |
| `key` | — | Tonic: `C C# Db D D# Eb E F F# Gb G G# Ab A A# Bb B` |
| `mode` | — | `major`, `minor`, `dorian`, `lydian`, `mixolydian`, `phrygian` |
| `progression` | — | 1–8 scale degrees, 0 = tonic (`[0, 5, 3, 4]` = I–vi–IV–V in major). Chords are diatonic triads, voice-led |
| `sevenths` | false | Four-note chords |
| `chordBars` | 1 | Bars per chord: 1, 2 or 4 |
| `layers` | — | The parts (§2.2). `[]` with no `lead` = sound effects only, on the grid |
| `lead` | none | The melody in the gaps (§2.3): written note by note (`line`) or composed from a `rhythm`. Or omit it |
| `kit` | `'standard'` | The drum kit: `standard`, `room` (live, warm), `power` (big rock), `electronic`, `808` (hip-hop, trap, modern pop), `jazz`, `brush` (soft, intimate), `orchestra` (concert percussion) |
| `swing` | 0 | 0–0.5: delays every other eighth/sixteenth (0.15–0.3 = a lazy, human groove). Layers can set their own |
| `seed` | 1 | Change it to hear a different melody in the same design |
| `fills` | true | A fill and a crash into a section where the energy rises (only where the score has drums) |
| `beatsPerBar` | 4 | |
| `snap` | `'beat'` | Where cuts land: `'beat'`, `'half'`, `'bar'` or `false`. Scenes can override with `snap` |
| `voiceOnBeat` | true | Start every voice line on an eighth note |
| `energy` (per scene) | an arc | 0..1. Decides which layers play. Default: a confident open, a fuller middle, a settled end, with music-only scenes a little higher |
| `duck` | −10 | How many dB the bed dips while someone speaks (the melody dips a further 12 dB) |
| `gap` | 6 | How many dB the music-only passages sit under the voice's speech level. The renderer measures the actual voice, so every voice gets the same balance |
| `volume` | 1 | A gain on top of that (`1.4` ≈ +3 dB) |
| `sfx` | true | Transitions play their natural sound |
| `parts` | — | Chapters of a long score: `{ name: { key, mode, progression, chordBars, sevenths, seed, lead, lines } }`, chosen by a scene's `part` (§2.5) |
| `ending` | `'resolve'` | `'resolve'` lands the tonic chord on the last downbeat and lets the score's own instruments ring. `'none'` lets the groove run to the end |
| `file` | — | A licensed track instead of the generated score (side-chain ducked, faded) |

Each preset's example video carries a score written for that video. Read one only to see the spec in use; start every new score from this brief (§2.1).

## 2. Designing the score

### 2.1 From a sound to a spec

What a good score sounds like is in [music-and-sound.md](music-and-sound.md) §1. This section is how that sound becomes a spec.

**A reference** is a genre, an era, an artist or a soundtrack that a music supervisor would license for this exact video ("Joe Hisaishi strings over a felt piano", "lo-fi hip hop with a dusty Rhodes", "2010s indie folk, hand claps and a stomp", "city pop bass and bright keys", "Nils Frahm, a repeating piano figure that grows", "trap hats and an 808 under a koto line", "bossa nova guitar, brushes"). It comes from the story's feeling and the audience, not from the visual preset or the subject: a video about running can be a lazy bossa nova. Translate it into tempo, mode, a progression, the instruments that carry that sound (§2.2), a groove pattern and swing.

**The hook** is a layer: a one- or two-bar `pattern` with `notes` (an arpeggio, a bass line, a plucked riff, a chord rhythm), or a `line` you write note by note, that plays from the first scene. The `lead` answers it in the gaps (§2.3).

**The arc** is the scenes' `energy` against each layer's `from`: a layer enters in every bar whose energy reaches its `from`. So the energy values are the arrangement: low where the story holds its breath, the groove in early, a change at the turn (more layers, or all but one falling away, or a new `part`), and a landing.

Say it in one line in the brief: *feel in three words · reference · BPM key mode · the hook · how it builds*.

### 2.2 Layers

A layer is one part, repeated every bar (or every `bars` bars), playing in the bars whose energy is in `[from, to)`.

| Key | Meaning |
|---|---|
| `inst` | **beds:** `pad` (warm synth pad), `synthpad` (brighter polysynth), `strings` (string section), `sinepad` (soft, slow strings), `choir` · **keys:** `piano` (grand), `felt` (mellow, intimate piano), `epiano` / `keys` (electric piano) · **plucked:** `guitar` / `pluck` (nylon), `acoustic` (steel-string), `harp`, `koto`, `pizz` (pizzicato strings) · **mallets:** `bell` with `kind`: `glock`, `marimba`, `kalimba`, `celesta`, `vibes`, `musicbox`, `xylophone`, `tubular` · **melodic:** `flute`, `shakuhachi`, `violin`, `cello`, `horn`, `brass`, `synthbrass`, `lead` (square; `saw: 1` for a saw), `timpani` · **bass:** `bass` with `kind`: `finger` (default), `picked`, `upright`, `fretless`, `synth`, `synth2` (`synth: true` = `kind: 'synth'`) · **drums:** `kick`, `snare`, `clap`, `snap`, `rim`, `hat`, `openhat`, `shaker`, `tamb`, `ride`, `crash`, `tom` (`pitch` Hz picks floor … high tom), `conga` |
| `line` | pitched only, instead of `pattern` + `notes`: the part written note by note (notation in §2.3), repeated from the start of each part. For a bass line, a counter-melody or a riff whose exact notes matter. It does not follow chord changes, so a part that changes the harmony rewrites it in its `lines` (§2.5) |
| `pattern` | Steps across the bar(s), equal length: `X` hit, `x` soft hit (0.6), `1`–`9` hit at n/9, `-` hold the previous note one more step, `.` rest. Spaces are ignored. `'X---'` = a whole-bar note, `'X.x.X.x.'` = eighths, 16 characters = sixteenths |
| `bars` | 1, 2 or 4: how many bars the pattern spans |
| `notes` | pitched only: `'chord'` (all chord tones), or a list cycled per hit: `root`, `third`, `fifth`, `seventh`, or a chord-tone index `0`–`7` of the voiced chord (`3` on a triad = the bottom note an octave up); add `^` / `_` for an octave up / down (`'root_'`, `'0^'`). Default: `'chord'` (`'root'` for bass). `[0, 1, 2, 3, 2, 1]` on eighths is an arpeggio |
| `octave` | Shift the whole layer −2…+2 octaves |
| `vel` | Loudness of a full hit, or `[low, high]` scaled by the scene energy. Capped per instrument (§2.4) |
| `gate` | Note length as a fraction of its steps (default 0.9; 1 for beds); above 1 lets notes ring over the next hit (piano arpeggios: 1.5–2) |
| `from`, `to` | The energy range the layer plays in (default 0 and 1) |
| `pan` | −1…1 |
| `swing` | 0–0.5, this layer only |
| sound | `bright` 0..1 (brightness; 0.5 = as sampled) · `cutoff` Hz (pad, synthpad, bass, lead) · `attack`, `release` s (slower or faster envelopes) · `verb` 0..1, `echo` 0..0.6 (reverb and dotted-eighth delay sends) · `strum` s between chord notes · `decay` s (keys: how long a note may ring) · `kind` (bell, bass) · `saw` (lead) · `pitch` (tom). Any number may be `[low, high]` by energy |

### 2.3 The lead

**Write it.** `lead: { inst, vel, line, …sound }` plays the melody you wrote, bar by bar from the start of each part, **only where nobody is speaking**:

```js
lead: { inst: 'violin', vel: 0.12, line: 'E5:1.5 D5:.5 C5:1 G5:1 | A5:3 r:1 | F5:1 E5 D5 C5 | D5:3 r:1' }
```

A note is a name with its octave (`C4` = middle C, MIDI 60; `F#5`, `Bb3`); `:beats` sets its length and carries over to the next notes until changed (`:1/3` for triplets); `r` is a rest; `[A3 C4 E4]:2` is a chord; `@1.2` accents a note (0.3–1.3 × `vel`); `|` checks that the bar is full. The line must fill whole bars and is at most 16 bars long; it repeats. It is played like a player would: its high points a little stronger, downbeats leaning, off-beats lighter.

A good line is a tune someone could hum after one hearing: a short motif (2–4 notes with a recognisable rhythm) stated, answered (the same rhythm, moved), contrasted, and brought home; mostly steps with one or two leaps that land on a chord tone; chord tones on the strong beats; a peak note reached once, about two-thirds of the way through; phrases that end on long notes and leave rests for breath; the last phrase resolving to the tonic. Write it in the key and against the progression you chose: `gaga music` warns when more than a quarter of the notes fall outside the key. It sounds wrong when it wanders by step with no rhythm of its own, sits on one note, leaps on every note, crowds every beat, or never lands.

**Or let it be composed.** `lead: { inst, range: [lowMidi, highMidi], rhythm, vel, …sound }`: `inst` is any keys, plucked, mallet or melodic instrument (`piano`, `felt`, `epiano`, `guitar`, `harp`, `koto`, `bell`, `flute`, `shakuhachi`, `violin`, `horn`, `lead` …); `rhythm` is `sparse` (long notes, reflective), `melodic` (a singable line) or `rhythmic` (short, syncopated). Two seeded motifs are composed per part and laid out as an eight-bar period (statement, an answer a step higher, a contrast, the statement again landing home), on the key's scale with chord tones on the strong beats, and played **only where nobody is speaking**. Keep the range above the voice (MIDI ≥ 69 for a lead that sings, at least 7 semitones wide).

### 2.4 Rules and limits

`scripts/music.mjs` enforces these (`validateScore`, `LIMITS`); a spec that breaks one is refused with the exact field to fix:

- `bpm` 60–150; `progression` 1–8 degrees 0–6; `chordBars` 1, 2 or 4; known `key`, `mode` and `kit`.
- At most **8 layers**, at most **32 steps per bar** per layer, and at most **40 drum hits per bar** across all drum layers at full energy.
- Loudest hit per instrument: beds (pad, synthpad, strings, sinepad, choir) 0.12 · keys, plucked and mallets 0.2 · flute, violin, cello, horn, brass 0.15 · lead 0.12 · timpani 0.3 · bass 0.35 · kick 0.7 · snare 0.35 · clap 0.3 · conga 0.3 · snap 0.25 · rim 0.2 · crash 0.15 · hat, shaker, tamb, ride 0.12 · openhat 0.1 · tom 0.5. Lead `vel` ≤ 0.15. (The mix is levelled against the voice afterwards; these keep one part from swamping the others.)
- Notes stay inside MIDI 28–100 (pattern notes are folded by octaves; a written `line` outside it is refused); sound options stay in safe ranges (e.g. `cutoff` 80–8000 Hz, `echo` ≤ 0.6).
- A written `line` fills whole bars (each `|` must close a full bar), is at most 16 bars long, and a layer has either a `line` or a `pattern`, not both.
- Unknown keys are errors, so typos never pass silently.

And these are **design rules** (warnings from `gaga music`, and things to check yourself):

- Something harmonic plays at low energy (a piano, keys, guitar or pad with `from` ≤ 0.3), so quiet scenes are not empty.
- Something articulates the beat: a score of only pads/strings and bass drones (warned).
- A low tom is not the only pulse (warned): that is a horror-film heartbeat.
- Layers enter with energy (`from`), so the score builds and breathes with the story rather than playing flat.
- Leave the voice its band: keep busy parts (arps, 16ths) at `from` ≥ 0.45 or in music-only scenes, and prefer piano, guitar, bass and soft drums under narration.
- Balance by numbers: in `gaga music`'s `mix:` line, drums usually sit around −4 to −8 dB of the whole when the groove is in, the lead around −10 to −15, and the reverb below −10 (above that it washes out).
- One signature sound carries the identity (the hook's instrument); the rest supports it.

### 2.5 Parts: a long score in chapters

One four-chord loop carries a 30 s piece. Over two or three minutes it repeats fifteen times or more and turns into wallpaper, and the melody's two motifs come round again and again. A long video is told in chapters, so give the score chapters too: **parts**.

```js
music: {
  bpm: 88, key: 'D', mode: 'major', progression: [0, 4, 5, 3], layers: [ … ], lead: { … },
  parts: {
    stuck:   { key: 'B', mode: 'minor', progression: [0, 5, 2, 6], chordBars: 2, lead: { rhythm: 'sparse' } },
    hundred: { progression: [5, 3, 0, 4], seed: 8, lead: { rhythm: 'rhythmic' } },
    home:    { progression: [3, 0, 4, 0], chordBars: 2 },
  },
},
scenes: [
  { id: 'open', … },                    // the main harmony (the top-level spec)
  { id: 'kid', part: 'stuck', … },      // from here on: B minor, two bars per chord
  { id: 'voice', … },                   // still 'stuck' (a part holds until the next one)
  { id: 'day30', part: 'hundred', … },
]
```

- A part may change `key`, `mode`, `progression`, `chordBars`, `sevenths`, `seed` (new melody motifs), `lead` (merged over the main lead: a different `rhythm`, `range`, `vel` or its own written `line`) and `lines: { layerName: line }` (new written lines for named layers). A written line doesn't follow chord changes, so a part that changes the harmony gives its lead and its written layers new lines (`gaga music` warns when it doesn't). The **layers stay the same** for the whole video, so it keeps one sound; energy still decides which of them play.
- Put `part` on the first scene of each chapter. It holds until another scene names a part. The cut into that scene moves to the next **bar line** (not just the beat) so the new chords arrive with the new picture; this can hold the previous scene up to one bar longer. Set the scene's `snap` to override.
- Each part starts on the first chord of its own progression, and the melody in it uses its own two motifs. The ending resolves to the home chord of the part the video ends in.
- Design parts from the story, not for variety's sake: a relative minor for the low point, a pop loop (`[5, 3, 0, 4]`) for momentum, a slower `chordBars: 2` for reflection, and back home for the ending. Three to six parts suit a 2–5 minute piece.
- `gaga music` prints where each part takes over (`parts (name@bar): main@1 stuck@9 …`) and warns when a score longer than ~75 s loops one progression more than eight times.

## 3. How the score follows the video

- **One clock.** The runtime moves every cut so that the middle of the transition lands on a beat, starts each voice line on an eighth note, and ends the video on a beat. Draw code reads the same grid: `s.onBeat(i)`, `s.nextBeat(t)`, `s.pulse()`.
- **Energy per scene** decides which layers play in each bar (each layer's `from`/`to`), so the arrangement builds the way you designed it: harmony → bass → groove → full kit.
- **The voice comes first.** While someone speaks, the bed dips 10 dB and the melody drops out. The melody plays *only in the gaps*, so a music-only beat (`narration: false, beats: 6`) gets a phrase of its own.
- **Section changes** get a short snare or tom fill and a crash on the downbeat, when the energy rises and the score has drums there.
- **A hit gets a breath.** A `hit` or `boom` effect silences the music for the half beat before it, which makes the hit land.
- **The ending resolves.** The tonic chord lands on the last downbeat that leaves at least 1 s to ring, played by the score's own instruments, and fades with the last frame.
