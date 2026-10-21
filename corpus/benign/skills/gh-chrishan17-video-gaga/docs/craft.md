# What good looks like

This page describes the finished video you are aiming for, not the steps to get there. Get there however you like. Before you deliver, hold the real output (the frames, the motion, the score report, the encode) against it, and keep going until the video meets it.

The bar is what people scroll past every day: work by good studios, editors and creators. A video that is only correct (on time, readable, in sync) still looks like a template next to that.

## The whole

A good video is about one thing and is told by someone. After 30 seconds the viewer can say what it was about in a sentence, remembers one image and one line, and felt something change between the start and the end. It could not be swapped for another video on the same topic.

It earns attention early and keeps paying it back: within the first two seconds there is a picture worth stopping for, and after that something new lands every few seconds (a reveal, a transformation, a change of scale or place), with the quiet stretches chosen rather than left over.

Not good: a sequence of true statements with pictures, which is a slideshow with music. A video whose every part is fine but which leaves nothing behind.

## Story

**Good**
- It is specific: a person, a moment, an object, a number. 5:40 on a dark street, the third lamp post where the lungs gave up, 0.12 km on day one. One true, odd detail makes the viewer believe the rest.
- It has a shape: an opening that makes the viewer want something (a question, a gap, a problem they recognise), a **turn** where something changes (a reversal, a reveal, a reframe), and a landing that pays off the opening, often by bringing back the first image, changed.
- The angle is a choice. Of the several ways to tell it (a confession, a counter-intuitive claim, one object followed through time), it is the one with tension and a picture.
- Every line is concrete and sounds like a person talking to one person. One line is worth repeating, and it lands with silence before it.
- Words and pictures split the work: the voice says what the picture can't, and the picture shows what words would make dull.
- When the brief is only a topic, the invented specifics are plausible, humane and modest, and they are listed as assumptions the user can swap for their own. Facts, figures and quotes are real and sourced.

**Not good**
- Lines that could close any advert: 梦想, 坚持, 改变, 未来, 成就更好的自己, "unlock", "journey", "seamless".
- A list with no turn. A moral at the end instead of an image.
- The voice describing what is already on screen.
- Facts invented about real people or products.

[examples/take-your-time/BRIEF.md](../examples/take-your-time/BRIEF.md) is a story at this level: a specific person, a device that carries the story, a turn, a callback.

### When the video explains

An explainer is told by someone too, but its turn happens in the viewer's head: they leave with one new understanding they could pass on, of how something works, why it happens or what follows from it. Everything above holds. What changes is the shape and the discipline.

**Good**
- It answers one question, written in the viewer's own words ("why does my phone get slower?", not "battery chemistry"), and names what they believe now and what they can say after.
- The opening is the thing most viewers get wrong, shown as an image, not a title card: the tempting wrong answer in the picture, about to be overturned.
- The middle builds the smallest correct picture of how it works, one element per beat, then runs it on a real case so cause and effect play out on screen. The turn changes one variable and shows what follows; that is where it clicks. The landing is the opening image again, now read correctly, plus one next step.
- The facts were sorted before writing: what the viewer must know, and a cut list of true, interesting things that stay out. The cut list is long.
- A metaphor is used only when it makes the idea more accurate; otherwise the real thing is shown (real UI, real data, the real mechanism). A metaphor that has to be explained away later costs more than it gave.
- One name per thing, used every time, in the voice and on screen. Plain words come before the term; the term arrives once the picture has earned it.
- On-screen words are anchors (a term, a number, the label of what is being pointed at), at most two short lines, never the voice line written out.
- What the viewer has learned stays on screen and changes rather than being replaced: the dot becomes a node, the label becomes an axis ([motion-design.md](motion-design.md) §3).
- Every number on screen or in the voice has a source or a calculation in `<project>/SOURCES.md`; a number without one is cut.

**Not good**
- A tour of everything true about the topic. Jargon before the picture that would make it obvious. A new name for the same thing halfway through.
- A model shown all at once and then described. A metaphor that is cute but wrong in the part that matters.

## Picture

**Good**
- One visual idea carries the video: a device that recurs and changes as the story moves. A red caret that is a man's voice and a red slab that is the wall in front of it. A grey world where one colour survives and floods back. A roll of film with 35 of 36 frames shot. A row of street lamps. Scenes are moments in the life of the device, not slides about the topic.
- The device comes from this story, so you can say why: because the story has X, the picture is Y. Its nouns become objects, its verbs become motion, its numbers become something you can see. It reads without a label, and screenshots of the video would lose something important: the meaning is in how it moves.
- Every frame would work as a poster: scale contrast (one thing huge, the rest small), deliberate empty space, supporting shapes and texture cropped by the edge, asymmetry, a clear grid, one place the eye goes first.
- Type is image: one word filling the frame, weight contrast, tracking and line breaks chosen for the word that matters. The hierarchy is unmistakable: the hero is around twice the size of the next level, and labels are clearly smaller again. When two typefaces meet, the contrast between them means something (a voice and a record, then and now).
- Shots vary the way an editor varies them: wide, close and extreme close; dense and empty. When two scenes share a layout, it is on purpose (a match cut, a before and after).
- The palette is small, so colour can carry meaning: the accent marks the one thing that matters, and a shift of the whole palette marks a shift in the story. Colour moves with the acts, like a score: one colour event per act lands harder than colour everywhere.
- Light and contrast let the subject read at a glance, even in a dark, moody piece. Surfaces look made: one light direction for the whole film, a base with texture and one edge or highlight, value contrast between planes. The biggest moment can get a light of its own behind the subject.
- Each shot is drawn by the engine its content asks for: three.js where form, material or depth is what the shot shows (a product turning, chrome catching a glint, layers separating, a globe), Canvas for what is read, charted or flat, and an isometric machine on Canvas when the explanation is a mechanism the viewer watches work ([iso-figures.md](iso-figures.md)). They read as one film: one palette, one light, one grain ([three-d.md](three-d.md), *Canvas or three.js*).

**Not good**
- A centred title over a centred subtitle on every frame.
- The subject too small or too dark to read in the first second.
- The subject or a word the viewer has to read cut off by the frame: a hero word with letters off the edge, a face or object sliced at the frame line, a label half outside. On a phone it reads as a mistake, not as boldness. Crops are for what supports the subject (a background numeral, a texture, a road running out of shot), never for the thing the frame is about.
- The look models reach for by default, unless the brief truly asks for it: a cream ground with a high-contrast serif and a terracotta or red accent; near-black with one acid accent; a broadsheet of hairline rules; tracked ALL-CAPS eyebrows, mono data labels and middle-dot meta strings; scene counters and chrome (NO. 01, 00 —, 03 / 04, INTRODUCING); purple-blue gradients, neon on dark, glass cards, floating blobs, icons in circles, emoji, stock-looking illustration. Name the default you are reaching for and ask what this story would choose instead.
- A frame that would pass unchanged as a corporate slide. A metaphor that only works because of its label.
- Full-frame dark gradients that band after encoding; a long crossfade between a light and a dark scene that passes through grey.
- A preset's example video with the words swapped.
- 3D because it can be: a spinning logo, a turntable as the only motion, the 3D defaults (dark navy space, a halo ring, bloom, particles). Or the opposite: a product that should be turned in the light, drawn flat.
- Labels on everything, and on-screen text that repeats what the voice or the captions already say. The picture tells it; text on screen is either a hero (one word, huge) or quiet, and the composition leaves room for whichever it is.

### The look has a name

A model draws a look it can name far better than one assembled from adjectives. "上海美影《山水情》", "a 1930s Shanghai calendar poster", "Saul Bass's *Anatomy of a Murder* titles", "a two-drum riso zine", "a PC-98 adventure game" each bring palette, line, texture, composition and a way of moving all at once.

**Good**
- The reference fits the content: its own feeling matches what this story is about, so the brief can say in one sentence why this reference and not another. A story about patience takes a reference that is patient; a story about rigour and proof takes one where rigour is the drama. The look carries the meaning instead of fighting it.
- The brief names one or two specific references the look stands on (a work, a studio, a designer's period, a print or craft medium, an era of games or animation) and says what this video takes from them (palette, type, texture, camera, how text enters and leaves) and what this story changes.
- A frame from the video could sit beside a frame from the reference and look like it belongs to the same family, while the subject, the device and the story are this brief's own.
- When the user gives a reference (a frame, a clip, a link, a folder of their own work), it outranks every preset: the palette is sampled from it, and its shot lengths, transitions, type and the way text arrives and leaves carry over.

**Not good**
- A reference chosen for a surface word in the request and not for the story: "cool and dynamic" answered with racing and speed lines for a tool whose point is going deep and proving it works. The frames look exciting and say the opposite of the voice.
- A look described only in adjectives (clean, modern, premium, techy), which lands on the default every time.
- A reference so famous that it is the default ("Apple keynote", "Kurzgesagt"), named without saying what this story changes.
- Taking the reference's content, characters or logos instead of its grammar; carrying over only its colours.

Places to look, well beyond the presets: title design (Saul Bass, Kyle Cooper, Elastic), motion studios (Buck, ManvsMachine, Oddfellows, Ordinary Folk, Giant Ant), editorial motion (Vox, The New York Times, The Pudding), poster design (Josef Müller-Brockmann, 1930s Shanghai posters, Polish film posters), animation traditions (上海美影, UPA, Ghibli backgrounds, Cartoon Saloon, Spider-Verse), print and craft media (risograph, linocut, cyanotype, cut paper, stop-motion clay, chalk on a blackboard), game eras (NES, Super Famicom, PC-98, PS1 low-poly), and Chinese visual traditions (留白 in ink painting, 书法, 年画, 剪纸).

## Motion

**Good**
- Every move has a job (it points, explains a change, gives a hold life) and the screen is never dead.
- Every cut carries something across: a shape, a colour, a direction, a word. The best transitions are set up inside the shot before them (a push into a jar becomes its inside; a thrown page becomes a boat), and the middle of a transition is itself a designed frame. Across a seam, direction and speed match, and the next shot enters already moving the way the last one left.
- Cuts are the quiet base. The few narrative transitions are spent where the story turns, each used once.
- Moves have weight: anticipation, a snap or a long settle, follow-through, arcs. Related elements arrive as one cascade.
- Speed has contrast: a quick hit then a long drift, a burst of cuts then a held shot.
- Holds stay alive with a travelling camera, moving light, parallax between layers, and not all in the same way. The one moment everything stops dead, a breath before the big hit, can be the strongest in the film.
- The camera changes shot size for real (wide, then close) rather than drifting 2% on every shot.
- Things that belong together still move as individuals: one side leads by a few frames, timings differ a little. Key poses read as good stills before they move.
- Cuts happen on action; secondary elements leave before the cut.
- A few signature moves that belong to this video, usually the device transforming, are what people remember.
- Hits land on their words and beats.

**Not good**
- Everything fading in together; text that sits on a still frame; scenes shoved off by the next one.
- Motion added because a frame felt empty: wobbling text, particles, pulsing rings and ripples, heartbeats, everything pulsing to the beat.
- Bounce on numbers or data; a different transition at every cut.
- The same slow push on every scene. Zooming in, then straight back out. Two shots in a row that end the same way.
- Twins: parts moving identically because they share the same numbers.
- The answer on screen before the voice has reasoned towards it; a list shown all at once before it is read out.

The language and the vocabulary are in [motion-design.md](motion-design.md).

## Sound

**Good**
- The score is one piece of music composed for this video, as if a music supervisor had licensed it: a reference you can name, a theme you could hum after one hearing (a short motif stated, answered, varied and brought home changed), and a form with an opening, a lift, a climax and an ending that resolves.
- It underscores the voice: accompaniment that moves under the narration, the theme where the voice rests. It meets the picture only where the story turns (three to five moments a minute: the world changing, the turn, the last image) and otherwise follows its own phrases.
- It is played, not looped: each part with its own feel and dynamics, figures that vary, harmony with colour, space, registers kept apart, drums only where the story moves.
- The voice is clear and unhurried. There is silence where a line needs to land.
- Sound effects are few: things on screen that would feel false in silence, in the same room as the music. Many videos need none to four.

**Not good**
- The music answering every action (an instrument hit on every jump and button press, the band stopping before each): it sounds forced.
- A pattern looped bar after bar, the same four chords from start to end, a tune fighting the voice, a drum kit by default.
- A drone (pads or strings alone for long stretches), a low tom as the only pulse, slow minor chords drowned in reverb, a melody that never resolves. These read as cheap or creepy.
- Wall-to-wall narration; a sound on every element; synthesized beeps and sine ticks.
- Instruments chosen by subject cliché (a guzheng because the topic is China) rather than by feeling.

How to write it is in [music-and-sound.md](music-and-sound.md).

## How you know

Intent is not evidence: judge what was rendered. The contact sheets show composition and readability; a strip of close probes shows whether a move has weight; a half-scale draft shows the cuts; frames pulled from the final MP4 show what the viewer gets; `gaga music` shows the arc and the mix, and its `listen:` line measures what ears would catch (a ghostly stretch, a buried melody, a flat score, effects lost or jumping out). You cannot hear the audio, so say what you intended and ask the user to listen to the 8 seconds around the key mood change.

Look at them as a harsh director, not a proud author. For each of the opening two seconds, the picture (would frames work as posters, does the look hold up beside its reference), motion, variety (does something new land every few seconds), readability on a phone (`gaga still --phone` shows probes at 390 px wide: every word is legible and the subject of each frame is shown whole; its `text:` line points at text that is small or low in contrast there) and sound sync, give a score out of 10 and name the three weakest moments with their timestamps. A video is ready when every score is 8 or more; a 6 means that part is rebuilt, not polished.

Then take it in the two ways people often do:
- **Muted.** Most feeds start silent. With the sound off, the frames and captions still carry the story in the right order: read the contact sheet with `--subs` and the voice switched off in your head.
- **Audio only.** Read `narration.json` on its own: no line leans on the picture to make sense ("this one", "as you can see"), and the order of ideas holds.

For an explainer, read the brief's *adds* column against the frames: each scene adds the one thing it promised, and the viewer can say it afterwards. A scene that adds nothing is cut.

Have a subagent review it cold: give it the contact sheet, the brief's line and audience, and nothing else, and ask who this is for, what it is communicating, what the viewer can now say, and which frame they would stop on. Where its answers differ from the brief, the video is what changes. When you fix something, keep the frame before and after (`gaga still --at <t>` both times) and show the pair in the delivery.

Deliver when it meets this page. If something still falls short, rebuild that part rather than patch it, or say plainly what it is.

## The brief

`<project>/BRIEF.md` records the target for this video, short and specific:

```markdown
# {Title}
- The line: "{the sentence someone would repeat}"
- Angle: {the chosen telling} (also considered: {…}; {…})
- Audience and format: {who} · {1920×1080 | 1080×1920 | …} · {N} s
- Explains (when it does): "{the question, in the viewer's words}" · believed now: {…} · can say after: {…} · cut list: {…} · sources in SOURCES.md
- The device: {the visual idea, why it comes from this story, and how it changes across the video}
- Look: stands on {named references} · takes {…} · this story changes {…} · palette {hex…} and its colour events · light {direction} · type {display + label, sizes hero / secondary / label}
- Motion: {its character in a sentence} · signature moves {…}
- 3D (when a shot uses three.js): model {real units, proportions that don't change} · environment {polyhaven:<hdri id> | gl.studio: why} · surfaces {each hero surface: polyhaven:<id> | generated "<prompt>" | matcap "<prompt>" | flat on purpose: why} · materials {per surface, in numbers} · light {key, fill, rim: colour, strength, where} · camera {lens, azimuth/elevation/distance, its one move} · springs {damping ratio per move} · banned {the 3D defaults, by name}
- Voice: {voice id, rate} · captions {burn | file | none}
- Score: {feel in three words} · {reference} · {bpm} BPM {key} {mode} · {the theme} · {the form, bar by bar in sections} · {the 3–5 moments it meets the picture} · {the few sound effects}
- Calls made: {each decision taken without asking, one line each, so the user can overturn it}

| # | scene | adds (what the viewer can now say) | voice line (or — music only) | picture | engine · why (`2D`, `2D·iso`, `3D`, `3D+2D`) | motion & sync | transition | music · sfx | ≈ s |
|---|---|---|---|---|---|---|---|---|---|
```
