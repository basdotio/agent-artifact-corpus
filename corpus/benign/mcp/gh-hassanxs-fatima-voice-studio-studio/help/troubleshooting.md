# Troubleshooting

Find your problem below. If it isn't here, see [Still stuck?](#still-stuck) at the end.

## Installing and starting

### "Windows protected your PC" when installing

The installer isn't code-signed yet, so Windows SmartScreen doesn't recognise it. Click **More info**, then
**Run anyway**. The installer is built by GitHub from the public source code, and each release lists its SHA-256
checksum if you want to check your download.

### The page doesn't open, or says it can't connect

- Look for the app's icon in the system tray (next to the clock; click the **^** arrow to see hidden icons). If
  it's there, right-click it and choose **Open Fatima Voice Studio**.
- If it isn't there, start **Fatima Voice Studio** from the Start menu again.
- The top right of the page says **Not running** when the app has stopped: start it from the Start menu, then
  reload the page.
- If you changed the **Port** in Settings, the address changed too: `http://127.0.0.1:<new port>/`.

### All the pages except Setup are greyed out

The app needs an engine and a voice model before it can speak. Download both on the **Setup** page; the other pages
open as soon as they're ready. See [Getting started](getting-started.md#3-setup-two-downloads).

## The engine

The top right of every page shows the engine's state. **Engine problem** in red means it couldn't speak; the line
below says why.

### "The engine couldn't start: a file it needs is missing"

Usually the **Microsoft Visual C++ Runtime** is missing, which happens on a freshly installed Windows. Install it
free from Microsoft ([vc_redist.x64.exe](https://aka.ms/vs/17/release/vc_redist.x64.exe)) and try again. If that
doesn't help, remove the engine and download it again on the **Setup** page.

### "The graphics card ran out of memory"

- Close other programs that use the graphics card: games, video editors, other AI apps, many browser tabs with video.
- Use the smaller **Qwen3-TTS 1.7B · Q4** voice model: download it on the Models page and pick it in
  **Settings → Defaults for new scripts → Voice model**.

### "S2 Pro didn't fit in the graphics card's memory"

S2 Pro Q8 needs about 7 GB of graphics memory. Close other programs that use the graphics card (games, video
editors, other AI tools), or download **S2 Pro · Q6** on the Models page, which needs about 6 GB.

### S2 Pro: "runs on the NVIDIA · CUDA or AMD / Intel · Vulkan engine" or "engine part is missing"

S2 Pro doesn't run on the older-driver CUDA engine or the CPU engine: on **Setup**, download and use *NVIDIA · CUDA*
(or *AMD / Intel · Vulkan*). If the engine part is missing (after switching engines, for example), click **Get it**
on S2 Pro's card on the Models page.

### The NVIDIA engine won't start, or Setup says the driver is too old

Update your graphics driver from [nvidia.com](https://www.nvidia.com/Download/index.aspx) or the NVIDIA app, then
click **Check again** on Setup. If you can't update it, download **NVIDIA · CUDA (older driver)** on Setup and click
**Use this one**.

### "The engine couldn't load the model files"

The model download may be damaged. On the Models page, **Remove** the model and download it again.

## Speed

### It's much slower than expected

- On **Setup**, check which engine is **In use**. On an NVIDIA card it should be *NVIDIA · CUDA*, not *CPU only*.
- Close other programs using the graphics card.
- A laptop should be plugged in: on battery, Windows slows the graphics card down.
- Run the **speed test** again on Setup to see the current speed. About 2× faster than real time is normal on a
  recent NVIDIA card; a PC without one is slower than real time.

### "Writing files · subtitles" takes a long time

That's Whisper timing the subtitles. On the processor, a long script with a big Whisper model takes minutes (a
26-minute script with large-v3 turbo: about 6½). The top bar shows its progress and where it runs.

- With a graphics card, use a graphics card engine on **Setup** (NVIDIA · CUDA, or Vulkan for AMD and Intel):
  Whisper then runs on the card too, and the same script takes under a minute. Step 3 on Setup shows where Whisper
  runs, and whether its graphics card part is still downloading or needs **Try again**.
- Without one, pick **Whisper small** in **Settings → Files → Whisper model**: plenty for subtitles, since they
  use your script's own words.

### The estimate on the Create page is wrong

Run the **speed test** on Setup once. Until then the estimate uses a typical speed, not yours.

## How it sounds

### The voice doesn't sound like the clip

The clip makes the biggest difference. See [What makes a good clip](voices.md#what-makes-a-good-clip):

- Use 6–15 seconds of one person, clearly, without music. Read the tips on the voice's card.
- Try **Reduce background noise**, or prepare the clip again from a cleaner part of the original (**Edit** on the
  voice).
- For a clip with music under it, add it again with **Take the voice out of music or background sound**.
- Check the **Language**: pick the language of your text on the Create page.

### A word or name is said wrong

Add it to your [pronunciation list](pronunciation.md), spelled the way it sounds. To fix it only once, **Edit** that
part in the batch. For numbers, check that **Say numbers as words** is on, and use **See what the voice will read**.

### A part repeats itself, rambles, skips words, or sounds odd

Open the batch, find the part (parts with a problem are marked), and click **New take** for a different reading.
If it keeps happening, **Edit** the part: split a long sentence, or add a comma. See
[Fixing one part](batches.md#fixing-one-part).

### A part is marked "worth a listen" but sounds fine

Whisper didn't recognise enough of its words. That's often an unusual name or a word in another language. If it
sounds right to you, you can ignore it.

### Different scripts sound slightly different

Every part is spoken with its own seed (shown under the part), and the delivery can vary a little from one seed to
another. A **New take** changes only that part. To make a whole batch again exactly as it was, use **Re-run**: it
keeps the seeds.

### The voiceover is too quiet or too loud

Change **Loudness** with **Output** on the batch: −16 LUFS for voiceovers, −14 to match YouTube music. The files are
rebuilt in seconds. See [Change speed, loudness or files afterwards](batches.md#change-speed-loudness-or-files-afterwards).

## Subtitles and files

### There's no SRT file

Subtitles need a Whisper model: download **Whisper small** on Setup or Models. Then open the batch and click
**Output**, make sure **Subtitles (SRT)** is ticked, and click **Rebuild files**.

### "Reading this file needs ffmpeg" / "Reading video needs ffmpeg"

Video files (and some audio formats) need ffmpeg. Download it on **Models → Tools**. See
[Tools: ffmpeg](setup-and-models.md#tools-ffmpeg).

### I can't find my files

Click **Folder** on the batch. All batches are in **Music\Fatima Voice Studio\Batches** unless you chose another
folder in Settings. See [Files and folders](files-and-folders.md).

### I deleted something by mistake

Batches, scripts, voices and transcripts go to the **Windows Recycle Bin**. Open it, right-click the folder, and
choose **Restore**. Then restart the app.

## Batches

### "This batch is working right now" when renaming, editing or deleting

Pause the batch, wait for the current part to finish, then try again. To delete a batch that's still working,
**Stop** it first.

### A batch says "Needs attention"

A part failed. Open the batch to read why (the red note under the part), fix the cause, and click **Retry**.

### The PC turned off in the middle of a batch

Nothing is lost: the batch carries on where it left off when the app starts again.

## Updates

### No update appears, but there's a new version on GitHub

Click **Check now** under **About → Updates** (About is in the menu at the top right). If you run the app from its source code (not installed), updates
come from git instead. You can always install a new version by running its installer from the
[releases page](https://github.com/hassanxs/fatima-voice-studio/releases).

## Still stuck?

![The About page: the version, your models' licences, and This PC with Copy details and Report a problem](images/about.webp)

1. Open the log: **Settings → Folders → Logs**. `studio.log` (the app) and `engine.log` (the engine) say what went wrong, in more
   detail than the page.
2. Open **About** (in the menu at the top right) and click **Copy details**: your version, Windows, graphics card,
   engine and models, ready to paste.
3. Open an issue on [GitHub](https://github.com/hassanxs/fatima-voice-studio/issues) (**Report a problem** on the
   About page) with what you did, what you expected, what happened, the details you copied, and the end of the
   log. Don't post your API key.
