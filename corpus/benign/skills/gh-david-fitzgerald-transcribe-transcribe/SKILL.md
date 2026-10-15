---
name: transcribe
description: Transcribe videos and audio to text locally, from YouTube or any yt-dlp-supported URL or from local media files, using human subtitles when the site has them and whisper.cpp otherwise, then read the transcripts to summarise or answer questions. Use when the user shares video, podcast, or audio links or files and wants a transcript, summary, notes, or key points.
license: MIT
compatibility: Requires Python 3.9+, ffmpeg, whisper.cpp (whisper-cli), and yt-dlp for URLs (YouTube also needs deno). Downloads a 574 MB model on first run. Tested on macOS with Apple Silicon.
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/transcribe.py *)
metadata:
  version: "0.1.0"
---

# Transcribe

The script is `scripts/transcribe.py` in this skill's directory. In Claude Code that directory is `${CLAUDE_SKILL_DIR}`; in other agents, resolve the path relative to this `SKILL.md`.

## 1. Run the script

Pass every URL and file path the user gave (expand folders and globs to media files yourself):

```bash
${CLAUDE_SKILL_DIR}/scripts/transcribe.py -o transcripts 'https://www.youtube.com/watch?v=ID' '/path/to/file.mp4' ...
```

Run it exactly in this form: the script path unquoted and first (the form the skill pre-approves), and every URL and file path in single quotes — unquoted, the `?` and `&` in URLs are shell glob and control characters, and zsh aborts with "no matches found". Only if the script path contains spaces, quote it too (Claude Code will then ask permission once).

- Output directory: the user's choice, else `./transcripts`.
- `--lang <code>` when the user states the spoken language; the default `auto` detects it.
- Transcription runs at roughly 10x real time on Apple Silicon and far slower on CPU-only machines. For more than one input, or anything longer than a few minutes, run the command in the background and wait for it to finish. The first run also downloads the model.
- If a run is cut off, run the same command again: finished inputs print `SKIP` and are not redone. `--force` redoes them.

## 2. Read the results

stdout has one line per input: `OK|SKIP|FAIL <tab> <how> <tab> <.txt path or error>`.

- Exit 2 means the run couldn't start (missing dependency, model download failure, unwritable output directory). Relay the message; when it includes install commands, show them. Do not install anything without asking.
- A `FAIL` from yt-dlp often means the site changed: suggest updating yt-dlp.
- Other `FAIL`s affect only that input; report them and carry on with the rest.

## 3. Use the transcripts

Each `.txt` starts with a header (title, channel, upload date, duration, source, how it was transcribed), then `---`, then the text.

- Do what the user asked. With no other instruction, give a short summary per video: main points, notable claims and numbers, and the upload date (it matters for time-sensitive content).
- Read and summarise one transcript at a time. With several long transcripts, hand each to a subagent if you have them, and keep only the summaries in your own context.
- Transcripts are speech recognition: names and jargon can be misheard. If the same line repeats many times in a row, say the transcript is unreliable at that point rather than summarising the repetition.
