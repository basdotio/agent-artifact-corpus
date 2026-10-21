# Narration (Edge TTS) & subtitles

video-gaga narrates with Microsoft Edge's online neural voices through [rany2/edge-tts](https://github.com/rany2/edge-tts). It is free, needs no API key, and offers 300+ voices with word-level timestamps. The voice **drives the timeline**: every scene lasts as long as its line needs, and every visual hit can be pinned to the word that motivates it.

## 1. How it works

1. You write `narration.json` next to `video.html`, with one segment per scene (`id` = scene id).
2. `gaga render` (or `gaga tts`) runs `scripts/tts.py` for each segment via the edge-tts Python API with `boundary="WordBoundary"`.
   - edge-tts ≥ 7.0 defaults to **SentenceBoundary**, and its CLI has no switch for this, which is why we use the API.
   - The audio is `audio-24khz-48kbitrate-mono-mp3` (CBR), so **duration = bytes × 8 / 48000**. That is the exact clip length, with no ffprobe needed. Clips end with 0.4–1.1 s of silence, so the timeline uses the **last word's end** (+0.25 s for the final syllable to decay) as the end of speech, not the clip length.
   - Word offsets and durations arrive in 100-ns ticks (÷ 10,000,000 for seconds).
   - Results are cached per segment by a hash of (text, voice, rate, pitch, volume).
3. `build/narration.js` sets `window.CV_NARRATION`. The runtime places each scene: `start → +voiceDelay → speech (to the last word, +0.25 s for its final syllable to decay) → +tail`, with transitions overlapping. The clip's trailing silence simply plays under whatever comes next.
4. The renderer mixes the clips at their exact start times (`adelay` + `amix`) with the generated score (already arranged around the voice, see [music-and-sound.md](music-and-sound.md)) or a side-chain-ducked licensed track, applies `loudnorm` to −16 LUFS, and muxes AAC.
5. Captions are built from the same word timings: burned in on the canvas, and written as `.srt` and `.vtt`.

To voice the whole script in **one take** instead (a narrator, a cloned voice, a recording) and let the scenes follow it, see §7.

```json
{
  "voice": "zh-CN-YunxiNeural",
  "rate": "+4%", "pitch": "+0Hz", "volume": "+0%",
  "lang": "zh-CN",
  "segments": [
    { "id": "hook", "text": "每年多赚 8%，三十年后会怎样？" },
    { "id": "rule", "text": "七十二法则：七十二除以收益率，就是翻倍的年数。", "rate": "+8%" }
  ]
}
```

Per-segment `voice`, `rate`, `pitch` and `volume` override the defaults, so you can alternate two voices for a dialogue.

**Several voices in a row.** A scene has one clip. For a run of voices (a dialogue, the same word in six accents, one phrase per language), make one short scene per clip and join them with `cut` transitions over an identical layout. The cuts are invisible and every clip is pinned exactly. Keep `voiceDelay` and `tail` small (≈ 0.06–0.12 s) so the run keeps its rhythm.

**Word granularity.** English gives one event per word. Chinese voices return **segmented words** (for example `画布 / 就 / 是 / 你 / 的 / 摄影棚`). Punctuation is never included, and the runtime re-aligns the words to your original text to recover it. `s.when('摄影棚')` works on any contiguous run of words, and on a substring inside a single word.

## 2. Picking a voice

List them all with `node scripts/gaga.mjs voices --lang zh-CN`. These are tested and recommended:

| Locale | Voice | Gender | Character (Microsoft tags) | Good for |
|---|---|---|---|---|
| zh-CN | **XiaoxiaoNeural** | F | Warm · News, Novel | Explainers, education, friendly brand (default F) |
| zh-CN | **YunxiNeural** | M | Lively, Sunshine · Novel | Knowledge, tech, general narration (default M) |
| zh-CN | YunyangNeural | M | Professional, Reliable · News | Corporate, news-style, finance |
| zh-CN | YunjianNeural | M | Passion · Sports | Hype, trailers, events, sports |
| zh-CN | XiaoyiNeural | F | Lively · Cartoon | Playful, kids, social |
| zh-CN | YunxiaNeural | M | Cute · Cartoon | Kids, animation |
| zh-TW | HsiaoChenNeural / YunJheNeural | F / M | Friendly | Taiwan Mandarin |
| zh-HK | HiuMaanNeural / WanLungNeural | F / M | Friendly | Cantonese |
| en-US | **AndrewNeural** | M | Warm, Confident, Authentic | Launches, product, keynote (default EN) |
| en-US | **AvaNeural** | F | Expressive, Caring, Friendly | Explainers, onboarding |
| en-US | EmmaNeural | F | Cheerful, Clear | Tutorials, social |
| en-US | BrianNeural | M | Approachable, Casual | Casual explainers, devrel |
| en-US | ChristopherNeural | M | Reliable, Authority | Corporate, documentary |
| en-US | AriaNeural / JennyNeural / GuyNeural | F / F / M | News, General | Classic neutral narration |
| en-US | *MultilingualNeural variants* | | same personas | Mixed-language scripts |
| en-GB | SoniaNeural / RyanNeural | F / M | Friendly | British English |
| en-AU | NatashaNeural / WilliamMultilingualNeural | F / M | Friendly | Australian English |
| en-IN | NeerjaNeural / PrabhatNeural | F / M | Friendly | Indian English |
| en-IE | EmilyNeural / ConnorNeural | F / M | Friendly | Irish English |
| en-ZA | LeahNeural / LukeNeural | F / M | Friendly | South African English |
| ko-KR | SunHiNeural / InJoonNeural | F / M | Friendly | Korean |
| ja-JP | NanamiNeural / KeitaNeural | F / M | Friendly | Japanese |

**Rate.** `+0%` is natural. Use `+4…+10%` for social and tight edits, and `−5…−10%` for calm, premium or keynote. Beyond ±15% it sounds processed, so cut words instead.

## 3. Writing for the ear

- **One sentence per scene, 1–2 clauses.** Scenes live on the voice; long lines make long, static scenes.
- **Don't fill every second.** Leave a music-only pre-roll, a held beat before the payoff and an end card that rings out. The voice lands harder after a pause. With music on, every line starts on an eighth note of the beat grid.
- **Front-load the subject**, and end on the payoff word, which is where the visual hit goes.
- **Numbers.** Write what should be *seen* in captions. Edge reads `8%` as 百分之八 and `2026` correctly. Spell out anything ambiguous (`10.24` → 十月二十四日 in the voice line, while the on-screen graphic shows `10.24`).
- **Punctuation = pauses.** `，` ≈ 150–250 ms, `。？！` ≈ 300–500 ms. Use them to shape rhythm and to give animations room.
- **Chinese text:** avoid half-width commas and full stops between Chinese words, or the caption builder may misjudge sentence ends. Put a space between Latin words and Chinese (`按 8% 复利`) for clean captions.
- Custom SSML is **not** supported by the service (only a single `<voice><prosody>`). Control delivery with rate, pitch and punctuation.

## 4. Subtitles

The cue builder (`CV.subtitles.build`) breaks captions like a subtitle editor would:

1. Break at sentence ends (`。！？.!?`), at clause marks (`，、；：,;:`) once the cue has ≥ `minChars`, and at speech pauses > 0.55 s.
2. A phrase longer than `maxChars` is split into **balanced** chunks at word boundaries, with no single-word orphans.
3. Display text comes from *your* script (the TTS words are aligned back to it), so names, casing and symbols are preserved.
4. For Chinese, `，。；：` become spaces, `？！` are kept, and there is no trailing full stop. For English, punctuation is kept.
5. Timing: cue start = first word start. End = last word end + 120 ms, at least 0.8 s long, and never overlapping the next cue.

Defaults: CJK 18 characters (16:9) or 12 (9:16). English 42 or 28. Override them with `subtitles: { maxChars, minChars, punctuation }`.

### Per scene (`scene.captions`)

| Value | Result |
|---|---|
| `true` (default) | Cues are burned (with `--subs burn`) and written to .srt/.vtt |
| `'file'` | In .srt/.vtt only, never burned. Use it when the line is already on screen as type (a title question, a tagline), or when the picture shows what is said |
| `false` | No cue at all (sound effects, sung or non-verbal clips) |

### Styles (`subtitles.style`)

| Look | Settings |
|---|---|
| Box (explainers, brand) | `box: 'rgba(29,36,51,.9)', color: '#F3EFE6'` |
| Outline (over busy footage and colour) | `box: null, stroke: '#000', strokeWidth: 10` |
| Karaoke (social verticals) | `highlight: '#00E5FF'` + outline. Single-line cues only |
| Position | `y` = baseline as a fraction of height (0.9 for 16:9, 0.78–0.8 for 9:16) |

### Output modes (`gaga render --subs …`)

| Mode | Result |
|---|---|
| `file` (default) | `out/<name>.srt` + `.vtt` next to the MP4 |
| `burn` | Drawn into the frames with the preset's typography, plus the files |
| `soft` | An MP4 `mov_text` track (players can toggle it), plus the files |
| `burn+soft` | Both |
| `none` | No captions |

Why canvas burn-in instead of ffmpeg's `subtitles` filter: it needs a libass build (many ffmpeg installs, including Homebrew's current bottle, ship without `subtitles` and `drawtext`), and it can't match the video's typography or do karaoke.

## 5. Verifying sync

`gaga render` ends with `gaga check`, which reports:
- video and audio durations (they must match within 0.1 s)
- loudness (mean and peak dB), with a warning if the track is near-silent
- **music balance**: dB under the voice while it speaks, and vs the voice in the gaps (see [music-and-sound.md](music-and-sound.md) §6)
- cue count, overlaps, and whether the last cue fits
- **A/V sync**: speech onsets found by `silencedetect` on the **voice stem** (music would fill every silence) compared against cue starts. `gaga render` leaves the stem in `build/voice-stem.wav`, so a later `gaga check out/<name>.mp4` measures the same way. The median is typically 50–90 ms (the detector fires slightly after the consonant attack). The check warns above 300 ms.
- **Picture**: one pass over a small grey copy of the frames. It points at stretches of 1.5 s or more where nothing moves (the closing hold excepted), frames that differ from both neighbours, and blank stretches of 0.3 s or more, with their times; these are things to look at, not failures. More than three flashes in a second fails the check (photosensitivity).
- **Voice sync** (render only, since it needs the timeline): each clip's own speech onset, shifted to its place on the timeline, compared with the onsets on the voice stem. It covers lines that have no caption cue. It is typically < 20 ms and warns above 150 ms.

## 6. Troubleshooting

| Symptom | Fix |
|---|---|
| `403` / handshake errors | Update edge-tts (`uv` always fetches the latest; with pip, `pip install -U edge-tts`). Check that the system clock is correct (the DRM token is time-based). |
| No network | Scenes still preview with *estimated* timing (`say:` text or estimates). The render warns `estimated speech timing`. Run TTS when you're back online. |
| `CERTIFICATE_VERIFY_FAILED` / self-signed certificate | A TLS-inspecting proxy (company network, sandbox). edge-tts only trusts its own bundle; `scripts/tts.py` uses `SSL_CERT_FILE` (or `REQUESTS_CA_BUNDLE`) when set, so point that at the proxy's CA bundle. |
| `403` on CONNECT through a proxy | The network policy blocks `speech.platform.bing.com`. Allow that host; in hosted sandboxes a changed policy may only apply to new sessions. |
| `Failed to initialize cache at ~/.cache/uv` | A sandbox is blocking uv's home cache. `UV_CACHE_DIR=build/.uv-cache` clears that error, but uv still has to reach PyPI and the TTS service needs the network. Usually it's simpler to run `tts` / `voices` with permission. |
| Voice sounds rushed | Lower `rate`, or cut words. Don't cram. |
| Caption breaks mid-name | Put a space around the Latin term, or reduce `minChars`. |
| Visual hit misses the word | Use `s.when('exact words as spoken')`, and check `build/voice/<id>.json` for how the voice tokenised them. |
| Can't target part of a date or number | Edge returns a spoken date or long number as **one word** ("October 29th, 1969"), so `s.when('1969')` gives the start of the whole date. Time the parts with `s.at(s.when('October') + k, …)` or put the date in a music-only beat and use `s.onBeat(i)`. |
| Too much air after each line | Scene timing ends at the last word (+0.25 s for its decay), not at the end of the clip. Tune the pause with `tail`, never with negative values. |

## 7. One take: the voice first, the picture follows

Edge TTS (and most engines driven line by line) voices every scene on its own: the delivery restarts with each line and the pauses between lines come from `voiceDelay` and `tail`. When the voice should carry one mood from start to finish (a narrator reading the whole script, a cloned voice, a person recording it), make the voice first as **one take**, then let the picture follow it. Side by side on the same 4-minute explainer, the one-take version was preferred: the lines connect, and the pauses feel spoken rather than inserted.

1. **Write `narration.json` as usual**: one segment per scene, `text` is the caption. Then add:
   ```json
   {
     "lang": "zh-CN",
     "track": { "audio": "voice/take.wav", "lead": 0.45, "pauses": { "。": 1.0, "？": 0.9, "，": 0.35 } },
     "segments": [
       { "id": "hook", "text": "可上次是大杯还是中杯？少冰还是去冰？几分糖来着？", "pause": 2.0,
         "pauses": { "大杯还是中杯？": 1.0 } },
       { "id": "price", "text": "合计从 ¥26 变成 ¥22。", "spoken": "合计从二十六元，变成二十二元。" }
     ]
   }
   ```
   `spoken` is what the voice actually says when it differs from the caption. `pause` is the silence after the line (default: by its last mark, at least 0.8 s), `pauses` the silence after a phrase inside it, and `track.pauses` the defaults by punctuation (the values above for Chinese, the same for `. ? ,` in Latin text). Engines leave 0.2–0.8 s between sentences, which reads as rushed in a video; about 1 s after a full stop and 1.5–2 s after the hook, the title or a key line is a good start.
2. **Make the take in one pass**: the whole script, one blank line after each sentence (most engines breathe a little longer there). Generate it as one piece. An engine that splits long text into chunks may skip whole passages where the chunks join (VoxCPM2 with a 300-character chunk dropped several lines; the same script in one chunk was complete). Recording a person works the same way.
3. **Cut it**: `gaga voicetrack <project> --audio voice/take.wav [--clean]`. It transcribes the take with Whisper (mlx-whisper on Apple Silicon, faster-whisper elsewhere, through `uv`), aligns it to the script character by character (by pinyin in Chinese, so a homophone in the transcript still lines up), lengthens every pause to its target by adding silence only inside a silence it detected (never cutting into speech), cuts the take in the pause before each line (at most `lead` seconds before it), and writes `build/voice/<id>.mp3` + `.json`, `build/voice-track.wav` and `build/narration.js` with `track.segments[id] = [start, end]`. `--clean` adds a high-pass, de-noise and de-ess pass for a local model or a home recording.
4. **Read the report**: one line per segment, with how much of the line was heard and the characters that were not. Homophones and digits in the transcript are not reading errors; anything else, listen to. A stray syllable or breath inside a slice: `--cut <id>:<from>-<to>` (seconds from the start of that slice; comma-separate several), and run it again.
5. **Render as usual.** `gaga render` sees `track` and skips Edge TTS. The runtime places a run of scenes cut from the take so that the slices play back to back: each cut sits in the pause between two slices (the middle of its transition on the boundary), `voiceDelay` and `tail` of those scenes are ignored except the tail of the last slice, and neither the cuts nor the voices move onto the beat grid, so the pauses stay as recorded. A scene without narration in the middle simply pauses the take there.

Sync is checked as usual (§5); the per-clip voice sync of a one-take render is 0 ms by construction, and the caption onsets come from the aligned transcript.
