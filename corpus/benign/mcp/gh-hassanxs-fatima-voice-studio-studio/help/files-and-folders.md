# Files and folders

Everything the app makes is ordinary files on your PC, in folders you can open, copy and back up.

## Your audio: the Batches folder

Every batch is a folder in **Music\Fatima Voice Studio\Batches**, named after the batch. Rename the batch in the app
and the folder is renamed too. Open it with **Folder** on a batch, **Open folder** on the Batches page, or
**Open batches folder** in the tray menu.

Inside a batch's folder:

```
EP 08 - Seven impossible places\
    01_seven-impossible-places.wav    the finished voiceover
    01_seven-impossible-places.mp3
    01_seven-impossible-places.srt    its subtitles
    02_...                            the next script
    segments\                         every part on its own (001\001.wav, 001\002.wav, ...)
    batch.json                        the scripts, seeds and settings
```

Quick takes are in one folder per day, like `2026-10-09_Singles`, numbered `001_`, `002_`…

You can copy the WAV, MP3 and SRT files anywhere. Leave `segments` and `batch.json` in place while you might still
fix parts or re-run the batch: the app needs them.

To keep your audio somewhere else (another drive, a synced folder), choose the folder in
**Settings → Folders → Batches**.

## Everything else

| What | Where (installed app) |
|---|---|
| Batches (your audio) | `Music\Fatima Voice Studio\Batches\` |
| Exports made by AI agents | `Music\Fatima Voice Studio\Exports\` |
| Voices (one folder each: the original file, the prepared `clip.wav`, `voice.json`) | `%LOCALAPPDATA%\Fatima Voice Studio\voices\` |
| Settings, pronunciation list, presets, transcripts, logs | `%LOCALAPPDATA%\Fatima Voice Studio\data\` |
| Voice, Whisper and separator models | `%LOCALAPPDATA%\Fatima Voice Studio\models\` |
| Engines | `%LOCALAPPDATA%\Fatima Voice Studio\engine\` |

To open a `%LOCALAPPDATA%` folder, paste its path into the File Explorer address bar, or use the **Voices**,
**Models** and **Logs** buttons in **Settings → Folders**.

Run from source, everything is inside the project folder instead (`batches\`, `voices\`, `data\`, `models\`,
`engine\`).

## Back up

The things you can't download again:

- **Batches** — your audio.
- **voices** — your voice library.
- **data** — `config.json` (settings and API key), `dictionary.json` (pronunciation list), `presets.json` (channel
  presets) and `transcripts\`.

Copy those three folders. The models and engines (several GB) can always be downloaded again on the Setup page.
The pronunciation list can also be exported as a spreadsheet (see [Pronunciation](pronunciation.md#import-and-export)).

## Move to a new PC

1. Install Fatima Voice Studio on the new PC and start it once, then **Quit** it from the tray.
2. Copy the `voices` and `data` folders into `%LOCALAPPDATA%\Fatima Voice Studio\` on the new PC, and your
   batches into `Music\Fatima Voice Studio\Batches\`.
3. Start the app and download the engine and models on the Setup page.

If the new PC's Music folder is in a different place, set the Batches folder in **Settings → Folders**.

## Deleting

Batches, scripts, voices and transcripts deleted in the app go to the **Windows Recycle Bin**, so you can restore
them from there.
