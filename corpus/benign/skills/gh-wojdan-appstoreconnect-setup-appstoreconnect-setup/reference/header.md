# Stage 3: the product page header

The wide picture at the top of the app's page in the store (21:9; `specs.md`). The store shows the app's icon and name
right under it, so the header carries neither: it carries the slogan, in the kit's type, on the kit's strongest
background, with at most one shape of the kit. No logo, no screenshot, no card.

## 1. The slogan

Propose two or three, each in two lines, and say which you would pick. Where to look: the claim of the project's site,
the first frame's claim, the sentence from stage 1 that a stranger would repeat. A good header slogan names the
person's problem in their own words and turns it; a pattern that works is a quiet first line and a full second one
("the thing people believe," / "and what it really is."), which the two tones of a line are for.

## 2. The design

Everything from the kit: the background is one of its tones (the darkest or the brand's), the shape is one the kit
already uses on its cards or frames, the face is the kit's display face. Ask for it on a **new** page in Claude Design
(`claude-design.md`), as a 1920 × 823 CSS px stage, or write it directly, since it is three rules of CSS:

- `store/header/template.html`: an element with `id="stage"`, inside it the slogan in an element with `id="title"`
  holding `{{lines}}`, and the shape. Give a shape the attribute `data-keep-clear` (or `data-keep-clear="circle"` for
  a circle) and the renderer measures how close the slogan comes to it.
- `store/header/header.css`: the stage's background, the shape, the title's face and size, and one class per tone of a
  line (`.h-line--quiet`, `.h-line--full`), all from the kit's variables.
- `store/header/texts/<source>.json`: `{"lines": [{"text": "…", "tone": "quiet"}, {"text": "…", "tone": "full"}]}`.

`node SKILL_DIR/tools/render-header.mjs <source>` writes `store/out/<source>/header.png` at 3840 × 1646 and prints where the
slogan lies.

## 3. What the store does to it

Measured in the preview of App Store Connect on an iPhone in October 2026 (Apple publishes no safe area in pixels, only
the advice to keep the focal point in the centre, so measure again when it matters):

- the full height is shown and about the middle 84% of the width (`header.visible` in the configuration, in CSS px of
  the 1920 px canvas; the renderer warns when the slogan leaves it);
- above the picture the store continues its top edge, blurred, under the status bar;
- the back and share buttons lie over the top corners, so nothing that has to be read goes there.

Letters as large as the visible width allows read best at the size a phone shows. A longer slogan takes a third line;
it does not get smaller letters, or the languages stop looking like one set.

## 4. Approval

Show the picture, with the visible part marked or cropped next to it. On the owner's yes: record it, copy the file to
`store/approved/<source>/`, and say that the real test is the preview in App Store Connect after the upload (stage 8),
which nobody has seen yet.
