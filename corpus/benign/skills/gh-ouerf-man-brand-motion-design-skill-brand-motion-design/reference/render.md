# Final render, verification and delivery

## Render (`scripts/render.mjs`)

```bash
node <skill>/scripts/render.mjs videos/<film> [--name acme-launch] [--poster b9.1] [--fps 60] [--blur 4] [--loop] [--webm]
```

1. **Master.** `npx hyperframes render --fps 240 --quality high --crf 10 --strict`, with the audio mix (music and effects from the `<audio>` tags).
2. **Motion blur.** ffmpeg `tmix` averages each group of 4 subframes and `select` keeps one, giving 60 fps with real blur on fast moves. HyperFrames tags its output BT.709 limited range; the pipeline keeps those tags end to end, so colors do not shift. `--blur 1` skips it.
3. **Deliverables** in `out/<name>/vN/` (a new version every run, never overwritten):
   - `<name>.mp4`: H.264 High, yuv420p, 60 fps, BT.709 tags, AAC 256k 48 kHz, `+faststart`. The file for social, review and most players.
   - `<name>-muted.mp4` (with `--loop`, or when silent): the landing-page loop.
   - `<name>.webm` (with `--webm`): VP9, for the web.
   - `poster.jpg` from `--poster` (a headline or the logo lockup, not frame 0).
   - `loop-seam.png` (with `--loop`): the last 8 and first 8 frames, played twice.
4. Master and intermediate are deleted; sizes are printed.

Timing: the master captures 4x the frames (6000 for 25 s). Measured: about 3.5 frames per second on a software-GL cloud sandbox (about 30 minutes for 25 s); a laptop with GPU capture is several times faster. Run it in the background and review other things meanwhile. Iterate with `--draft` (30 fps, no blur).

If the render summary says `screenshot capture · software gpu`, it is on the slow path (fine, just slower). `npx hyperframes doctor` explains how to enable BeginFrame capture.

## Verify before sending (`scripts/verify.py`)

```bash
uv run --with numpy python3 <skill>/scripts/verify.py videos/<film>/out/<name>/v3 \
  --duration 25 --bg 11,18,38 --probe 14.7:369,785=255,138,61 [--loop] [--lufs -14]
```

For every deliverable it checks:
- duration (to a frame), size and frame rate
- BT.709 color tags (untagged files shift on phones)
- frame 0 at a background point decodes to the background token within 3 (a range or matrix mistake lifts #0a0a0a to #171717: fix the pipeline, never the tokens)
- each probe (`seconds:x,y=r,g,b`): the accent or the one highlight where it should be, within 12
- with `--loop`, the last frame against frame 0
- audio: present, integrated loudness and true peak (fails above -1 dBTP)

## Deliver

- Send the file with music (and the muted loop, WebM and poster if made) with a two-line caption of what changed.
- Report: durations, sizes, the checks you ran and their numbers.
- Keep the composition source next to the renders (the `videos/<film>/` folder is the source of truth).
- Do not commit, push or publish unless asked.
