---
title: J and L cuts
slug: j-and-l-cuts
summary: Split sound from picture at dialogue cuts: L cut to hold a line over the listener, J cut to lead into a speaker or place; offsets of 6-24 frames, with generated audio crossfaded at the split.
tags: [edit, j-cut, l-cut, dialogue, sound]
last_checked: 2026-10-04
sources: ["Walter Murch, In the Blink of an Eye, 2nd ed., 2001", "Ken Dancyger, The Technique of Film and Video Editing, 6th ed., 2019"]
---

# J and L cuts

## Rules

- Dialogue scenes: straight cuts on every line change feel mechanical. Default to an L cut when the reaction matters more than the end of the line; a J cut when the next speaker's first words should pull the eye.
- Make the picture cut first (where), then slide the sound edit (when). The split is in the sound track only; both clips stay in sync.
- J cut into a new scene: the next place's ambience starts 0.5-1 s before its picture. This is the cheapest scene transition there is.
- Generated takes carry their own audio. At a split, crossfade the two audio tracks over 2-4 frames so the model's room noise does not click; lay room tone or ambience under the whole scene so the model's changing noise floors do not show (cinewright-sound, entry generated-audio).
- In a multi-shot generation (one take holding 1A+1B+1C), the model made straight cuts; a J or L cut there means cutting the generation apart and offsetting the sound, which is worth it only on a dialogue cut.

## Numbers

- Typical offset: 6-24 frames (0.25-1 s at 24 fps). Scene-transition J cut: 12-24 frames.
- Audio crossfade at a split: 2-4 frames.

## Vocabulary

- split edit, J cut, L cut, lead, overlap, prelap (sound of the next scene early).

## Pitfalls

- An L cut that runs past the listener's reaction into the next line confuses who is speaking.
- Lip sync: a J cut must not show the speaker's mouth before the sound it belongs to.

## Verify

- `edit/cut.md` marks each split with its offset in frames and which track moves.
