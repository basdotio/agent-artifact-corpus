# Questions and answers

## Can I use the voiceovers in monetized YouTube videos?

With Qwen3-TTS, yes: it (Apache 2.0) and Whisper (MIT) are free for commercial use, and the app itself is
MIT-licensed. Every model shows its licence in the app; *Commercial use OK* means monetized videos and client work
are fine. The optional **Fish Audio S2 Pro** model is marked in red: it's for non-commercial use unless you get a
licence from Fish Audio. So is the optional **OmniVoice** model (CC-BY-NC 4.0, non-commercial).

What you must still have is the **right to the voice**: see the next question.

## Can I clone anyone's voice?

Only your own voice, or a voice you have the speaker's permission to use. The app asks you to confirm this every
time you add a voice. Copying someone's voice without permission can break the law and the rules of YouTube and
other platforms, and it can mislead your audience.

If you don't have a voice of your own to use, **Find a new voice** on the Voices page: those voices are invented by
the model and belong to nobody, so no permission is needed.

## Does anything go over the internet?

No. Your scripts, voices and audio never leave your PC. There's no account, no analytics and no telemetry. The app
only goes online when you ask it to:

- downloading an engine (from GitHub), a model (from Hugging Face) or ffmpeg, with the Download buttons;
- checking for updates (GitHub), which you can turn off in Settings.

The API and MCP server only answer programs on your own PC, and only with the API key.

## Does it cost anything?

No. There's no subscription and no per-minute price: it runs on your own PC.

## Which languages does it speak?

Qwen3-TTS speaks English, Spanish, French, German, Italian, Portuguese, Russian, Japanese, Korean and Chinese.
The optional Fish Audio S2 Pro speaks 80+ languages, including Hindi, Urdu, Arabic, Turkish and Polish (see
[Setup and models](setup-and-models.md#fish-audio-s2-pro-a-second-voice-model)), and the optional OmniVoice speaks
96, for non-commercial use (see [OmniVoice](setup-and-models.md#omnivoice-a-third-voice-model)). Chatterbox (23 languages)
and VoxCPM2 (30) are free for commercial use, including Hindi, Arabic, Swahili and Turkish (see
[the audio.cpp models](setup-and-models.md#chatterbox-voxcpm2-cosyvoice-3-kokoro-and-moss-tts-nano-audiocpp)). *Numbers as words* works in English,
Spanish, French, German, Italian and Portuguese.

## How fast is it?

It depends on your graphics card. A laptop RTX 5060 speaks about 2.2× faster than real time: a 10-minute voiceover
takes about 5 minutes, subtitles included. AMD and Intel cards work too. Without a graphics card it runs at about
0.7× real time (a 10-minute voiceover takes about 15 minutes). The speed test on the Setup page tells you yours.

## How long can a script be?

As long as you like, up to about 4 hours of speech per script and 500 scripts per batch. Long scripts are spoken in
parts of about 40 seconds and joined, so you hear one voiceover.

## Can I work while it speaks?

Yes. Batches run in the background, in a queue. You can keep writing, start more batches, make Quick takes (they go
first), or close the browser. Your PC's graphics card is busy while it speaks, so games and video editing will be
slower.

## Does the voice always sound the same?

A voice from your library always sounds like the same person. The delivery (the pace and emphasis) can vary a
little from part to part. The same seed, voice and text give exactly the same take again, and **New take** gives a
different one when you'd like another reading.

## What's a seed?

A number that decides the small random choices the voice makes. Leave it empty for a random one. The seed is shown
under every part; use it again to get the same reading.

## What's LUFS?

A measure of how loud audio sounds. The app levels every voiceover to the same loudness, −16 LUFS by default (the
usual voiceover level), so your videos don't jump in volume between episodes.

## Do I need a Hugging Face account or token?

No. None of the models the app offers needs one.

## Does it work on Mac or Linux?

Yes, community-supported. The app is made for Windows 10 and 11 and has an installer for them. On Linux one
command sets everything up, with the engines for your graphics card (CUDA or Vulkan) and S2 Pro; run it again to
update. Apple Silicon Macs (M1 and newer) run it from the source code with Homebrew's engines, and S2 Pro with
one extra build step. How to set it up: [Linux and macOS](https://github.com/hassanxs/fatima-voice-studio#linux-and-macos) on GitHub.

## Can AI agents use it?

Yes: Claude Code, Codex, Antigravity, Hermes and other MCP agents can make voiceovers with it, within limits you
set. See [Connect](connect.md).

## Where do I report a problem or suggest something?

On [GitHub](https://github.com/hassanxs/fatima-voice-studio/issues). See also [Troubleshooting](troubleshooting.md).
