# Stage 6: every language

Starts only when the source-language frames, header, video and listing are approved. From here on a change to the
source costs one round in every language.

## 1. Ask which languages

Ask the owner which languages the store page should speak. Give them what they need to decide:

- the languages the app itself speaks (from stage 1). A store page in a language the app does not speak is allowed,
  but the screens on the frames would then show an app the person will not get; recommend the app's own languages
  first and say so if they choose more;
- that Spanish and Portuguese are two store languages each (Spain and Latin America, Portugal and Brazil), and Chinese
  is two scripts;
- that right-to-left languages are mirrored and that this is handled;
- the cost: a translator and an auditor per language, a render of everything per language, one more column in App
  Store Connect, and a manual upload per language at the end.

Write the list into `languages` in `store/store.config.json`, source first, and into `store/PROGRESS.md`.

## 2. A translator and a separate auditor, per language

Every language is written by one agent and read by another. Never the same agent, never you: an auditor that did not
write the text finds what its author cannot see. Use the strongest model you can for both.

For each language, in this order:

1. **Translator**: a fresh agent with `SKILL_DIR/reference/translator-brief.md` as its brief and an assignment (below). It
   writes the language's four text files and `store/translations/<code>/notes.md`.
2. **Auditor**: another fresh agent with `SKILL_DIR/reference/auditor-brief.md` and the same assignment. It reads, corrects
   the files itself where something is plainly wrong, and writes `store/translations/<code>/audit.md`.

The translators of different languages are independent: start them together, a handful at a time, and start each
language's auditor when its translator has reported. The briefs name no paths of this machine: the assignment does.

The assignment you add to each brief:

```
Language: <name> (<code>), as written in <countries>.
Register: <informal "you" / formal / the app's own choice in this language, if the app already speaks it>.
Source language: <code>. Product: <the stage 1 summary: the one sentence, for whom, what it is not, tone rules>.
The app speaks this language: <yes: its texts are in store/app-texts/<code>.json | no>.
The project's site speaks this language: <where its texts are | no>.
Files: store/frames/texts/<code>.json, store/header/texts/<code>.json, store/video/texts/<code>.json,
       store/listing/<code>.json, store/translations/<code>/.
Tools: <SKILL_DIR>/tools/texts.py and listing.py, run from the project's root.
Briefs: <SKILL_DIR>/reference/translator-brief.md and auditor-brief.md.
```

Do not paste the source texts into the assignment: the agent reads the files.

## 3. Your part: the engineer's

When a language's audit is in:

1. `python3 SKILL_DIR/tools/texts.py <code>` and `python3 SKILL_DIR/tools/listing.py <code>`: no problem left.
2. Render: frames, the contact sheet, the header, the video's stills. Read every warning; **open every picture**.
3. What does not fit:
   - a claim line, a header line or a scene line too wide: first break the same words elsewhere. If no break fits,
     the words have to change, and that is the language's editor's decision, not yours: send the auditor (or a new
     one) the measured widths and the limit and have them shorten it, then render again;
   - a header slogan that is long takes a third line; the letters keep their size;
   - a card in the video that needs more height: the renderer grows all of that language's cards; look at whether the
     picture still holds;
   - a label of the app that wraps or is cut on a screen: it is the app's text and stays. If it ruins the frame, say
     so to the owner; the fix is in the app or in the choice of screen.
4. Right to left: put what the kit places with `left` and `right` into `store/rtl.css` and look at every mirrored
   picture: the shape in the other corner, bars and rows from the right, arrows turned.
5. Read each `audit.md`: what the auditor left as a matter of taste, and what it says "needs the engineer". Fix what
   is yours; collect what is the owner's.
6. Render the video itself only when the stills are right.

## 4. Report

One table for the owner: language, what the auditor corrected (a line each for the ones worth knowing: a word with a
second meaning, a keyword swapped because it belongs to another category in that country), what did not fit and what
was done, what is left for them to decide. Then the contact sheets. Say plainly that every text was written and read
by models and by no native speaker, and that the pictures have not been seen in the store's preview.

When the owner accepts a language's pictures, copy them from `store/out/<code>/` to `store/approved/<code>/`
(further sets of screenshots with their folders, `<code>/<set>/`), as was done for the source language: that copy is what later renders are compared with and what is uploaded. Write
`store/LISTING.md` again (`python3 SKILL_DIR/tools/listing.py`) and update `store/PROGRESS.md`.

## Later changes

A changed or new store text gets every language in the same change: the source by you with the owner, the others by
that language's translator and a separate auditor, then the renders. Never translate a line yourself "just this once".
