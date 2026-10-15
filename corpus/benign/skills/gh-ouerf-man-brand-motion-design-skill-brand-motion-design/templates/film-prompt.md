<context>
<Product> <does what, for whom, in one or two sentences>.
This film plays <where, from the interview>. It must read <with the sound off, if it plays muted>.
Read `videos/BRAND.md` first. It holds the brief, the look, the brand element, the components, the product owner's rulings and what we may claim. This prompt only adds the story.
</context>

<inputs>
Type: <launch | feature spotlight | promo | teaser | social proof | event | before/after | product showcase> (reference/video-types.md).
Facts from the owner, word for word: <price, offer, dates, place, review and source>.
Assets used: <files in assets/, and what each becomes>. Missing, replaced by: <...>.
Decided: <width>x<height>, 60 fps, <dark|light>, <N> bars at <BPM> BPM, <seconds> s. Music: <title, artist, license | generated with synth.py: key, progression, energy | silent>, in `assets/audio/`. Edit (licensed track): song bars <a-b>, <c-d> (`edit.json`).
</inputs>

<direction>
<The feel in 3 short lines, in the product's own voice.>
The message, in three statements: <1.> <2.> <3.>
Showreel defaults (reference/showreel.md): a lit 3D showpiece per chapter, a camera cut every 2 beats, giant slammed words over wide shots only, a colour flip per chapter, the HUD with chapter labels, particles or the highlight converging into the logo at the end.
Only the brand's own colours, type and logo; light, depth and motion are the showreel's.
Banned: <from BRAND.md, plus: anything the product's language does not use, words the product avoids, false claims>.
</direction>

<cast>
- The brand element: <the logo, a wordmark, a mascot the product has, or none>, and where it appears.
- Cursors: <the user's OS arrow, the product's own cursor, or none>.
- Demo world, from the landing page: <names, data, placeholders like (your product)>.
</cast>

<structure>
<BPM>, 4/4, <N> bars. One beat is <s> s. Something happens on every beat.

Per chapter: the 3D showpiece, its shots (wide for words, close for detail), the words (1 to 3, slammed), the sticker, the transition out, the sound.
Bars 1 and 2, cold open + hook. <something already moving in frame 1; two giant words on bar 2>.
Bars 3 and 4, the problem as a picture. <the user's material in 3D, the flaw gets the highlight>.
Bars 5 and 6, the drop. <the generative showpiece built from the subject; bloom, one shake>.
Bars 7 and 8, the fix. <the same material corrected; a check lands; colour flip>.
Bars 9 and 10, the payoff. <the outcome as a feeling; stickers from the brand pack>.
Bars 11 and 12 (+ hold), the lockup. <converge into the logo; the official build; tagline>.
</structure>

<build>
1. HyperFrames project in `videos/<film>/` (`scripts/setup.mjs`), set up as BRAND.md "Workspace" says. Kit in `kit/`, runtimes vendored in `vendor/`.
2. Every style is a pure function of t: `setup()` builds and measures once, `draw(t)` sets styles. Anything on its own clock gets a frame-driven twin.
3. `cues.js` is the beat sheet as data; scene code never holds a literal time. `scripts/beat-sheet.mjs` writes the table.
4. Springs are closed form; values that retarget sum one spring per key (`PF.track`).
5. Transitions as chosen; magic moves use `PF.move` + `PF.travel`, measured in `setup()` and checked with `scripts/stills.mjs --debug`.
6. Music: `scripts/synth.py music` (or `beats.py` + `audio-edit.py` for a licensed track); effects with `synth.py sfx` and `scripts/place-audio.mjs`.
7. Gate: `npx hyperframes check`. Final: `scripts/render.mjs` (240 fps master, motion blur), then `scripts/verify.py` (duration, colors, tags, loudness, probes). Report file sizes.
</build>

<gotchas>
No closing script tag in any script or comment. Shown means visibility: inherit. Measure after fonts. Never put will-change on anything the camera scales. Text never travels across text. Keep a slot for every word before it lands. A texture under words stays thin there; behind UI it stays calm. If the film loops, the last frame equals frame 0. Draw dashes as SVG strokes. Judge the encoded file, and decode its pixels.
<Product claims: what needs a human approval step on screen, what the product never does.>
</gotchas>

<start>
Read `videos/BRAND.md`. Before any scene code, show the beat sheet on the measured grid and three style frames: the opening, one feature scene, the strongest moment. Wait for OK.
</start>
