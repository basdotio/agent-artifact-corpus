# Setup and models

The app itself is small. The parts that do the work are downloaded once, on the **Setup** and **Models** pages,
and then run offline. Both are in the menu button at the top right (the sliders icon, next to **?**).

## The Setup page

Setup shows what your PC has (graphics card and its memory, RAM, processor, free disk) and warns you about
anything that matters, like an NVIDIA driver that's too old. Then it walks through five steps, with the choices
that suit your PC marked **Recommended**:

1. **Engine** — the program that runs the voice model.
2. **Voice model** — speaks your scripts.
3. **Subtitles** (recommended) — the Whisper model that times your subtitles.
4. **A voice** — a link to the Voices page.
5. **Speed test** — speaks a short paragraph and measures how fast your PC is.

Click **Check again** after changing something on your PC (a new driver, for example).

![The Setup page](images/setup.webp)

## Engines

The engine is the official [llama.cpp](https://github.com/ggml-org/llama.cpp) build for your kind of graphics card.
You need one; you can download others and switch with **Use this one**.

| Engine | For | Download |
|---|---|---|
| **NVIDIA · CUDA** | NVIDIA GeForce RTX 20 series and newer, with a 2025 or newer driver. The fastest. | about 580 MB |
| **NVIDIA · CUDA (older driver)** | NVIDIA cards whose driver can't be updated, and GTX 10 and 16 series. | about 660 MB |
| **AMD / Intel · Vulkan** | AMD Radeon and Intel Arc cards. Also works on NVIDIA, a little slower. | about 33 MB |
| **CPU only** | PCs without a graphics card. Slower than real time. | about 19 MB |

If the recommended NVIDIA engine won't start, update your graphics driver from nvidia.com or the NVIDIA app, or use
*NVIDIA · CUDA (older driver)*.

## Voice models

| Model | For | Download |
|---|---|---|
| **Qwen3-TTS 1.7B · Q8** (default) | The best quality. Graphics cards with more than 4 GB. | 2.3 GB |
| **Qwen3-TTS 1.7B · Q4** | Graphics cards with 4 GB or less, and CPU-only PCs. | 1.5 GB |
| **Fish Audio S2 Pro · Q8** | Very expressive, 80+ languages, emotion tags. NVIDIA cards with 8 GB or more. | 5.6 GB |
| **Fish Audio S2 Pro · Q6** | The same for cards with 6 to 8 GB. | 4.5 GB |
| **OmniVoice · Q8** | Fast and small, 96 languages. Every engine, including 4 GB cards and the CPU. | 945 MB |
| **OmniVoice · Q4** | The same, compressed further: a third faster on the CPU. | 660 MB |
| **Chatterbox** | Clones voices in 23 languages, incl. Hindi, Arabic, Swahili, Turkish. Graphics cards. | 2.1 GB |
| **VoxCPM2** | Clones voices in 30 languages, 48 kHz. Graphics cards with 8 GB or more. | 3.0 GB |
| **CosyVoice 3** | Fast cloning in 8 languages, incl. Cantonese. Graphics cards. | 2.3 GB |
| **Kokoro** | Very fast, with its own 15 voices; over 2× real time even without a graphics card. | 190 MB |
| **MOSS-TTS Nano** | Tiny, clones voices; over 2× real time even without a graphics card. | 190 MB |

The two Qwen3-TTS downloads are the same model ([Qwen3-TTS](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base)),
free for commercial use (Apache 2.0), and speak 10 languages: English, Spanish, French, German, Italian, Portuguese,
Russian, Japanese, Korean and Chinese. The Models page warns when a model is a tight fit or too big for your
graphics card.

### Fish Audio S2 Pro (a second voice model)

[S2 Pro](https://huggingface.co/fishaudio/s2-pro) is a bigger, very expressive voice model: it speaks 80+ languages
(Hindi, Urdu, Arabic, Turkish, Polish and many more) and follows **emotion tags** in the text, like `[whisper]` or
`[excited]` (see [Writing scripts](writing-scripts.md#emotion-tags-s2-pro)). It copies a voice from the same clips
as Qwen3-TTS.

- **Engine:** it runs with the **NVIDIA · CUDA** or **AMD / Intel · Vulkan** engine (not the older-driver CUDA or
  CPU engine). Its own small engine part downloads with the model.
- **Speed:** about real time on an NVIDIA card with 8 GB (a 10-minute script takes about 10 minutes, half the speed
  of Qwen3-TTS). On Vulkan about 1.5 to 2× slower than real time, and there Q8 is faster than Q6 when it fits.
- **Graphics memory:** Q8 uses about 7 GB, Q6 about 6 GB. It stays loaded while you use it and unloads after a few
  idle minutes, or when Qwen3-TTS speaks. On cards under 12 GB, Whisper and S2 Pro take turns on the card: after
  each script S2 Pro steps aside for the subtitles and loads again (about 5 seconds).
- **Licence:** S2 Pro is for non-commercial use (Fish Audio Research License); commercial use needs a licence from
  Fish Audio. The app marks it in red, never picks it as the default by itself, and AI agents can't use it unless
  you allow it on the Connect page.
- Pick it per batch, quick take or preset in the **Voice model** list on the Create page, or as the default in
  Settings. Scripts for it are spoken in shorter parts (about 300 characters).

![One S2 Pro batch in English, Hindi, Urdu, Arabic, Japanese and Turkish](images/batch-s2.webp)

### OmniVoice (a third voice model)

[OmniVoice](https://huggingface.co/k2-fsa/OmniVoice) is a small, fast voice model. In the app it speaks 96 languages: Qwen3-TTS's 10 plus Hindi, Urdu, Arabic, Bengali, Swahili,
Cantonese, Hausa, Uzbek and many more (every language Whisper can also make subtitles for). It copies a voice from
the same clips as Qwen3-TTS.

- **Engine:** it runs on every engine: CUDA, the older-driver CUDA and Vulkan engines (on the graphics card), and the
  CPU engine. Its own small engine part downloads with the model.
- **Speed:** about 4× faster than real time on an NVIDIA card (a 10-minute script in about 2½ minutes, twice as fast
  as Qwen3-TTS), about 3× on Vulkan. On the CPU it uses a quicker setting and takes about 2 to 3 times as long as
  the audio (Q4 is the faster one there).
- **Graphics memory:** under 2 GB, so it suits 4 GB cards. It stays loaded while you use it (it starts in about a
  second) and unloads after a few idle minutes, or when another voice model speaks. Whisper runs beside it, except
  on cards under 6 GB, where they take turns.
- **Licence:** the model is for non-commercial use (CC-BY-NC 4.0; its makers changed it from Apache 2.0 in July
  2026 because of its training data). Like S2 Pro, the app marks it in red, never picks it as the default by
  itself, and AI agents can't use it unless you allow it on the Connect page.
- Pick it per batch, quick take or preset in the **Voice model** list on the Create page, or as the default in
  Settings. Long scripts are spoken in the usual parts (about 600 characters).

### Chatterbox, VoxCPM2, CosyVoice 3, Kokoro and MOSS-TTS Nano (audio.cpp)

These five run on [audio.cpp](https://github.com/0xShug0/audio.cpp), an engine for many voice models. Its own
official build for your engine (CUDA, Vulkan or CPU) downloads with the first of them; on NVIDIA · CUDA that's
about 460 MB (audio.cpp plus NVIDIA's cuFFT library). All five are free for commercial use.

- **Chatterbox** ([Resemble AI](https://huggingface.co/ResembleAI/chatterbox), MIT) copies a voice from its clip in
  23 languages, including Hindi, Arabic, Swahili, Turkish, Polish and Korean. About 2.7× faster than real time on an
  NVIDIA card in about 3 GB (Korean needs up to 6 GB). It needs a graphics card: on the processor it's about 10×
  slower than real time.
- **VoxCPM2** ([OpenBMB](https://huggingface.co/openbmb/VoxCPM2), Apache 2.0) copies a voice from its clip and what
  the clip says in 30 languages, including Hindi, Arabic, Thai, Vietnamese, Turkish and Swahili, at 48 kHz. About
  2.8× faster than real time on an NVIDIA card, in about 6 GB: for cards with 8 GB or more.
- **CosyVoice 3** ([Alibaba FunAudioLLM](https://huggingface.co/FunAudioLLM/Fun-CosyVoice3-0.5B-2512), Apache 2.0)
  copies a voice from its clip and what the clip says in English, Spanish, French, German, Italian, Chinese, Korean and
  Cantonese, about 5× faster than real time in about 3 GB. (It also knows Russian and Japanese, but copies a voice from
  another language poorly there, so they aren't offered.)
- **Kokoro** ([hexgrad](https://huggingface.co/hexgrad/Kokoro-82M), Apache 2.0) is tiny and very fast: over 10× faster
  than real time on a graphics card and about 2× on the processor alone. It **can't copy a voice**: it has its own
  voices, and the app adds 15 of them to your voice library (marked **Kokoro**) in English (American and British),
  Spanish, French, Hindi, Italian, Brazilian Portuguese and Chinese. Use those voices with Kokoro; the other models
  can copy them too. A voice you delete isn't added back. Kokoro also downloads eSpeak NG (12 MB, GPL v3, a separate
  library it uses for pronunciation).
- **MOSS-TTS Nano** ([OpenMOSS](https://huggingface.co/OpenMOSS-Team/MOSS-TTS-Nano-100M), Apache 2.0) copies a voice
  from its clip and what the clip says (heard by Whisper, as for S2 Pro), in under 1 GB: over 10× faster than real
  time on a graphics card and about 2.5× on the processor alone. The app offers it in English, Spanish, French,
  German and Chinese, the languages it speaks well.
- One model is loaded at a time; it unloads after a few idle minutes or when another voice model speaks. On cards
  under 12 GB it steps aside while Whisper makes the subtitles.

## Whisper models (subtitles and transcripts)

Whisper listens to the finished audio to time the subtitles, checks that every part was read, and powers the
[Transcribe](transcribe.md) page. With a graphics card engine it runs on the card, otherwise on the processor
(see below).

| Model | Notes | Download |
|---|---|---|
| **Whisper base** | The smallest and quickest. | 60 MB |
| **Whisper small** | Recommended for subtitles. About 10× faster than real time. | 190 MB |
| **Whisper medium** | More accurate, especially in Spanish and other non-English languages. | 539 MB |
| **Whisper large-v3 turbo** | Close to the best accuracy, much quicker than large-v3. Used by itself when Whisper runs on the graphics card. Good for transcribing other people's audio. | 574 MB |
| **Whisper large-v3** | The most accurate, and the slowest. For hard audio: accents, noise, music underneath. | 1.1 GB |

When you have more than one, choose which one is used with **Use this one** on the Models page, or in
**Settings → Files**. Left on *Best one downloaded*, the app uses *large-v3 turbo* when Whisper runs on your
graphics card (about as quick there as *small*, and much more accurate outside English), otherwise *small*. Your
subtitles always use your script's own words; Whisper only times them and checks that every word was said.

### Whisper on the graphics card

Whisper runs on the same graphics card as the voice, every model, with nothing to set up:

| Engine in use (step 1) | Whisper runs on | One-time extra download |
|---|---|---|
| **NVIDIA · CUDA** | the NVIDIA card | 131 MB |
| **NVIDIA · CUDA (older driver)** | the NVIDIA card | 247 MB |
| **AMD / Intel · Vulkan** | the AMD, Intel or NVIDIA card | 17 MB |
| **CPU only** | the processor | none |

That extra part of Whisper downloads by itself once you have the engine and a Whisper model (also after an update);
step 3 on Setup and the Models page show its progress, and then *Whisper runs on your graphics card*. Your Whisper
models aren't downloaded again: they're the same for the processor and the card. It uses the engine's own NVIDIA
files, so nothing big is downloaded twice.

On a graphics card, a 26-minute script is subtitled in about 40 seconds instead of about 6½ minutes, and the PC stays
free. **Large-v3 turbo** is then both the most accurate model and a quick one, so pick it.

- Laptops often have two graphics chips: one built into the processor and the real graphics card. Whisper uses the
  graphics card; the first time, it may start on the built-in chip and switch over by itself.
- If the graphics card can't run Whisper for any reason, the app uses the processor instead.
- On the processor, Whisper runs at low priority on half the threads, so the rest of the PC stays usable.

## Voice separator

*Voice separator (UVR MDX-Net)*, 67 MB: takes a voice out of music or background sound when you
[add a voice](voices.md#take-the-voice-out-of-music-or-background-sound) from a video or song. Runs on the
processor, about 4× faster than real time.

## Tools: ffmpeg

*ffmpeg* lets the app read video files (MP4, MKV, MOV, WEBM…) for transcripts and voice clips. If it's already
installed on your PC, the app uses that one and says *Already on this PC*. Otherwise, download it (115 MB) on the
Models page, under *Tools*. It's a separate program under the GPL licence; using it doesn't affect your audio.

## Downloading, pausing, removing

- **Download** — shows the size. A progress bar follows it, and you can leave the page.
- **Pause** — stops a download; **Resume** carries on from where it stopped. **Discard** deletes the part
  downloaded.
- Every download is checked against its known checksum when it finishes.
- **Remove** — deletes a model or engine from your PC. You can download it again any time. The default voice model
  and the engine in use can't be removed until you choose another.

Models come from Hugging Face and engines from GitHub. Nothing else is downloaded without you clicking a button.

## Licences

Every model shows its licence. **Commercial use OK** (green) means you can use the audio in monetized videos and
client work. Everything the app offers today is commercial-use OK. A non-commercial model would carry a red label,
and AI agents couldn't use it unless you allow it on the Connect page. The full list is in
[THIRD_PARTY_NOTICES.md](https://github.com/hassanxs/fatima-voice-studio/blob/main/THIRD_PARTY_NOTICES.md).

## The speed test

**Run speed test** speaks a short paragraph (about 20 seconds) and shows how many times faster than real time your
PC speaks, and about how long a 10-minute script takes. The Create page uses it for its estimates. Run it again
after changing the engine or the model. It can't run while batches are speaking.

Typical results: a laptop RTX 5060 speaks about 2.2× faster than real time; a PC without a graphics card about
0.7×.
