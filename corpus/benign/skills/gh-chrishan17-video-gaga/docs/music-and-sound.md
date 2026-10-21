# Music, sound & pacing

Every video gets a **score composed for it as one piece of music**, written note by note in a small module next to `video.html` (`score.mjs`). The runtime hands the module the film's timeline (the scenes, every spoken word with its time, the beat grid that the cuts and voice lines already sit on), and the module writes the piece. The renderer plays it on real instruments, ducks it under the voice, levels it and measures it.

The instruments are **real samples**: a General MIDI SoundFont (MuseScore General, MIT licence) rendered offline by [spessasynth_core](https://github.com/spessasus/spessasynth_core), for grand and felt piano, electric piano, strings, choir, guitars, harp, koto, mallets, basses, brass, winds and eight drum kits. The parts a score leans on most play from **multi-sampled recordings**: `piano` from the Salamander Grand Piano (Alexander Holm, CC BY 3.0: credit it when you deliver a video that uses it, e.g. *Piano: Salamander Grand Piano by Alexander Holm, CC BY 3.0*), and `felt`, `strings`, `sinepad`, `violin`, `cello` and `harp` from VSCO 2 Community Edition (CC0). Only the notes a score plays are downloaded, once, into `~/.cache/video-gaga/samples`; a part whose samples can't be fetched falls back to the SoundFont and `gaga music` says so (`VIDEO_GAGA_MULTISAMPLE=0` turns them off). The 40 MB SoundFont downloads once to `~/.cache/video-gaga` on the first render (`gaga doctor` fetches and checks it). It is seeded and deterministic: the same score renders the same audio every time. You can still bring a licensed track with `--music file.mp3`.

## 1. What a good score is

**Good**
- **It is a piece of music.** Played on its own, it could be released as a one-minute cue: an opening, a development, a lift, a climax and an ending that resolves. It has a theme someone could hum (a motif of two to four notes with its own rhythm) that is stated, answered, varied and brought back changed: the game tune returning on a music box at the end, the same four notes slower and lower at the low point.
- **It underscores the voice.** Most videos are narrated, so most of the score is accompaniment that moves: a bass line, a keys figure, a light groove, the harmony changing. The theme sings where the voice rests: the pre-roll, a music-only scene, after the last line. Under a sentence there is no tune competing with the words.
- **It meets the picture only where the story turns.** Three to five moments in a minute: the world changing (the drawing becomes a game, the band comes in), the turn (everything but the piano falls away), the one line the video is about, the last image (the final chord). Everywhere else the music follows its own phrases. The cuts already land on its beats; it does not need to answer each one.
- **It is played, not looped.** Every part has a feel (the bass and snare a few milliseconds behind, the shaker a little ahead, the off-eighths lightly swung); velocities rise and fall with the phrase; there are ghost notes; a figure has two or three versions that take turns, and now and then a note is left out; the voicing and the instruments change from section to section, so no stretch repeats exactly for 20–30 s.
- **The harmony has colour.** Beyond the four-chord loop: a iii, a ii–V, a secondary dominant (A7 in F) into the climax, a borrowed minor iv (B♭m6 in F) for the one moment that hurts, a held sus chord where the story asks a question.
- **There is space.** Each part keeps its own register (bass in octaves 1–2, chords in 3–4, the tune in 4–5); rhythms complement each other (when one part is on the beat, another is off it); a section where everything but one instrument drops out; drums only where the story moves, not by default.
- **Sound effects are few.** A sound effect is a physical thing on screen that would feel false in silence: a page turning, a door, the one impact. Many videos need none to four. They sit in the same room as the music and nothing in the score answers them.

**Not good**
- **Mickey-mousing:** an instrument hit for every jump, bump and button press, the band stopping before each one. It reads as forced. It belongs to a cartoon or a comedy whose brief asks for it, and even there only for the gags.
- **Wallpaper:** a one- or two-bar pattern repeated bar after bar, with parts switched on and off by scene; the same four chords (I–V–vi–IV or a rotation of it) from the first bar to the last.
- A tune fighting the voice; a drum kit under an intimate story because songs have drums; a sound effect on every element; a sound effect that copies what the music already says.
- A drone (pads or strings alone for long stretches), a low tom as the only pulse, slow minor chords drowned in reverb. These read as cheap or creepy (阴间).

**The reference.** Name what a music supervisor would license for this exact video ("Lena Raine's *Celeste*: felt piano under a chiptune lead", "Joe Hisaishi strings over a felt piano", "lo-fi hip hop with a dusty Rhodes", "bossa nova guitar and brushes", "Nils Frahm, a repeating piano figure that grows"). It comes from the story's feeling and the audience, not from the look or the subject: a video about running can be a lazy bossa nova. Say the score in one line in the brief: *feel in three words · reference · BPM key · the theme · the form, and the moments it meets the picture*.

## 2. Writing it: `music.script`

```js
CV.create({
  music: { bpm: 124, key: 'F', mode: 'major', script: 'score.mjs' },
  scenes: [ … ],
});
```

`bpm` sets the grid every cut and voice line snaps to; `key` and `mode` tell the sound effects and the checks which key the piece is in. Everything else is in `score.mjs`:

```js
// score.mjs: 《第一关》, 36 bars in F. Piano alone on the page; the band comes in when the
// drawing becomes a game (bar 6); the theme in full over the montage, where nobody speaks;
// back to the piano at the flag (bar 22); the theme comes home on a music box.
export default function score(S) {
  const THEME = ['C5:.5 F5 A5 G5 F5:1 C5:1', 'E5:.5 A5 C6 A5 G5:2', 'F5:.5 Bb5 D6 C6 Bb5:1 A5:1', 'G5:1.5 F5:.5 E5:1 C5:1'];
  // the page: the theme as a child might pick it out on the piano, before the first word
  S.line(S.at(0), 'felt', THEME[0], 0.11);
  S.chord(S.at(0), 'felt', ['F2', 'C3'], S.bar, 0.1);
  // …
  // the montage: the theme in full on the square lead, a secondary dominant on the second bar
  S.line(S.at(18), 'lead', 'C5:.5 F5 A5 G5 F5:1 C6:1 | C#6:1.5 A5:.5 E5:1 G5:1', 0.11, { bus: 'lead' });
  // …
  // the last chord on today's pencil stroke (a scene's sound effect is a cue time too)
  const stroke = S.event('clear', 'tick');
  S.chord(stroke, 'felt', ['F1', 'F2', 'C3', 'A4', 'C5', 'F5'], 2.2, 0.12, { strum: 0.02 });
}
```

Write the form first, as a list of bars against the scene timeline (`gaga music` prints the cut times; at 124 BPM a bar is 1.94 s), then the parts bar by bar. A helper of your own for a part that recurs (the piano's broken chords, the bass line, the kit) is fine; give it the variations the piece needs rather than one shape for every bar.

**`S`, the timeline:**

| | |
|---|---|
| `S.bpm`, `S.beat`, `S.bar`, `S.beatsPerBar`, `S.offset`, `S.duration`, `S.key`, `S.mode` | the grid (seconds) and the key |
| `S.at(bar, beat = 0)` · `S.barAt(t)` | bar *n*, beat *b* (from 0) in film seconds · which bar a time falls in |
| `S.grid(t, div = 1)` · `S.next(t, div = 1)` | the nearest / the next grid point (`div` in beats: 1, 0.5, 4 …) |
| `S.scenes`, `S.scene(id)` | `{ id, start, end, energy, voiced, words: [{ text, t, end }] }` in film seconds |
| `S.when(id, 'words')` · `S.whenEnd(id, 'words')` | when a phrase starts / ends in that scene's narration |
| `S.voice` · `S.speaking(t)` | the spans where someone speaks · whether someone speaks at `t` |
| `S.events` · `S.event(scene, type, i = 0)` | the scenes' sound effects and transition sounds, with their times |
| `S.random()` | seeded, so the same score renders the same take |

**`S`, the notes** (`t` in film seconds, `vel` 0..1 of the instrument's loudest):

| | |
|---|---|
| `S.note(t, inst, pitch, dur, vel, o)` | one note; `pitch` is `'C4'`, `'F#5'`, `'Bb3'` or a MIDI number |
| `S.chord(t, inst, pitches, dur, vel, o)` | several at once (`o.strum` s between them) |
| `S.line(t, inst, 'C5:.5 F5 A5 G5 F5:1 C5:1', vel, o)` | a written line (notation below); returns how long it lasts |
| `S.drum(name, t, vel, o)` | `kick snare clap snap rim hat openhat shaker tamb ride crash tom conga` (`o.pitch` Hz for a tom, `o.kit` a kit name) |
| `S.fx(type, t, o)` | a sound effect of §4 placed by the score (a riser into its own climax); `o.semi` tunes a recorded one |
| `S.hole(t0, t1, fade)` · `S.dip(t, dB, { attack, hold, release })` | silence the music (not the effects) from `t0` to `t1` · lower it for a moment |

Instruments (`inst`): **beds** `pad`, `synthpad`, `strings`, `sinepad`, `choir` · **keys** `piano`, `felt`, `epiano` / `keys` · **plucked** `guitar` / `pluck`, `acoustic`, `harp`, `koto`, `pizz` · **mallets** `bell` with `kind`: `glock`, `marimba`, `kalimba`, `celesta`, `vibes`, `musicbox`, `xylophone`, `tubular` · **melodic** `flute`, `shakuhachi`, `violin`, `cello`, `horn`, `brass`, `synthbrass`, `lead` (square; `kind: 'saw'`), `timpani` · **bass** `bass` with `kind`: `finger`, `picked`, `upright`, `fretless`, `synth`, `synth2`. Options in `o`: `kind`, `bright` 0..1, `attack`, `release`, `verb`, `echo`, `strum`, `decay`, `pan`; `bus: 'lead'` marks the tune (it steps further back while someone speaks), `tight: true` turns off the small human timing and touch every note otherwise gets.

**Line notation.** A note is a name with its octave (`C4` = middle C); `:beats` sets its length and carries over to the next notes (`:1/3` for triplets); `r` is a rest; `[A3 C4 E4]:2` a chord; `@1.2` accents a note; `|` checks that the bar is full. A line is played like a player would: its high points a little stronger, downbeats leaning, off-beats lighter.

**Limits** (refused or capped, so a score can't break the mix): `bpm` 60–150; a note's `vel` is capped per instrument (beds 0.12 · keys, plucked and mallets 0.2 · flute, violin, cello, horn, brass 0.15 · lead 0.12 · timpani 0.3 · bass 0.35 · kick 0.7 · snare 0.35 · clap and conga 0.3 · snap 0.25 · rim 0.2 · crash 0.15 · hat, shaker, tamb, ride 0.12 · openhat 0.1 · tom 0.5); an unknown instrument, drum, effect, scene or phrase is an error that names what exists. The mix is levelled against the voice afterwards; the caps keep one part from swamping the others.

`gaga music <project>` renders the score on its own and prints the mix by part, the listening checks (§6), every sound effect and the cut times; `gaga render` renders it into the video. A scene whose cut should land on a bar line (a new section starting with a new picture) gets `snap: 'bar'`.

[music-spec.md](music-spec.md) has the older pattern spec (`layers`, `lead`, `parts`), which the preset example videos still use.

## 3. How the score sits with the video

- **One clock.** The runtime moves every cut so that the middle of the transition lands on a beat, starts each voice line on an eighth note, and ends the video on a beat. Draw code reads the same grid: `s.onBeat(i)`, `s.nextBeat(t)`, `s.pulse()`.
- **The voice comes first.** While someone speaks, the score dips 10 dB and a part marked `bus: 'lead'` a further 12 dB; sound effects dip 2 dB. Write for it: the theme where the voice rests, accompaniment under it.
- **The ending is yours.** The last frame lands on a beat; write the final chord there (or on the last image's moment) and let it ring. The mix fades with the last frame.

## 4. Sound effects

Transitions make their natural sound automatically (see the table in [runtime-api.md](runtime-api.md#transitions); `sfx: false` on a transition, or `music.sfx: false` for all of them, keeps them quiet). Add others per scene:

```js
sfx: [
  { at: 'ten thousand', type: 'tick' },          // when the phrase is spoken
  { at: 2.4, type: 'hit' },                      // local seconds
  { at: (s) => s.onBeat(2), type: 'shimmer' },   // computed from the scene (beats, word times)
  { at: (s) => s.when('Orbit'), type: 'riser', dur: 1.5 },  // a riser *ends* at its time
]
```

| Type | Sound | Use for |
|---|---|---|
| `whoosh` / `swish` | air past the camera: two bands of noise sweeping across the stereo field (swish is shorter and softer) | pushes, whips, wipes |
| `hit` | a big kick, a timpani on the tonic, a crash and a sub; the music breathes before it | the one big reveal per video |
| `boom` | a concert bass drum and a deep sub drop | a title slam, a dramatic number |
| `riser` | a reversed cymbal and noise opening up, ending at `at` | building into a hit |
| `swell` | a soft reversed cymbal | ink, dissolve, gentle reveals |
| `tick` / `click` | a small mechanical switch / a mouse click (recorded) | markers popping, counters, list items |
| `pop` | a small light object set down: a soft clack (recorded) | a result landing, a badge appearing |
| `shimmer` | a quick celesta arpeggio of the current chord | light, sparkle, a positive payoff |
| `chime` | two glockenspiel notes, the fifth then the octave | an end card, a notification |
| `paper` | a page turning, a sheet sliding (recorded) | page transitions |
| `type` | a key press (recorded) | typewriter text (one per character burst, not per letter) |
| `card` · `book` · `cloth` | a card laid down · a book closed or set down · fabric moving (recorded) | cards dealt, a chapter closing, a reveal |
| `wood` · `glass` · `metal` | a light knock or tap on that material (recorded) | an object or icon that *is* that material |
| `thud` · `step` | something solid landing · a footstep (recorded) | a heavy block settling, someone arriving |
| `glitch` | stuttered digital bursts | glitch transitions, cyber styles only |

The small physical sounds are real recordings (Kenney, CC0; `assets/sfx`), a few takes of each, picked in turn with a little change of pitch and level, so ten ticks never sound copied. Every effect sends to the score's one reverb, so effects and music sit in the same room. A synthesized beep or a pure sine "tick" reads as cheap; a real object in the room reads as made.

**Each one is a thing on screen that would feel false in silence,** and most videos need none to four (§1). A transition between two pages may turn a page; a cut does not need a whoosh. A `hit` is strongest when it is the only one in the video, and the score does not answer the effects: the music keeps its own phrase.

## 5. Pacing: let it breathe

Narration doesn't need to run without a break. Plan the silence the way you plan the shots:

| Moment | How | Why |
|---|---|---|
| **Pre-roll** | `voiceDelay` of 1–2 bars on the first scene | the music and the first visual set the tone before anyone talks |
| **Breath before the payoff** | a `narration: false` scene with `beats: 4–8`, or a long `tail` | a result needs a moment to sink in; the melody fills it |
| **Music-only montage** | 2–4 short `beats: 2` scenes cut on the beat | rhythm carries a list better than reading it out |
| **End card** | `tail: 1.5–2.5` on the last scene | the final chord resolves under the logo |

A 30 s explainer typically carries 20–24 s of speech. A 15 s teaser might have only 6–8 s.

## 6. Mix and verification

`gaga render` reports the balance from separate voice and music stems:

```
a/v sync: 4 cue onsets vs speech onsets — median 93 ms, worst 96 ms
music: 13.8 dB under the voice while it speaks, -3.9 dB vs the voice in the gaps
```

Aim for **10–18 dB under the voice** while it speaks (it warns below 9 and above 22 dB) and roughly −2 to −6 dB in the gaps. The score is levelled against the measured speech RMS of your narration, so the defaults land there for any voice. Adjust with `music.volume`, `music.gap` and `music.duck`. Word-synced sound effects are excluded from the measurement (it uses a bed-only stem, `build/music-bed.wav`). The final mix is loudness-normalised to −16 LUFS. Speech onsets are measured on the voice stem, so the sync check still works under music.

**Listening checks.** `gaga music` and `gaga render` also measure what a listener would notice, from the rendered audio, and warn (never refuse):

| Check | Measured | Reads well | Warned |
|---|---|---|---|
| ghost | per 4 bars: note starts per beat, share of held notes, reverb tail vs the dry sound | something articulates at least once a beat, or the reverb sits well back | < 1 start per beat **and** > 60 % held **and** a tail within 12 dB: the slow, washed-out, unresolved sound people call eerie (阴间) |
| melody | the tune (notes with `bus: 'lead'`) vs the other parts in 500 Hz–4 kHz while it plays | ≥ 3 dB above them | below 3 dB: it gets lost |
| range | loudness range of the music before ducking (3 s windows) | it rises and falls with the story | under 3 LU when the scenes' `energy` spans ≥ 0.3: the score stays flat |
| sfx | each effect's loudest 25 ms vs the music around it, in its band | +3 to +10 dB | under −6 dB (lost) or over +18 dB (jumps out; accents like `hit` excepted) |

The numbers are printed on the `listen:` line. They catch the common failures; they don't replace ears.

**The 8-second listen.** Whoever builds the video can't hear it. Before calling a score done, ask a person to listen to 8 seconds around the video's key mood change (the turn, the reveal) and say in a word how it feels and what is off (a sound that's too loud, a melody that's wrong, an effect that's cheap). Their answer beats every number above.

**Honest limits.** The instruments are real samples, so the score can sound like a well-produced library cue rather than a toy synth, but it is written by someone who cannot hear it: it won't match a composer's track or a commercial hit. The renderer verifies what it can measure (levels, ducking, mix balance, sync, peaks, every cut on the grid) but cannot judge taste: read the `mix:` line and the warnings, and write the score as carefully as the pictures. For a flagship piece, use the written score as the tempo map and swap in a licensed track with the same BPM: `--music track.mp3` plus `music: { bpm: <its bpm>, offset: <first downbeat s> }`.
