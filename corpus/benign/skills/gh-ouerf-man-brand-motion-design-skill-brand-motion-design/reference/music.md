# Music: a grid first, then cuts, then every hit on its frame

Everything runs with `uv` (no system Python packages): `uv run --with numpy [--with imageio-ffmpeg] python3 <skill>/scripts/...`. Keep audio under `videos/<film>/assets/audio/`; gitignore licensed tracks and write their source and license in `cues.js` (`music.license`).

## Path A: their licensed track

### 1. The grid: `scripts/beats.py`

```bash
uv run --with numpy --with imageio-ffmpeg python3 <skill>/scripts/beats.py \
  --drums assets/audio/licensed/stems/drums.mp3 \
  --stem bass=assets/audio/licensed/stems/bass.mp3 \
  --stem melody=assets/audio/licensed/stems/melody.mp3 \
  --out assets/audio/beats.json
```

- No stems? Pass the full mix as `--drums`. Known tempo? Pass `--bpm`.
- Tempo comes from autocorrelation refined by a comb; phase is the comb's best offset; the downbeat is where stems come and go.
- Check `gridCheckMs.spread` (under 10 ms is good). Then check the phase: on a full mix with busy off-beat hats the comb can lock half a beat late. Compare `firstBeat` with a kick you can see in a waveform, and listen once with a click on the grid.

### 2. The song map

Print each stem's loudness per bar (`beats.json` → `bars[].loudnessDb`) and read the structure: intro, drops, breakdowns, big hits, outro. Map the story onto it: the hello on a sparse bar, the first punchlines where the drums come in, the busy feature scenes on the full groove, the strongest moment on the drop, the headline where the bass drops out, home on the ring-out.

### 3. The edit: `scripts/audio-edit.py`

```json
{
  "source": "assets/audio/licensed/song.mp3",
  "out": "assets/audio/edit.wav",
  "bpm": 150,
  "firstDownbeat": 1.2516,
  "segments": [
    { "fromBar": 1, "toBar": 17, "why": "intro, shortened" },
    { "fromBar": 36, "toBar": 49, "why": "the drop" }
  ],
  "duration": 52.8,
  "fadeOutSeconds": 1.2
}
```

- `toBar` is exclusive; the film's bars are the segments back to back, so the grid runs straight through every join (5 ms fades, no clicks).
- Film length = a whole number of bars (plus an optional ring-out). The film's grid starts at 0 on a downbeat: `grid: { bpm, firstBeat: 0, pickupBeats: 0 }` in `cues.js`.
- Cut slow intros short: viewers leave in the first two seconds.

## Path B: no track, a generated royalty-free bed

```bash
# the default: a hip-hop / trap bed for a showreel cut (12 bars at 140 BPM is about 20.6 s)
uv run --with numpy python3 <skill>/scripts/synth.py music --out assets/audio/bed.wav \
  --style trap --bpm 140 --bars 12 --key F --mode minor --progression "i VI VII v" \
  --energy 123333332210 --hits "3 5 7 9" --risers "5" --gaps "5" --tail 0
```

- The grid is exact (nothing to detect): paste `bed.grid.json` into `cues.js`.
- `--energy` is one digit per bar, written from the beat sheet: `0` pad only, `1` + plucked arpeggio, `2` + soft kick and hats, `3` + bass and backbeat. Calm under the hook, full under the strongest moment, down for the headline, `0` for the ring-out.
- Tempo: 135 to 150 trap (the default, young audiences), 120 to 128 punchy electronic (launches, B2B). 90 to 110 `--style soft` only for an explainer the user asked to be calm.
- Hip-hop / trap for a young audience: `--style trap --bpm 140` (808s with glides that phone speakers can play, a half-time clap on beat 3, hat rolls into every other bar, dark FM bells; energy 1 is bells and hats only, a good first bar). Minor keys and progressions like `"i VI VII v"` sound right.
- Punchy electronic: `--style punchy` (harder kick with a click, claps, sixteenth hats, the pads pumping under the kick), `--hits "2 5 8"` (a sub drop and crash on those downbeats), `--risers "5"` (a riser filling the bar before bar 5), `--gaps "5"` (half a beat of silence before it). Put the hits where the picture changes hardest. Major keys read confident; `--mode dorian` reads cool.
- Generated from sine partials and noise, no samples: the output is yours to publish. It is a bed, not a hit; offer it when the user has no track, and say so.

## Sound effects

```bash
uv run --with numpy python3 <skill>/scripts/synth.py sfx --out assets/audio/sfx
```

- Writes `click tick pop whoosh ping chime thud` and `peaks.json` (seconds to each file's loudest sample). Or bring licensed effects and measure their peaks the same way.
- Short, dry, quiet (volume 0.2 to 0.45). The music leads. One sound per meaningful event: the landing, the click, the proof, the drop. Not every animation.
- Put them on the events in `cues.js` (`sfx: "ping", volume: 0.4`), then:

```bash
node <skill>/scripts/place-audio.mjs videos/<film>
```

It writes the `<audio>` tags between `<!-- pf:audio -->` markers: the music on its own track, each effect at `cue - peak` so the transient lands on the frame, with its real duration, packed onto tracks where nothing overlaps. Re-run it after every cue change.

## Loudness

Social platforms normalize to about -14 LUFS; aim there with a true peak under -1 dBTP. `verify.py` measures both on the final file. If effects poke out, lower their `volume` in `cues.js` rather than the music.
