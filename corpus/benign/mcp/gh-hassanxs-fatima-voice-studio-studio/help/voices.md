# Voices

Your voice library is on the **Voices** page. Every voiceover is spoken in one of these voices. A voice is a short
clip of someone speaking: the model copies how that person sounds and speaks any text in their voice.

![The Voices page: Add a voice on the left, Find a new voice on the right, your voices below](images/voices.webp)

## Add a voice from a recording

1. Drop an audio or video file on **Add a voice**, or click it to choose one. WAV, MP3, FLAC, OGG, M4A, MP4, MKV,
   MOV and WEBM all work (video files need ffmpeg, see [Setup and models](setup-and-models.md#tools-ffmpeg)).
2. Listen to it in the small player that appears, to check it's the right file.
3. Give it a **Name** (for example *Narrator Laura*) and pick its **Language**: the language spoken in the clip.
4. Add **Notes** if you like: where it's from, what it's good for.
5. Tick **This is my own voice, or I have the speaker's permission to use it.**
6. Click **Add voice**.

The app prepares the clip for you: it trims silence, evens out the level, and checks the length, the background
noise and distortion. If something could be better, the voice's card says so in a short list of tips.

**A longer recording** (an interview, a whole video) is fine: the app picks its best 12 seconds of speech. Clips are
never longer than 20 seconds; anything longer is cut at a pause.

### What makes a good clip

- **6 to 15 seconds** of speech. Under 6 seconds copies the voice less closely; under 3 seconds may not work.
- **One person**, talking normally, in the style you want: a calm narrator clip gives a calm narrator.
- **Clean sound**: no music, no other voices, little echo or room noise.
- **Not distorted**: a recording that was too loud when it was made will sound rough in every voiceover.

The voice keeps the clip's character: its microphone, its room, its mood. A better clip is the biggest single
improvement you can make to your voiceovers.

### Reduce background noise

Tick **Reduce background noise** when the clip has a hiss, hum or room noise. You can turn it on or off later
(see *Prepare the clip again* below) and compare.

### Take the voice out of music or background sound

For a clip from a video or a song, tick **Take the voice out of music or background sound**. The voice separator
keeps only the voice. A long file is cut to its best minute first, and it takes a minute or two. It needs the
*Voice separator* model (67 MB) from **Models → Voice separator**; until then the box is greyed out.

## Find a new voice

**Find a new voice** makes voices that belong to nobody: the model invents a different one each time.

1. Pick the **Language** and **How many** (2, 4 or 6). Each takes about 8 seconds. The list shows the languages your
   downloaded voice models speak: Qwen3-TTS's 10, with OmniVoice 96, with S2 Pro 80+. A language your default
   model doesn't speak is found with another downloaded one that does (S2 Pro takes about 15 seconds a voice). For a language without a ready sample sentence, type one in **What the voices say**.
2. Click **Find voices** and listen to each one.
3. Type a name under the one you like and click **Keep**.

With **Kokoro** downloaded, its own 15 voices are added to your library too, marked **Kokoro**. Kokoro speaks
only with those (it can't copy a clip); the other models can copy them like any voice.

A kept voice is saved like any other and sounds the same from then on. Because it's nobody's real voice, no
permission is needed, which makes found voices a safe choice for monetized channels. Voices you don't keep are
forgotten.

## Your voices

Each voice has a card with its clip, its language and length, and:

- **Hear it speak** — reads a sample sentence in the voice's language, so you hear the voice as the model makes it
  (not just the original clip).
- **Edit** — change the name, language or notes, or prepare the clip again (below). With S2 Pro,
  OmniVoice, VoxCPM2, CosyVoice 3 or MOSS-TTS Nano downloaded, it also shows **What the clip says**: they copy a voice
  from the clip *and* its words. Whisper writes them down
  by itself; fix a word it got wrong, or empty the box to have it heard again.
- **Make default** (star icon) — the voice picked for you on the Create page. The default voice has a *Default*
  label and a filled star.
- **Delete** (bin icon) — the voice's folder goes to the Windows Recycle Bin. Voiceovers already made with it are
  kept.

*Found* on a card means the voice was found with *Find a new voice*.

### Prepare the clip again

The original file is always kept, so you can make a new clip from it. Click **Edit** on the voice, then:

- tick or untick **Reduce background noise**, and/or
- set **Use from** and **to** (in seconds) to use a different, cleaner part of the original.

Click **Save**. Then use **Hear it speak** to compare.

## Using a voice in another language

Each voice has a language, and picking it on the Create page sets that language. You can change the language
there to have the voice read text in another language; try a short Quick take first to hear how it sounds.

## Next

- [Making voiceovers](making-voiceovers.md) with your voice.
- [Troubleshooting](troubleshooting.md#the-voice-doesnt-sound-like-the-clip) if the voice doesn't sound right.
