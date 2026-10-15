# Formats — platforms, safe zones, encoding, loudness

## Aspect ratios and sizes (2026)
| Platform / use | Ratio | Size | Notes |
|---|---|---|---|
| YouTube, websites, keynotes, X | 16:9 | 1920×1080 (3840×2160 for 4K) | default for launch films and walkthroughs |
| LinkedIn feed | 16:9 or 1:1 (4:5 also good) | 1920×1080 / 1080×1080 | 30–90 s ideal; ~85 % watched muted → captions |
| Instagram feed | 4:5 or 1:1 | 1080×1350 / 1080×1080 | 4:5 takes the most feed space |
| Instagram Reels | 9:16 | 1080×1920 | up to 3 min |
| TikTok | 9:16 | 1080×1920 | 5–60 s for completion; sound matters most here |
| YouTube Shorts | 9:16 | 1080×1920 | up to 3 min |
| Stories | 9:16 | 1080×1920 | 15 s segments |
`new_project.py --format 16:9 | 9:16 | 1:1 | 4:5` sets the stage size; everything reads `W`/`H`.

## Safe zones for vertical (keep text and faces inside)
| | top | bottom | left | right |
|---|---|---|---|---|
| TikTok in-feed | 8 % | 22 % | 6 % | 13 % |
| Instagram Reels | 12 % | 32 % | 6 % | 11 % |
| Instagram Stories | 13 % | 20 % | 6 % | 6 % |
| YouTube Shorts | 9 % | 20 % | 6 % | 12 % |
Design vertical cuts as their own layouts (re-frame the world camera, re-stack type) — never centre-crop 16:9.
Captions in vertical sit above the bottom safe line, not on it.

## Frame rate
Master at 60 fps (UI motion, cursors and scrolls look smooth; motion blur integrates cleanly). Deliver 30 fps
only if a platform requires it: `ffmpeg -i master.mkv -vf fps=30 …` (frame-blend with `tblend` is not needed
— the shutter already blurred motion).

## Encoding (tools/assemble.py)
- Master MP4: H.264 High, CRF 13, `-preset slow`, GOP 2 s, yuv420p, BT.709 tags (`colorspace`, `primaries`,
  `trc`, `range tv`), AAC 320 kb/s 48 kHz encoded from the float WAV, `+faststart`.
- Preview: short side 720 px, CRF 21, AAC 192 kb/s.
- Lossless intermediate: FFV1 level 3, bgr0 in MKV. Splice by frame index (`trim=start_frame:end_frame`) and
  re-encode losslessly; the concat demuxer's inpoint/outpoint is not frame-exact.
- Covers: a designed still (the hero frame, captions off: `--query only=…` excludes the captions scene).

## Loudness
| Destination | Target | True peak |
|---|---|---|
| Web / social (YouTube, LinkedIn, Instagram, TikTok) | −14 LUFS integrated | ≤ −1 dBTP (we use −1.5) |
| Podcasts / spoken-word | −16 LUFS | ≤ −1 dBTP |
| Broadcast EU (EBU R128) | −23 LUFS | ≤ −1 dBTP |
| Broadcast US (ATSC A/85) | −24 LKFS | ≤ −2 dBTP |

## Captions
Burn in for muted feeds (LinkedIn, Instagram, X); also ship `.srt` (UTF-8, ≤ 42 characters per line, ≤ 2
lines, 1–7 s each). For YouTube prefer the SRT; for in-app embeds burn in.

## Durations that work
Logo sting 4–8 s · teaser 15–30 s · vertical cut 15–45 s · onboarding 45–75 s · launch film 60–90 s (long-form
keynote films up to ~2:30 when the user asks for "all the sections") · explainer 60–90 s.
