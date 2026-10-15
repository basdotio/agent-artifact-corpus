---
name: fix-frame
description: >-
  Changes a single shot in the user's video ad without remaking the rest. Asks which shot (a timestamp or a
  description) and what should change, regenerates only that shot to match the ad's length, size and frame
  rate, and splices it back with the original audio kept. With no ffmpeg, it delivers the replacement shot and
  exact splice steps for any editor. Use when: "/fix-frame", "replace only this frame in my video ad", "change
  one shot", "fix the shot at 0:07", "swap this scene but keep the rest", "the product looks wrong in one
  shot". NOT for: new ads from a product link (link-to-ads), UGC creator videos (ugc-ad), a new product video
  (product-video), remaking an ad you like (reference-ad), a swipe carousel (carousel), new openings for a
  video ad (hook-variants), new headlines on a static ad (headline-variants), a video thumbnail (thumbnail),
  trending social formats (viral-formats).
---

# Fix one frame

One shot changes. Every other frame and the whole soundtrack stay as they were.

First, read [references/predis-mcp.md](references/predis-mcp.md) and follow its loop for every generation. Model prompting rules are in [references/prompting.md](references/prompting.md).

## Step 1: Which shot, and what changes

Ask for the video if it is not in the chat. Then, in one message:
- Which shot: a timestamp ("around 0:07") or a description ("the one where she opens the box").
- What should change, in one sentence ("make the box blue", "remove the second person", "show the product label facing camera").

If either is unclear, ask. Don't guess the shot.

## Step 2: Find the exact cut points

**With ffmpeg.** Probe the ad, then list the cuts near the shot:

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate -show_entries format=duration -of default=nw=1 ad.mp4
ffmpeg -i ad.mp4 -vf "select='gt(scene,0.3)',showinfo" -f null - 2>&1 | grep -o "pts_time:[0-9.]*"
```

The shot runs from the cut at or before the user's time (S) to the next cut (E). D = E minus S. Pull the shot and its first and last frames:

```bash
ffmpeg -y -i ad.mp4 -ss S -t D -an -c:v libx264 -crf 16 -pix_fmt yuv420p shot.mp4
ffmpeg -y -i ad.mp4 -ss S -frames:v 1 first.png
ffmpeg -y -sseof -0.1 -i shot.mp4 -frames:v 1 last.png
```

Look at first.png and last.png and confirm with the user: "This shot, 0:06.2 to 0:09.0?"

**Without ffmpeg.** Ask the user for the start and end time of the shot and a screenshot of its first frame. If they can trim, ask them to export the shot alone as its own file.

## Step 3: Pick the route

Use `describe_model` on each pick before use. Limits below were true at writing; trust the live values.

| Route | When | Starting pick |
|---|---|---|
| A. Video edit | The change is local (color, an object, a sign, wardrobe) and the motion should stay | `wan_2_7_videoedit`: source clip plus one optional image, `duration` 2 to 10 whole seconds, `resolution` 720p or 1080p, `aspect` auto. Premium: `runway_aleph_2` (length follows the source, up to 4 images) |
| B. New shot from a fixed frame | The change is big (new action, new framing), or the shot is under 2s | Fix first.png with `nano_banana_pro` (image edit), then animate it with `seedance_2_0` in `keyframes` mode, fixed frame as `first_frame` (`duration` 4 to 15) |

- Route A, shot over 10s: cut only the part that changes, or ask the user before splitting it.
- Route A, `duration` takes whole seconds: set it to D rounded up. The extra is trimmed in the splice.
- Route B makes at least 4s. A shorter shot is trimmed to D.
- An image reference (a product photo, a target look) helps both routes. Give it one job in the prompt.

Show the route, what will change, and the cost from `estimate_cost`. Get one OK. Make 2 takes in one batch if the user is fine with the cost, so there is a fallback.

## Step 4: Generate

- Route A: add shot.mp4 as video 1 (or the user's exported shot).
- Route B: generate the fixed frame first, look at it, then animate it. Show the fixed frame to the user only if the change is big.
- Write prompts with [references/prompting.md](references/prompting.md).
- Look at a frame of each take, then pick the best.

## Step 5: Splice

**With ffmpeg.** Download into `./predis-output/fix-frame/<ad-name>/`. Fill in S, E, D, W, H, FPS from Step 2:

```bash
ffmpeg -y -i ad.mp4 -i new_shot.mp4 -filter_complex \
 "[0:v]split[o1][o2]; \
  [o1]trim=0:S,setpts=PTS-STARTPTS,fps=FPS,setsar=1,format=yuv420p[pre]; \
  [1:v]trim=0:D,setpts=PTS-STARTPTS,scale=W:H:force_original_aspect_ratio=increase,crop=W:H,fps=FPS,setsar=1,format=yuv420p[mid]; \
  [o2]trim=start=E,setpts=PTS-STARTPTS,fps=FPS,setsar=1,format=yuv420p[post]; \
  [pre][mid][post]concat=n=3:v=1:a=0[v]" \
 -map "[v]" -map 0:a? -c:v libx264 -crf 18 -preset medium -c:a aac -b:a 192k -shortest <ad-name>_fixed.mp4
```

- Shot at the very start: drop `[pre]` and use `[mid][post]concat=n=2`. Shot at the very end: drop `[post]` and use `[pre][mid]concat=n=2`.
- The new shot must be at least D long. If it is shorter, regenerate longer; don't stretch it.

Check with ffprobe: same width, height, fps and length (within 0.1s) as the original. Pull a frame just before S, at S, and just after E to check both seams.

**Without ffmpeg.** Share the new shot link and give the exact edit:
> In your editor, cut the original at S and at E. Delete the clip between them. Put the new shot on the gap at S and trim its end so it lasts exactly D seconds (ends at E). Mute the new shot and keep the original audio track untouched. Export at the original size and frame rate as <ad-name>_fixed.

## Check before showing

Reject and retry once if any of these is true:
1. The requested change is not visible, or something else in the shot changed that the user did not ask for.
2. The product, a face or an outfit differs from the frames on either side of the shot.
3. A seam jumps: light, grade, framing or screen direction breaks at S or E.
4. Garbled text, a watermark, or broken hands, faces or physics.
5. Spliced file: size, fps or length differs from the original, or the audio is out of sync after the shot.

Still failing after one retry: say plainly what did not work and offer the other route.

## Deliver

The fixed ad (or the shot plus the edit steps), one line on what changed, and the time range that changed. Nothing else in the ad was touched.
