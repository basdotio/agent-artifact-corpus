# Social cuts: Reels, TikTok, Shorts

A social cut is a different film from a landing loop: vertical, watched on a phone, often muted, judged in the first two seconds, and partly covered by the app's own interface.

## Format

| | Instagram Reels | TikTok | YouTube Shorts |
|---|---|---|---|
| Frame | 1080x1920 (9:16) | 1080x1920 | 1080x1920 |
| Length that works for a product | 15 to 30 s | 15 to 30 s | 20 to 45 s |
| Upload | H.264 MP4, AAC, 30 or 60 fps | same | same |

Platforms change their specs and interfaces; check the current ones before a paid campaign.

`setup.mjs videos/<film> --size 1080x1920`, and `render.mjs` delivers `<name>.mp4` ready to upload.

## Safe zone

The app draws the account name, caption, buttons and progress bar over the video. Keep every word and the key visual inside roughly:

- top 250 px free (status bar, "Reels" header)
- bottom 420 px free (caption, audio label, progress)
- right 120 px free in the lower half (like, comment, share)
- left 60 px margin

Set `safe: { top: 250, bottom: 420, left: 60, right: 120 }` in `cues.js`; `--debug` stills draw it. Treat it as a guide and preview on a phone before posting.

## Story for a feed

- **Second 0 to 2 decides everything.** Open on words or motion already happening, never on a slow logo. A logo build belongs at the end (or where the brand says).
- **Muted first.** Every idea must read without sound: captions or punchlines carry the story, sound adds weight.
- **One idea.** One problem, one product moment, one proof, one line. Cut the rest.
- **End on the lockup** (logo and tagline) and hold it at least 2 s so it can be read; a call to action only if the user chose one.
- **Big type.** Punchlines 96 to 120 px, captions 48 to 56 px at 1080 wide.

## Audio

- Aim for about -14 LUFS integrated, true peak under -1 dBTP (`verify.py` measures it).
- Music chosen in the app (trending audio) is added by the user when posting; deliver the cut with the generated or licensed bed, and a muted version if they plan to add in-app audio.

## Several formats from one film

Keep the story and cues; change the layout. Put the frame size in `cues.js` and derive positions from `CUES.width` and `CUES.height` in `setup()`, then render each size from its own copy of `index.html` (`--size` on setup). A 1:1 or 4:5 cut usually needs its own spacing, not a crop.
