# Sounds

Everything here is synthesised by `engine/sfx.py` and `engine/music.py`: no
samples, nothing to license. Listen to any of them from the links (the MP3s
are rendered by `node engine/make.mjs gallery`).

## Music styles

Set once for the video: `"music": { "style": "lofi" }`. Tempo defaults to the
style's own (override with `bpm`), key to C (`"key": "D"`), chords to
`["C", "Am", "F", "G"]` (`progression`, written in C, transposed to the key).
Each demo plays the five moods in order: tension, calm, groove, run, outro.

| Style | Default bpm | Sound and when to use it | Demo |
|---|---|---|---|
| `playful` | 100 | Marimba riff, punchy kick, claps, bouncy bass. Cartoons, kids, food, light promos. | [▶ listen](sounds/music-playful.mp3) |
| `lofi` | 80 | Soft swung drums, warm electric-piano 7ths, sub bass, vinyl crackle. Calm explainers, study, lifestyle. | [▶ listen](sounds/music-lofi.mp3) |
| `upbeat` | 118 | Four-on-the-floor, plucked arpeggios, off-beat bass, sidechain pump. Launches, sports, energy. | [▶ listen](sounds/music-upbeat.mp3) |
| `cinematic` | 90 | Taiko drums, strings, bells. Trailers, big reveals, serious topics. | [▶ listen](sounds/music-cinematic.mp3) |
| `chiptune` | 128 | 8-bit squares and noise drums. Games, tech, retro, nerdy humour. | [▶ listen](sounds/music-chiptune.mp3) |
| `tropical` | 102 | Steel drums, shaker, syncopated rim. Travel, summer, food. | [▶ listen](sounds/music-tropical.mp3) |
| `corporate` | 110 | Soft kick, shaker, piano eighths, plucks. B2B, product tours, how-tos. | [▶ listen](sounds/music-corporate.mp3) |
| `ambient` | 72 | Pads and bells, no drums. Wellness, meditation, gentle stories. | [▶ listen](sounds/music-ambient.mp3) |

Per scene, `"mood"` picks what plays: `tension`, `calm`, `groove`, `run`
(groove without the lead), `outro`, or `none` (silence). Defaults: pileup
tension, title and fan calm, card and list groove, grid run, logo outro.

Your own music instead: `"music": { "file": "music/track.mp3", "volume": 0.5 }`.
It is looped if too short, faded at the end, and ducked under voices like the
synthesised music. Only use tracks you have the rights to.

## Sound effects

Scenes already play fitting effects on their own (cards thud, bubbles bloop,
lists whoosh, grids play a marimba run, logos end on a ta-da). Add more with a
scene's `sounds`, timed like everything else, in seconds or on a spoken word:

```json
"sounds": [
  { "at": "fuzz", "kind": "squeak" },
  { "at": 1.2, "kind": "whoosh", "dur": 0.6, "gain": 0.8 },
  { "at": "Squeeze", "kind": "water", "pitch": 1.2 },
  { "at": "reveal:end", "file": "sounds/my-own-hit.wav" }
]
```

`gain` scales the effect's default level, `pitch` shifts it (1 = normal).
`"autoSfx": false` on a scene (or the whole story) keeps only the sounds you
place; `"music": { "sfx": false }` silences every effect.

| Kind | What it is | Parameters | Hear it |
|---|---|---|---|
| `pop` | Bubbly pop: things appearing | pitch | [▶ listen](sounds/sfx-pop.mp3) |
| `click` | UI click | pitch | [▶ listen](sounds/sfx-click.mp3) |
| `tap` | Soft tap, a finger on glass | pitch | [▶ listen](sounds/sfx-tap.mp3) |
| `tick` | Tiny tick, letters landing | pitch | [▶ listen](sounds/sfx-tick.mp3) |
| `blip` | Rising blip, a badge or an idea | pitch | [▶ listen](sounds/sfx-blip.mp3) |
| `bubble` | Speech-bubble bloop | pitch | [▶ listen](sounds/sfx-bubble.mp3) |
| `ding` | Phone notification, two tones | pitch | [▶ listen](sounds/sfx-ding.mp3) |
| `tritone` | Three-note message tone | pitch | [▶ listen](sounds/sfx-tritone.mp3) |
| `chime` | Success chime, rising bells | pitch | [▶ listen](sounds/sfx-chime.mp3) |
| `bell` | Single bell strike | pitch | [▶ listen](sounds/sfx-bell.mp3) |
| `error` | Soft error buzz | pitch | [▶ listen](sounds/sfx-error.mp3) |
| `coin` | Game coin | pitch | [▶ listen](sounds/sfx-coin.mp3) |
| `cash` | Cha-ching cash register | pitch | [▶ listen](sounds/sfx-cash.mp3) |
| `whoosh` | Air sweep, a transition (dur) | dur pitch | [▶ listen](sounds/sfx-whoosh.mp3) |
| `swoosh` | Short fast whoosh | pitch | [▶ listen](sounds/sfx-swoosh.mp3) |
| `swipe` | Very short swipe | pitch | [▶ listen](sounds/sfx-swipe.mp3) |
| `whip` | Whip crack, a snappy cut | pitch | [▶ listen](sounds/sfx-whip.mp3) |
| `rise` | Riser before a reveal (dur; place it to end on the hit) | dur pitch | [▶ listen](sounds/sfx-rise.mp3) |
| `impact` | Deep boom hit | pitch | [▶ listen](sounds/sfx-impact.mp3) |
| `drop` | Bass drop | pitch | [▶ listen](sounds/sfx-drop.mp3) |
| `thud` | Card landing | pitch | [▶ listen](sounds/sfx-thud.mp3) |
| `slam` | Sticker slam | pitch | [▶ listen](sounds/sfx-slam.mp3) |
| `boing` | Cartoon spring boing | pitch | [▶ listen](sounds/sfx-boing.mp3) |
| `spring` | Quick twang | pitch | [▶ listen](sounds/sfx-spring.mp3) |
| `squeak` | Rubber squeak | pitch | [▶ listen](sounds/sfx-squeak.mp3) |
| `slide` | Slide whistle (from, to in Hz; dur) | from to dur | [▶ listen](sounds/sfx-slide.mp3) |
| `zap` | Laser zap | pitch | [▶ listen](sounds/sfx-zap.mp3) |
| `glitch` | Digital glitch stutter | pitch | [▶ listen](sounds/sfx-glitch.mp3) |
| `typing` | Keyboard typing burst (dur) | dur pitch | [▶ listen](sounds/sfx-typing.mp3) |
| `shutter` | Camera shutter | pitch | [▶ listen](sounds/sfx-shutter.mp3) |
| `scratch` | Record scratch, a comic stop | pitch | [▶ listen](sounds/sfx-scratch.mp3) |
| `heartbeat` | Heartbeat, suspense | pitch | [▶ listen](sounds/sfx-heartbeat.mp3) |
| `clock` | Tick-tock | pitch | [▶ listen](sounds/sfx-clock.mp3) |
| `drumroll` | Snare roll building up (dur) | dur pitch | [▶ listen](sounds/sfx-drumroll.mp3) |
| `crash` | Cymbal crash | pitch | [▶ listen](sounds/sfx-crash.mp3) |
| `sparkle` | Twinkles, confetti | pitch | [▶ listen](sounds/sfx-sparkle.mp3) |
| `magic` | Harp glissando with sparkles | pitch | [▶ listen](sounds/sfx-magic.mp3) |
| `breath` | Soft exhale, calm | pitch | [▶ listen](sounds/sfx-breath.mp3) |
| `water` | Water drop | pitch | [▶ listen](sounds/sfx-water.mp3) |
| `tada` | Fanfare chord: the big finish | pitch | [▶ listen](sounds/sfx-tada.mp3) |
| `clap` | Hand clap | pitch | [▶ listen](sounds/sfx-clap.mp3) |
| `marimba` | Marimba note (semis from the key's middle C) | semis | [▶ listen](sounds/sfx-marimba.mp3) |
| `pluck` | Plucked string note (semis) | semis | [▶ listen](sounds/sfx-pluck.mp3) |

Tips: a `rise` should end on the moment it leads to, so start it `dur` seconds
earlier; `impact`, `drop` and `crash` are big, so use one per video; keep
effects under voices sparse, since the music ducks but effects do not
completely.
