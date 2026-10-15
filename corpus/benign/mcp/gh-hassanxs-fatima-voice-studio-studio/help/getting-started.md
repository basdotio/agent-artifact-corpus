# Getting started

From download to your first voiceover in about 15 minutes, most of it waiting for downloads.

## 1. Install

1. Download `FatimaVoiceStudio-Setup-<version>.exe` from the
   [latest release on GitHub](https://github.com/hassanxs/fatima-voice-studio/releases/latest).
2. Run it. It installs for your Windows user only, so it doesn't ask for an administrator password.
3. If Windows says **"Windows protected your PC"**, click **More info**, then **Run anyway**. The installer isn't
   code-signed yet; it is built by GitHub from the public source, and each release lists its SHA-256 checksum.

**You need:** Windows 10 or 11 (64-bit), 8 GB of RAM and about 4 GB of free disk. An NVIDIA GeForce RTX card with
4 GB or more is best; AMD and Intel cards work too, and so does a PC without a graphics card (more slowly).

## 2. Start the app

Open **Fatima Voice Studio** from the Start menu. It runs in the background with an icon in the system tray (next
to the clock) and opens the studio in your web browser at `http://127.0.0.1:9830/`. The studio is a page in your
browser, but nothing goes over the internet: it all runs on your PC.

Starting it again while it's running just opens the page again. To close it for good, right-click the tray icon
and choose **Quit**.

> **Tip:** the small dot on the tray icon shows what it's doing: no dot = ready, amber = speaking or writing
> files, red = the engine has a problem.

## 3. Setup: two downloads

The first time, the app opens the **Setup** page by itself, and the other pages stay greyed out until two things
are downloaded. Setup has already looked at your PC and marked the right choices **Recommended**.

![The Setup page: what this PC has, then the engine, voice model and subtitles, each with a Download button](images/setup.webp)

1. **Engine** — the program that runs the voices. Download the *Recommended* one (for an NVIDIA card,
   *NVIDIA · CUDA*, about 580 MB).
2. **Voice model** — the voice itself. Download the *Recommended* one (*Qwen3-TTS 1.7B · Q8*, 2.3 GB, or the
   smaller *Q4* on PCs with little graphics memory).
3. **Subtitles** (recommended) — *Whisper small*, 190 MB. It times the subtitles of every voiceover. You can skip
   it, but then you get no SRT files.

Downloads can be paused and resumed, and they're checked when they finish. You can leave the page while they run.
See [Setup and models](setup-and-models.md) to choose differently.

## 4. Add a voice

Click **Open Voices** (step 4 on Setup), or **Voices** at the top. There are two ways to get a voice:

- **Add a voice** from a recording: 6–15 seconds of one person speaking clearly. Drop the file in, give it a name,
  tick the permission box, and click **Add voice**. Only use your own voice, or one you have the speaker's
  permission to use.
- **Find a new voice**: the model invents voices that belong to nobody. Pick a language, click **Find voices**,
  listen, name the one you like and click **Keep**.

Click **Hear it speak** on the new voice's card to hear it read a sample sentence. More in [Voices](voices.md).

## 5. Run the speed test

Back on **Setup**, step 5, click **Run speed test** (about 20 seconds). It measures how fast your PC speaks, so the
app can tell you how long each voiceover will take. On a laptop RTX 5060 it's about 2.2× faster than real time:
a 10-minute voiceover takes about 5 minutes.

## 6. Make your first voiceover

1. Click **Create** at the top. **Quick** is selected.
2. Type or paste a few sentences.
3. Check that **Voice** and **Language** are right. The language is the language of your text.
4. Click **Make it**, or press **Ctrl+Enter**.

The take plays by itself when it's ready, with **WAV**, **MP3** and **SRT** buttons to download it. It is also
saved on your PC, in today's *Singles* folder under **Batches**.

For a full script (or fifty), switch to **Batch**. See [Making voiceovers](making-voiceovers.md).

## What next

- [Write scripts that read well](writing-scripts.md): pauses, numbers, names.
- [Save a channel preset](making-voiceovers.md#channel-presets) so your channel's voice and settings are one click away.
- [Teach the voice a name it gets wrong](pronunciation.md).
