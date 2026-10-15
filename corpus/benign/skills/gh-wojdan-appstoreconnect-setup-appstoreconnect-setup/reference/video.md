# Stage 4: the search-results video

A short looping video shown in the store's search results (3:2; `specs.md`). The store plays it muted and nobody can
unmute it there, so the texts on screen carry everything; a soundtrack is only heard where the same video is used with
sound.

## 1. The scenario, in words

The owner can describe the video the way one tells a storyboard: scene by scene, what is on screen, what it says, how
one scene becomes the next. You build exactly that and render it. If they have no idea yet, propose this one, which is
the scenario the renderer ships with, filled with the product's own words:

| Scene | Text on one side (two or three short lines) | Card on the other side |
|---|---|---|
| 1 | how a session starts: "Start with ⟨the first small step⟩." | ⟨the first thing the app shows or asks⟩ |
| 2 | what the app does: "⟨App⟩ ⟨does its part⟩." | ⟨what it proposes, with its main button⟩ |
| 3 | what the person does: "You ⟨do yours⟩." | ⟨the same thing, in progress or being answered⟩ |
| 4 | where it ends: "⟨And that is all⟩." | ⟨the done state⟩ |

Then scene 1 comes back, so the last frame equals the first and the loop has no seam. Four scenes of 3.75 s fill
15 s. Each scene has its own background tone from the kit; the card flips in from the side, the next background fades
in over the current one, the text fades out and in with a slight scale.

Show the scenario as a table like the one above, with the real texts, and wait for the owner's answer. Things they
may want, and where each lives:

| They say | You change |
|---|---|
| other texts, another number of scenes, another order, other backgrounds | `store/video/scenario.json` (`scenes`: a tone and a card each) and `store/video/texts/<source>.json` |
| slower, faster, a longer pause, a quicker change | `sceneSeconds`, `transitionSeconds`, `fps` in `scenario.json` |
| something else than a card: a phone screen, the icon, a list filling up | another template in `store/video/cards/` (a "card" is any HTML from the kit) and its size in `scenario.json` (`card`, `cardZoom`, `cardsWidth`) |
| the text bigger, on the other side, in the middle | `store/video/video.css` (it is loaded after the renderer's own rules and overrides them) and `block`, `blockZoom`, `textWidth` |
| another kind of motion: slide instead of flip, the text typed out, the card growing, a zoom into a button | a copy of `SKILL_DIR/tools/motion-default.js` as `store/video/motion.js`, rewritten; its first lines say what it is given and what it must do |

For a motion you write yourself: everything is a function of the time alone (`window.renderAt(t)`), no timers and no
CSS animations, because frames are captured one by one; and the stage must be back at the first picture one frame
before the end, or the loop shows a seam (the renderer compares the last frame with the first and warns).
Describe back to the owner in one sentence per scene what will move, before you build it.

## 2. Build it

- `store/video/cards/<name>.html`: each card as kit markup on one line, with a `{{field}}` for every text. Take the
  cards from the screens of the frames where you can: the same component, the same texts.
- `store/video/texts/<source>.json`: `{"scenes": [["line", "line"], …], "cards": {"<name>": {"field": "text"}}}`.
  Scene texts are broken into lines by hand; a line has to fit the text column (the renderer warns), which is about
  twelve Latin characters at the default size.
- `store/video/video.css`: one class per background tone (`.v-tone--<name>`: `--scene-bg`, `--scene-shape`,
  `--scene-ink`), the shape, the face of the scene text. **All from the kit's variables**; the tones are the kit's own.
- Rule 3 of the skill holds for the cards: every word on a card is the app's own text (`python3 SKILL_DIR/tools/texts.py`).

`node SKILL_DIR/tools/render-video.mjs <source> stills` writes the middle of each scene as a PNG in seconds: iterate on
these. Show them to the owner as a sample; when the scenes are right, render the video
(`node SKILL_DIR/tools/render-video.mjs <source>`, half a minute to a few minutes) and send it.

The cards have one height. A language whose tallest card needs more gets all of its cards that much taller, still
centred; the renderer says by how much.

## 3. Sound

Optional: put a track at `store/video/bgm.wav` and the renderer lays it under the video, cut at the video's length
(`gainDb` in `scenario.json` raises or lowers it). The loop sounds right only if the track loops at that length too.

**Recommend music under CC0** (public domain dedication): no attribution to carry, no licence that can be withdrawn
from a published app page, no doubt about commercial use. Where to look:

- [FreePD](https://freepd.com): everything on it is CC0;
- [Freesound](https://freesound.org): set the licence filter to "Creative Commons 0" (loops and beds more than songs);
- [OpenGameArt](https://opengameart.org): music section, licence filter "CC0";
- [Free Music Archive](https://freemusicarchive.org): filter by licence, "CC0" or "Public Domain";
- [Pixabay Music](https://pixabay.com/music/): free for commercial use without attribution under Pixabay's own
  licence, which is not CC0; read it if that matters.

Whatever the source: the owner chooses and downloads the track themselves, reads the licence on the track's own page
that day, and you write the track's name, author, address and licence into `store/video/bgm.txt` next to the file.
Never take a track from a video or a streaming service.

## 4. Size and codec

Scale 1 is the scenario's size (1920 × 1280, H.264); `node SKILL_DIR/tools/render-video.mjs <source> 2` doubles it
(3840 × 2560, HEVC, because that size is beyond what H.264 decodes smoothly on Apple hardware). If App Store Connect
refuses the large file, upload the 1920 × 1280 one. After a render on a Mac,
`ffmpeg -hwaccel videotoolbox -i <file> -map 0:v -f null -` has to report every frame and no error.

## 5. Approval

The owner watches the video, twice round the loop. On their yes: record it, copy the file to
`store/approved/<source>/`, and note that where the store crops or covers the video is only known from the preview in
App Store Connect (stage 8).
