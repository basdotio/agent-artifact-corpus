---
title: Assembly to delivery
slug: assembly-to-delivery
summary: Assemble in card order from passing takes, write the cut as a table in edit/cut.md, conform it frame-accurately with ffmpeg (re-encode, never stream copy), lock picture, then hand to finish and sound.
tags: [edit, assembly, edl, conform, ffmpeg, picture-lock]
last_checked: 2026-10-04
sources: ["https://ffmpeg.org/ffmpeg-filters.html", "Ken Dancyger, The Technique of Film and Video Editing, 6th ed., 2019"]
---

# Assembly to delivery

## Rules

- Order: assembly (every card in order, best take each) → rough cut (trims, drops) → fine cut (splits, pace) → picture lock → finish (cinewright-finish) → mix (cinewright-sound). No grade or mix before lock.
- Takes in: those with verdict `pass` or `keep-fix-in-edit` in `takes/` (`CINE cards list` gives the order).
- The cut lives in `edit/cut.md`, one row per shot: `# | slate | take file | in | out | length | cut in (straight, J n, L n, on action, match) | reason`. Times in seconds to 3 decimals and in frames. It is the edit decision list; a script or a person can conform from it.
- Conform with a re-encode. Stream copy (`-c copy`) cuts only on keyframes and drifts by up to a second.
- Keep one frame rate and size through the cut (the style bible's); conform mixed takes to it before joining.
- Intermediate files: high quality (`-crf 12` or a mezzanine codec) so the grade has room; the delivery encode happens once, at the end of finish.

## Numbers

- Frame time at 24 fps: 41.667 ms; an in point is `frames / 24`.

## Verify

Conform two trims and join them (frame-accurate, audio kept):

```
ffmpeg -i a.mp4 -i b.mp4 -filter_complex "[0:v]trim=start=0.208:end=6.000,setpts=PTS-STARTPTS[v0];[0:a]atrim=start=0.208:end=6.000,asetpts=PTS-STARTPTS[a0];[1:v]trim=end=4.000,setpts=PTS-STARTPTS[v1];[1:a]atrim=end=4.000,asetpts=PTS-STARTPTS[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]" -map "[v]" -map "[a]" -c:v libx264 -crf 12 -c:a pcm_s16le cut.mov
```

- `ffprobe -v error -show_entries format=duration cut.mov` equals the table's total within one frame.
