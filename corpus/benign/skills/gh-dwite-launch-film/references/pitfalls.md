# Pitfalls (each one cost a render)

## Rendering

- **One Node process driving many pages** bottlenecks on decoding screenshots (~7 fps at 540p). Run one process per
  worker, each with its own Chrome and ffmpeg (`render.mjs` does): ~37 output fps at 1080p60 with 4 samples on 12
  workers.
- **NaN from Infinity.** `inv(Infinity, Infinity + x, t)` is NaN; CSS ignores the invalid value and the element keeps
  whatever the previous frame set, so frames depend on render order. `inv()` guards Infinity and `set()` logs NaN;
  the renderer prints `[stage]` errors.
- **Random numbers in particles.** Draw every random value for a particle before any `continue`, or the sequence
  shifts with `t` and particles flicker. Precompute per-particle params at build time when possible.
- **CSS background images** may not be decoded at the first capture. Use `<img>` elements (decoded in `boot()`).
- **Hidden elements measure as zero.** `offsetLeft`/`getBoundingClientRect` inside a `display:none` scene return 0.
  Compute positions from constants.
- **3D flattening.** `opacity` or `filter` on an element with `transform-style: preserve-3d` flattens its children.
  Put `perspective` on the parent of the rotating element, set opacity only on that parent, and write the rotating
  element's transform directly (not through `set()`).
- **Big blur filters** on full-screen layers are slow; keep them to short exits.

## Audio

- **Generated intros** are often ~10 dB quieter than the body and can open with a second of silence. Users hear that
  as "big pauses". Measure (`analyze_music.py`), trim whole bars (`musicStart`, keeps the grid), lift the rest.
- **Stitched fragments sound like stutter.** Three separately generated pieces with gaps ("Once upon a time…" / "there
  was…" / 3 s / "your child.") read as a stumble even when each clip is clean. Generate one take and split it
  (`split`), keep gaps under ~1.5 s early on, or fill a gap with purposeful sound.
- **Overlapping voices become a murmur.** Names said every 0.2 s by different voices (clips ~0.5 s) were
  unintelligible; speech-to-text caught 2 of 9. Space them by at least one clip's speech length and re-time the
  picture to match.
- **TTS alignment timestamps are off by 0.1–0.3 s.** Measure word timings on the generated audio with speech-to-text
  and place by them (`gen_vo.py`).
- **ffmpeg `sidechaincompress` stops when the sidechain input ends**, cutting the score after the last voice. Pad the
  voice bus to the full length (`apad=whole_dur=`).
- **Loudness varies wildly** between generated files (−45 to −12 LUFS). Match each cue to its own target.
- **You cannot listen.** Verify with speech-to-text transcripts of the mix (words and times), per-second levels, and
  a spectrogram with cue markers. Say in the handoff that the audio is checked by measurement only.
- **ElevenLabs music:** `force_instrumental` only works with a plain `prompt`; composition plans use `chunks` on
  music_v2/v2.5 and `sections` on music_v1.
- **Lyria** is on the Interactions API (`/v1beta/interactions`), not `generateContent`.
- **Library voices** work by id in text-to-speech without adding them to the account, so no voice slot is used
  (matters when the product clones user voices on the same account).
- **A short name can come out garbled** in one voice ("Theo" → "Fail."). Speech-to-text every chorus clip and retry
  with another voice.

## Tooling

- zsh does not split `$var` into words (`set -- $spec` fails): use `${=var}` or a Python loop. A glob with no match
  aborts an `&&` chain.
- The Write tool refuses to overwrite a file changed since it was last read (for example after a `sed` edit): read
  it again first, or the old script runs silently.
- Keep keys in a `chmod 600` temp file or the environment and delete it at the end; never write them into the film
  folder.
