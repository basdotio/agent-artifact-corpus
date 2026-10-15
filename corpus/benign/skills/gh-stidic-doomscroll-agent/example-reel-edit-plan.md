---
name: "reel-edit-plan"
description: "Turn a recorded StilesAI take and its script into a timestamped edit plan (graphics, on-screen text, pattern changes, effects) in Stiles's edit style, then build it if asked. Use when editing or planning the edit of a reel."
---

# Reel edit plan

Use this after Stiles records a take and wants Claude to edit it or plan the edit. The output is a timestamped edit list tied to what he says, then the edit itself if he asks for it.

## 1. His edit style (always applies)

These come from his approved voice-typing reel and his stated preferences. They override anything below.

- One continuous still take. No punch-in zooms, no random face zooms.
- Word-by-word white subtitles, placed low, but above the area Instagram's caption and buttons cover.
- Animated white cards pop into the empty space above his head: charts, dot grids, quote cards, before/after examples, real screenshots. Each card gets a small source label.
- Real visuals over text. No stacked mini-title + title + subtext cards. They read as vibe coded to him.
- Only checked numbers go on screen.
- Clean and simple. No glows, gradients, or decorative icons.

## 2. Techniques from the studied reels, and when to use them

1. **Pattern change at 2 to 3 seconds** (@kierzacporter). Something new appears right as the hook finishes. With a still take, that's a card popping in or a quick b-roll cut, not a zoom.
2. **Section labels** (@kierzacporter). A short label at the top that changes each section ("1. Visual hook," "2. Formats"). Good for list reels. Two to four words.
3. **Progress bar** (@realskytan). A thin segmented bar at the bottom showing which section you're in. Use on reels over about 40 seconds with clear sections. It quietly tells people there's more coming.
4. **UI cards beside the speaker** (@jasoncooperson). Small dark or white cards listing two or three points, a flow chip like "Raw footage → Finished edit," or an "In this video" checklist that ticks off. Closest to his style, so this is the default graphic.
5. **Show the prompt** (@jasoncooperson). When AI did the work, put the real prompt on screen as proof.
6. **Circle face-cam over screen recordings** (@johnbucog). For tool demos: the screen fills the frame and his face sits in a small circle in a corner, so he's always on screen.
7. **Result-first cold open** (@thetwofaced_). The first 2 to 3 seconds are the payoff clip, then the explanation starts.
8. **3D black bar pop** (@thetwofaced_). An object moving toward the camera seems to break out past black letterbox bars. How it's done: film the object moving at the lens, mask it out and content-aware fill the background, cut out a clean copy of the object, then keyframe black bars sliding in behind it. He did it in After Effects. Only use it for a hook where he's holding or pushing something toward the camera, like a phone.
9. **Lo-fi to polished contrast** (@bts). A messy handheld behind-the-scenes shot with POV text, then a hard cut to the polished piece. Good for showing off something he built.
10. **Full-screen word cards** (question-ladder reel, @johnbucog). A key phrase fills the screen in one color. Use once or twice at most, on the single line that matters. More than that fights his style.

## 3. Placement rules

- Nothing important in the bottom fifth or along the right edge, where Instagram's caption and buttons sit.
- One new element at a time, plus subtitles.
- Every graphic has to show data, proof, or a step. If it's decoration, cut it.

## 4. Output

1. **Edit table:** time range | what he says | what's on screen (card, text, b-roll) | source label | notes.
2. **Assets list:** screenshots to grab, charts with their data and source, any clips to record.
3. **Flags:** anything in the take that fails `reel-diagnosis` item 1 or 6 (a dead first frame, nothing new by 3 seconds, hook text that's hard to read), with the fix.

If he asks for the edit itself, build it from the table, render a draft, pull frames at 0, 1, 2, 3s and a few more across the reel, and check them before sending.

## Source reels

- @kierzacporter (instagram.com/p/Dc-_MDhotPD), @realskytan (instagram.com/p/DambEp1igDW), @jasoncooperson (instagram.com/p/DdCY-WwgHuK), @johnbucog (instagram.com/p/DW1xMPZjpkt), @thetwofaced_ (instagram.com/p/DbqEke7oewm), @bts snippet (instagram.com/p/DbVnWd3q_Yd), question-ladder reel (instagram.com/p/DdmmRtsPYfh)