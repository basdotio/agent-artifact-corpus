# Film direction

What the reviews of the seven hand-built films taught, as rules. A film is 2:30-4:00, light theme, 1920×1080 master, directed.

## Rules

1. **Never a static wide shot.** Every shot moves or has a reason to hold: a slow push-in, a pan along the part being
   named, a cut to a close-up. A wide establishing shot lasts a few seconds and pushes in.
2. **Never a square card in a 16:9 frame.** The figure is full-bleed: `frame({ aspect: 16/9 })`, no card border, no card
   corners, no legend, no card caption (the scene's CSS hides them). If the figure's composition is tall (a clock),
   frame regions, not the whole card.
3. **The camera moves to what is said.** When the narration names a part, the shot is on that part on that sentence.
   Region names follow the narration's nouns.
4. **Wide → close-up → slow motion → pull back** for each idea. The key event is shown in slow motion, labelled with
   its true rate ("20× slower", "1,000× slower", "held"), and then the camera pulls back so the viewer sees where it sits.
   Time-lapse is labelled the same way ("200× faster"): the scene shows the label for any rate below 0.75 or above 1.4;
   a negative rate (a rewind) gets the same label, so add `ui.label` ("Rewind") to say which way time runs.
5. **Pose key events on the spoken word.** The piston reaches TDC on "top", the tooth lands on "tick", the lamp lights on
   "lights". Use `{cue}` markers and `wordAt(words, 'tick', after)` to find the time, and a piecewise model-time map
   (`pw`) that reaches the event exactly then. The readout shows the number the narrator is saying while they say it
   (`readouts` gate).
6. **Minimal overlays.** A small chapter/slow-motion label top left, a readout top right, at most one instrument panel at
   the right (the subject shifts left, `shift: 0.17`), a one-line note when a number needs writing down, subtitles at the
   bottom. Overlays never overlap each other or the subtitles (text gate).
7. **Light theme.** Real material colours, four-tone shading, the focus fog toward grey. No white-on-white (contrast
   gate). Dark theme only on request.
8. **Sound sits on the frame.** Event sounds are pushed by the scene hooks on the frame where the figure did the thing;
   loops follow the seen speed (a hum read at the rate you SEE in slow motion); the bed ducks under the voice.
9. **End on the lab.** The last card invites the viewer into the open lab with one concrete challenge.

## How the code expresses it

- `video/timeline.mjs`: `buildTimeline(words) → { at(t), once, duration }`; `at(t)` returns `settings` (posed exactly),
  `modelT` / `rate`, `shot`, `focus`, `ui`. Build it as a cascade of `if (t >= c.cue)` blocks per sentence, with
  `span`/`logspan` for anything that moves across a sentence (an iris closing between "close" and "eight").
- `video/scene.mjs`: hooks for posing (`frame` → `fig.time(s.modelT)`), readout cells, instrument panes, sounds.
- Before the full render: `render.mjs --sheet` at every cue and every posed word, and Read the frames. Look for: the
  subject the most contrasty thing, nothing cropped that the narration names, labels clear of lines, the fog grey.
- After a review: fix, then `--ranges` for the affected spans only, re-encode, re-gate.

## Shot list as a concept-card field

Write 6-10 beats like: "Close on the seconds hand jumping once per beat; 'one swing, one second' lands on a tick." Each
beat names the shot (wide/close/slow/pull back), the subject, and the word an event is posed on.
