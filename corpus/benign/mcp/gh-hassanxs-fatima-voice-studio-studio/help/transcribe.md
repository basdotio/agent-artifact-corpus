# Transcribe

The **Transcribe** page turns a video or audio file into text and subtitles: a **TXT** file with the words, and
**SRT** and **VTT** subtitle files with timings. It runs with Whisper on your PC; nothing is uploaded anywhere.

Use it to get the script of a video, subtitles for a video you made elsewhere, or the words of an interview.

## Transcribe a file

1. Drop a file on the box, or click it to choose one: MP4, MKV, MOV, WEBM, M4A, MP3, WAV, FLAC, OGG…
2. **Language** — leave *Detect automatically*, or pick the language spoken to be sure.
3. **Whisper model** — *The one in use* is the one picked in Settings. Choose another downloaded one if you like.
4. Tick **Translate to English** to get English text from speech in another language.
5. Click **Transcribe**.

The transcript appears under **Transcripts** with its progress. You can leave the page; it carries on.

When it's done:

- **Read** — opens the text, ready to select and copy.
- **TXT**, **SRT**, **VTT** — download the files.
- **Delete** (bin icon) — the files go to the Recycle Bin.

Each transcript shows the length, the number of words, the language found, which model was used and how long it
took.

## Which Whisper model?

| Model | Good for |
|---|---|
| **Whisper small** | Quick, and plenty for clear speech. A 2-minute video takes about 15 seconds. |
| **Whisper medium** | More accurate with accents, noise, or several speakers. Slower. |
| **Whisper large-v3 turbo** | Accurate and still fairly quick. A good choice for other people's audio. |
| **Whisper large-v3** | The most accurate, and the slowest. |

Download them on the **Models** page, under *Subtitles and transcripts*. They run on the processor (CPU), or on
your graphics card when the voice engine uses one (CUDA or Vulkan): a 26-minute recording in under a minute. See
[Setup and models](setup-and-models.md#whisper-on-the-graphics-card).

## Video files need ffmpeg

Audio files work straight away. Video files (MP4, MKV, MOV, WEBM) need **ffmpeg**, a free tool that reads video.
If ffmpeg is already on your PC, the app uses it. If not, download it on **Models → Tools** (one click). See
[Setup and models](setup-and-models.md#tools-ffmpeg).

## Next

- [Setup and models](setup-and-models.md)
- [Connect](connect.md): transcription is also available to other apps through the API.
