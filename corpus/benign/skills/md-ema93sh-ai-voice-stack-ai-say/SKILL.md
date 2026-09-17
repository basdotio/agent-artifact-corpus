---
name: ai-say
description: >-
  Local text-to-speech on Ubuntu using Kokoro TTS with fallbacks.
  Use when the user asks you to speak, say, read aloud, announce, or
  narrate text. Also use for TTS playback testing, switching Kokoro
  voices, adjusting speech volume, or debugging audio output issues.
  Triggers: "say this", "say hello", "read that back to me",
  "read aloud", "speak", "announce", "narrate", "tell me out loud",
  "hear it out loud", "text to speech", "TTS", "voice test".
  Do NOT use for: recording audio, transcription, speech-to-text,
  playing music/media files, or dictation input.
license: MIT
compatibility: Requires Ubuntu/Linux with PulseAudio (pactl), ffmpeg, xbindkeys, xdotool, and Python 3
metadata:
  author: Ema93sh
  version: "1.0.0"
---

# AI Say

Local text-to-speech via `~/.local/bin/ai-say`. Kokoro-first with flite and
speech-dispatcher fallbacks. Requires the voice stack to be installed first.

## When to use this

Use this skill when the user wants text spoken aloud through their speakers:

- "say hello", "say this out loud"
- "read that back to me", "read this aloud"
- "speak", "announce", "narrate"
- "text to speech", "TTS"
- "voice test", "test audio output"
- "switch voice", "change TTS voice", "try a different voice"
- "it's too quiet", "adjust volume", "speech volume"
- "audio not working", "TTS broken", "no sound"

## When NOT to use this

Do not activate for these requests — they belong to other tools:

- **Recording or transcription** — "transcribe this", "speech to text", "STT", "dictate"
- **Media playback** — "play this mp3", "play music", "open audio file"
- **Audio hardware** — "install audio drivers", "configure ALSA", "set up Bluetooth speaker"
- **Dictation input** — "type what I say", "voice input" (that's dictate-start/stop, not ai-say)

## Prerequisites

The voice stack must be installed before using this skill:

```bash
git clone https://github.com/Ema93sh/ai-voice-stack.git
cd ai-voice-stack
scripts/voice-up-setup.sh --with-system-deps
```

This installs `ai-say` to `~/.local/bin/` and sets up Kokoro TTS.

## Usage

Speak text:

```bash
~/.local/bin/ai-say "Hello world"
```

Pipe text:

```bash
echo "Read this aloud" | ~/.local/bin/ai-say
```

Temporary voice override:

```bash
AI_KOKORO_VOICE=am_michael ~/.local/bin/ai-say "Different voice"
```

## Available Voices

### English (American)

**Female:** `af_alloy`, `af_aoede`, `af_bella`, `af_heart` (default), `af_jessica`,
`af_kore`, `af_nicole`, `af_nova`, `af_river`, `af_sarah`, `af_sky`

**Male:** `am_adam`, `am_echo`, `am_eric`, `am_fenrir`, `am_liam`,
`am_michael`, `am_onyx`, `am_puck`, `am_santa`

### English (British)

**Female:** `bf_alice`, `bf_emma`, `bf_isabella`, `bf_lily`

**Male:** `bm_daniel`, `bm_fable`, `bm_george`, `bm_lewis`

### Other Languages

Spanish (`ef_dora`, `em_alex`), French (`ff_siwis`), Hindi (`hf_alpha`,
`hf_beta`, `hm_omega`, `hm_psi`), Italian (`if_sara`, `im_nicola`),
Japanese (`jf_alpha`, `jf_gongitsune`, `jf_nezumi`, `jf_tebukuro`, `jm_kumo`),
Portuguese (`pf_dora`, `pm_alex`), Chinese (`zf_xiaobei`, `zf_xiaoni`,
`zf_xiaoxiao`, `zf_xiaoyi`, `zm_yunjian`, `zm_yunxi`, `zm_yunxia`, `zm_yunyang`)

## Persistent Voice Change

Edit `~/.config/ai-audio.env`:

```bash
export AI_KOKORO_VOICE="${AI_KOKORO_VOICE:-af_bella}"
```

## Volume / Gain

If speech is too quiet:

```bash
export AI_KOKORO_GAIN_DB=18
~/.local/bin/ai-say "Volume test"
```

## Diagnostics

Check stack health:

```bash
~/.local/bin/voice-status
```

Check audio devices:

```bash
pactl list short sinks
pactl list short sources
cat ~/.config/ai-audio.env
```

Test direct tone on a specific sink:

```bash
ffmpeg -hide_banner -loglevel error -f lavfi -i 'sine=frequency=880:duration=3' -f wav - | paplay --device='<sink-name>'
```

## Subcommands

### Install

Run the full voice stack installer. Finds the repo automatically or clones it:

```bash
bash scripts/install.sh --with-system-deps
```

### Doctor

Check installation health — reports PASS/FAIL for every component:

```bash
bash scripts/doctor.sh
```

## How to use ai-say (process)

Always use `~/.local/bin/ai-say` as the entry point. Never call Kokoro,
flite, or spd-say directly — `ai-say` handles engine selection, chunking,
volume boost, and sink routing automatically.

- Pass text as an argument: `~/.local/bin/ai-say "text"`
- Or pipe text: `echo "text" | ~/.local/bin/ai-say`
- Override voice with env var: `AI_KOKORO_VOICE=am_fenrir ~/.local/bin/ai-say "text"`
- For diagnostics, run `~/.local/bin/voice-status` first, then `bash scripts/doctor.sh`

Do NOT:
- Call `kokoro-synthesize.py` or the Kokoro Python API directly
- Use `spd-say`, `flite`, `espeak`, or `aplay` directly
- Modify files under `~/.local/share/kokoro-tts/` unless troubleshooting
- Speak content the user did not ask to hear

## Definition of done

The skill is working correctly when:

- `~/.local/bin/ai-say "test"` produces audible speech
- `bash scripts/doctor.sh` reports all checks PASS
- The agent used `~/.local/bin/ai-say` (not a direct TTS engine call)
- Only text the user requested was spoken

## Notes

- `ai-say` is Kokoro-first, with flite and spd-say fallback paths.
- Text is truncated at 1600 chars and chunked at 320 chars for reliable playback.
- Keep messages respectful and follow user intent exactly for spoken content.
