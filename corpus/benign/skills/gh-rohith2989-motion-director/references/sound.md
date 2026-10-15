# Sound — composed for this film, caused by the picture

Half of "premium" is sound. Everything here is synthesized from first principles (`audio/synth.py`: band-
limited oscillators, a zero-delay-feedback filter, FM, modal resonators, Karplus-Strong, convolution reverbs
from synthesized impulse responses) — no stock music, no sample packs.

## What got rejected (so you don't repeat it)
- **"CoComelon music"**: major-key glass bells, a cute 3-note bell motif, tuned glass ticks on every UI event.
- **Lame whooshes**: filtered-noise swooshes on transitions.
- **Cartoon SFX**: bloops, boings, sparkles, bouncy mascots with matching sounds.
- **Generic SFX** that could be in any video. Every sound must be *this* product's sound.
What replaced them and was accepted: minor/Dorian electronic scores (deep house for launches, a warm ducked
bed under a voice), dry tactile UI sounds (wooden-case keyboard thock, real clicks, felt ticks, mechanical
latches, paper landing on felt), tonal transitions (reversed chord blooms, pure glides, sub impacts).

## Scoring on the grid (`audio/score.py` + `audio/score_plan.json`)
1. **Choose the BPM so sections land on bars.** At 120 BPM a bar is 2 s; at 100 BPM 2.4 s. Set
   `config.bpm` and `gridOffset` so the picture's section starts are `bar(n)`.
2. **Key and loop.** Premium-safe: D minor 9 loop `Dm9 | Bbmaj9 | Gm9 | A7sus4`; warmer:
   `Dm9 | Bbmaj7 | Fmaj9 | Cadd9` resolving to `Fmaj9`; voicings keep colour tones high and roots low.
3. **Arrange by energy, section by section** (`sections`): title = filtered groove (`lpf` sweep 450→3600 Hz) →
   product = FULL groove (kick, off-beat bass, ep stabs, hats, shaker) → features = groove + hook →
   trust/thoughtful = breakdown (drums out, pad, drone, slow filtered arp) → big wall/climax = FULL + open hat +
   hook → kicker line = bed only → CTA/lockup = FULL for one phrase, then the last chord.
4. **Transitions are musical**: `rises` (tonal riser into a downbeat), `impacts` (sub on the downbeat),
   `blooms` (reversed chord arriving on a downbeat), `hits` (struck chord + sub under a title word).
5. **The ending**: `end` = last chord (e-piano + pad bloom + sub) under the lockup, then a 3-note figure; the
   lockup's own sound (`lockup` cue) a beat after. Fade the last 1–2 s.
6. **Sidechain** bass/keys/pads to the kick (built in). Let the bed breathe; never wall-to-wall.

Presets: **launch** `style:"house"` 120–124 BPM · **onboarding / under a voice** `style:"bed"` 96–104 BPM
(pad + soft ep + pulse, no kick until the payoff) · **explainer** `style:"halftime"` 90–100 BPM · **teaser**
house 124 with one drop at the reveal · **logo sting** one chord + `lockup_mark`/`sonic_logo`.

## Sound effects (`audio/sfx.py`, mapped in `audio/mix.py: SFX`)
| Cue type | Recipe | Level (dB) | Rule |
|---|---|---|---|
| `key` / `key_enter` | `wood_key` (space/tab heavy) | −19 / −15 | wooden-case mechanical thock; 14–20 cps |
| `click` | `mouse_click` (press + release) | −13 | every visible click, 4 ms early |
| `tap`, `tick` | `soft_tap`, `felt_tick` | −18 | menus, list items, highlights — dry, unpitched |
| `relay` | `relay` | −22 | fast sequences: bars growing, counters |
| `lock` / `done` | `lock` (latch + clunk) | −15 / −17 | connected, approved, step complete |
| `tock` | `tock` | −15 | a message landing, a ✓ settling |
| `open` | `drawer` | −16 | a panel/sources/menu opening |
| `file` / `paper` | `file_land` / `paper` | −13 | a file arriving, a page set down |
| `flip` / `flap` | `card_flip` / `flap` | −19 / −14 | cards turning, split-flap words |
| `denied` | `denied` | −13 | a refusal |
| `panel` | `landing` (+0.95 s) | −15 | a slide-over landing — no air, no whoosh |
| `window_in` | `settle` (+0.55 s) | −17 | an app window arriving |
| `glide` | `tonal_glide` | −18 | a transition that needs motion in sound |
| `impact` | `brake` | −12 | once or twice per film |
| `lockup` | `lockup_mark` | −11 | the logo landing |
Unknown cue types are reported by `mix.py` — give them a sound or add them to `SILENT`. User-supplied real
sounds (e.g. Slack's notification when Slack notifies on screen): put the file in `audio/assets/` and cue with
`{file: "knock.wav", gain: -15}`.

## Mixing and mastering (`audio/mix.py`)
- **Voice** (if any): HPF 75 Hz, +1.2 dB low shelf at 160 Hz (warmth), −1 dB at 260 Hz (box), +1.8 dB at
  3.6 kHz (presence), +2 dB air shelf at 9 kHz, RMS compressor 2.4:1, split-band de-esser above 5.2 kHz,
  a breath of plate (7 %). Voice to −17 LUFS before the master.
- **Bed under a voice**: −21 LUFS unducked, ducked 7 dB while speech is present (60 ms attack, 450 ms release,
  gaps < 0.5 s held) — the music stays audible (≈10 dB under the voice), never fights it.
- **Typing**: the bed dips 3.5 dB under dense typing.
- **Effects**: quiet but audible — a room reverb (12 %) so they sit in the music's space.
- **Master**: −14 LUFS integrated (web/social), true peak ≤ −1.5 dBTP (lookahead limiter iterated), last
  1–2 s faded. Check with `python audio/analyze.py audio/out/mix.wav out.png` (LUFS, true peak, clicks,
  spectrogram, short-term loudness) and `python review/listen.py audio/out/mix.wav`.
- Measured once, fixed for good: a first-pass bed sat 16 dB under the voice and effects 29 dB under — nobody
  could hear them. Measure stems in 3 s windows; the bed should be 8–12 dB under speech.

## Editing sound with picture
Section boundaries are bar lines, so cuts land musically. For a cutdown, never splice the mix — regenerate
the score on the new timeline (same plan, remapped bars, drop the transitions that led into removed sections)
and remap the cues; verify the join for clicks and level steps.
