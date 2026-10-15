# Delivering the file

For the file the client opens: video, stills, print. Game exports are in `game-assets.md`, and texture maps in `baking.md`. Checks on the `.blend` are not checks on the delivered file.

## Rules for every delivery

1. **Decide the spec explicitly** (fps, resolution, frame range, format, colour space) and state any value you chose because the brief didn't say.
2. **Check the file you deliver, not the scene.** Probe it, then pull frames or open the image and look.
3. **Hold client-bound files for the user's review.** Never send them yourself.
4. **Audio is outside this skill.** If the brief implies sound ("a heavy thunk"), ask whether it's wanted.

## Video

- **Frame range is inclusive.** The count is `frame_end - frame_start + 1`. At 24 fps, 4.000 s is 96 frames: decide whether that is 1–96 or 0–95.
- **Render a PNG or EXR sequence, then encode with ffmpeg,** so one bad frame can be re-rendered alone.
- **H.264 needs even width and height** (manual; libx264 refuses odd sizes). `resolution_percentage` can make an even size odd.
- **A gap in the sequence silently shortens the video.** With `-i f_%04d.png`, ffmpeg stops at the first missing number (tested: frame 95 of 96 missing gave 94 frames, no error). Count frames on disk before encoding, and count again after.
- **Encode:** `ffmpeg -framerate 24 -start_number 1 -i f_%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 out.mp4`.
- **Check the encode** (tested: a missing frame and a planted black frame were both caught; a clean control passed):
  ```bash
  f=out.mp4; want=96
  ffprobe -v error -select_streams v:0 -count_frames \
    -show_entries stream=codec_name,pix_fmt,width,height,r_frame_rate,nb_read_frames -of default=nw=1 "$f"
  ffprobe -v error -show_entries stream=codec_type -of csv=p=0 "$f" | sort | uniq -c   # audio stream?
  got=$(ffprobe -v error -select_streams v:0 -count_frames -show_entries stream=nb_read_frames -of csv=p=0 "$f")
  [ "$got" = "$want" ] || echo "FAIL: $got frames, expected $want"
  ffmpeg -i "$f" -vf blackdetect=d=0:pix_th=0.10 -an -f null - 2>&1 | grep -o 'black_start:[0-9.]* black_end:[0-9.]*'
  ```
- **Pull frames from the encoded file** and look: `ffmpeg -ss 2.5 -i out.mp4 -frames:v 1 f.png`.
- **Writing video straight from Blender (5.0+):** set `image_settings.media_type = 'VIDEO'` before `file_format = 'FFMPEG'`. In 5.2, `'FFMPEG'` is rejected while `media_type` is `'IMAGE'`. The default container is MKV; set `scene.render.ffmpeg.format = 'MPEG4'` for .mp4.

## Stills

- **Keep a master and make deliveries from it.** Master: OpenEXR, `color_depth '16'` (half) or `'32'`, `exr_codec 'ZIP'` or `'PIZ'` (lossless). Delivery: 8-bit sRGB PNG or JPEG, or 16-bit PNG/TIFF if the client retouches.
- **Only display formats get the view transform.** PNG, JPEG and TIFF are saved through the view transform (AgX). EXR stays scene-linear (manual, "Save as Render"). To force one transform for a file, set `image_settings.color_management = 'OVERRIDE'` and its `view_settings`.
- **JPEG has no alpha.** Setting `file_format = 'JPEG'` turns `color_mode` from RGBA to RGB without warning (tested in 5.2). With `film_transparent`, deliver PNG or EXR with `color_mode = 'RGBA'`.
- **No ICC profile is embedded.** Blender doesn't write one (moderate: tracker report). If the client needs it tagged, add it afterwards with an image tool.

## Print

- **Pixels = inches × DPI.** 300 DPI is the usual brochure figure. 3000×2000 px at 300 DPI prints 10 × 6.67 in; tell the client the size their pixels allow.
- **Write the DPI into the file:** `scene.render.ppm_factor = 300`, with `ppm_base` at its default of 0.0254 (4.5+; PNG, JPEG, TIFF, EXR, BMP). It is metadata only and doesn't change the pixels.
- **Ask about CMYK; don't convert.** Blender outputs RGB only. If the printer wants CMYK, it is converted in a prepress tool with the printer's profile (unverified: no source found for the workflow; Blender's RGB-only output is from the format list).

## Red flags

| Thought | Reality |
|---|---|
| "The `.blend` checks passed, so the clip is fine" | Probe the encoded file and pull frames from it. |
| "The encode finished without error" | A missing frame shortens it silently. Count frames. |
| "4 seconds at 24 fps, so frames 0–96" | That's 97 frames. The range is inclusive. |
| "Transparent background, saved as JPEG" | JPEG dropped the alpha. Use PNG or EXR, RGBA. |
| "It's 3000×2000, so it's print-ready" | That's 10 × 6.67 in at 300 DPI. Say so, and ask about CMYK. |
