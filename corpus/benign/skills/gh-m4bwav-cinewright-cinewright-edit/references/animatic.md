---
title: Animatic
slug: animatic
summary: Cut approved stills to the cards' durations over scratch audio before any video render; the timing sheet locks each card's length and the stills become first frames.
tags: [edit, animatic, previs, timing, storyboard]
last_checked: 2026-10-09
sources: ["invideo FAQ, How do you make an AI animatic, 2026-08-10", "flick.art, Blender for AI filmmaking, 2026-06", "Boords, MP4 animatics", "local test, ffmpeg concat timing, 2026-10-09"]
---

# Animatic

## Rules

- Before paying for video, cut the film as stills: one approved still per card, held for the card's `duration_s`, over a scratch track (temp voices read at speaking pace, temp music). Run `CINE_POST animatic PROJECT --stills DIR --audio scratch.wav`.
- Watch it straight through, twice, with the sound. Fix story, order and length here: a cut that drags as stills drags as video. Change `duration_s` on the cards and re-run; it takes seconds.
- Time dialogue cards to the line read aloud plus a beat; the timing sheet lists each card's lines beside its in and out points.
- The approved still becomes the shot's first frame (or its keyframe guide) and the locked duration becomes its render length, snapped up to the model's frame grid and trimmed in the conform.
- A card with no still shows a grey frame: the animatic still plays, so missing art never blocks timing.
- Camera moves show as a slow push or drift on the still, enough to judge pace, not framing.
- Keep the animatic and its timing sheet beside the project; the edit compares the first assembly against it.

## Numbers

- A still per card; scratch voice at about 150 words a minute; hold a reaction 1 to 2 s.
- Making the animatic costs minutes; one rendered minute of video costs hours of GPU or dollars.

## Vocabulary

- animatic, scratch track, temp voice, timing sheet, picture lock, previs.

## Pitfalls

- Timing to the music before the lines: dialogue sets the length, music is cut to it.
- Treating the animatic's push-ins as camera direction: write the move on the card.
- Joining stills with ffmpeg's concat demuxer and `duration` lines drifts by a second or more; encode each card to its exact frame count first (the tool does).

## Verify

- The animatic's length equals the sum of the cards' durations; every card has a still or is listed as missing.
