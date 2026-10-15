# Marginalia Reader

**A reading companion for [Claude Code](https://claude.com/claude-code) that helps you remember what you read.**

Send it the pages you read today, whether that's a photo, a scan, or just "I read chapters 5–7." It asks you a few good questions, responds to your answers like a well-read friend, and keeps a plain-text journal of everything. Over the following days and weeks, the important parts come back to you for review, so books stop evaporating.

```
you › /marginalia  did today's Harvard Classics, Jan 25 (Burns)  [photo of the page]

      Logged. Two quick ones:
      1. Without looking back: what happens in the poem? Two or three sentences.
      2. By the last stanza, who's worse off, the mouse or the man? Why?

you › 1. guy is plowing in november and wrecks a mouse's nest. feels bad,
         apologizes for humans being jerks to animals. then the best laid plans thing
      2. the man?? idk the mouse literally lost its house tho

      1. Yep. And you caught the bigger apology: he's sorry that "man's dominion"
         has broken "nature's social union." The best-laid-plans stanza is where
         it widens from one mouse to everybody.
      2. Your instinct was right: the man. The last stanza says the mouse only
         has to deal with the present ("the present only toucheth thee"), while
         he looks back with regret and forward with fear.

      Logged. Lens for next time (Herodotus on Egypt): after Burns's mouse,
      notice how the Egyptians treat their animals. Happy to dig into either one.
```

## Why it works

Most of us read for input and keep very little. The fix is well established. **Retrieval practice** (trying to recall what you read, in your own words) and **spacing** (coming back to it over days and weeks) are among the most effective learning techniques known. Rereading and highlighting feel productive but do little. Marginalia Reader builds both into a ten-minute habit:

- **Bookends.** Recall last time before you start, and recall what you just read before you stop.
- **Good questions.** They're built on Mortimer Adler's four questions from *How to Read a Book* (What is it about? What is being said, and how? Is it true? What of it?), adapted to novels, essays, nonfiction, poetry, plays, craft books, and daily reading plans.
- **Spaced review.** One "keeper" question per session comes back after 1, 3, 7, 21, and 60 days, then retires.

## Built for real life, ADHD brains included

- No streaks, and no "you missed 5 days." Every session counts, even "just log it."
- Starting is the hard part, so there's a one-minute warm-up, and every session ends with a "lens": one thing to notice next time you open the book.
- On a low-energy day, a five-minute review counts as a reading day.
- There's no rigid schedule, just a loose lineup tied to parts of your day instead of clock times.
- Your reading is logged before any questions, so drifting off mid-session loses nothing.
- Answer in fragments, dictate, or skip. A normal session takes about ten minutes.

## Features

- Works from photos, scans, PDFs, or pasted text, or from no pages at all.
- **No spoilers.** It only talks about what you've already read, and that includes famous books.
- A running *Previously on…* recap and cast list for each book (a lifesaver for Russian novels).
- Questions tuned to the kind of book: plot and character for novels, argument for nonfiction, image and form for poetry, and short exercises for books about writing.
- Reading plans, with the complete Harvard Classics *Fifteen Minutes a Day* guide included: all 366 days.
- **Own the books as PDFs?** Tell it where they are once, and it reads each day's assigned pages straight from your copy, so plan days need no photos. It finds the right pages even when the PDF's numbering differs from the printed book's. (macOS; the full Harvard Classics set is free on the Internet Archive.)
- A commonplace book for lines worth keeping, plus weekly and monthly reflections.
- Scanning from iPhone to Mac with Continuity Camera.

## Install

You need [Claude Code](https://claude.com/claude-code) (desktop app, terminal, or IDE extension) and Python 3.9 or later. On a Mac, Python comes with the Xcode command line tools (`xcode-select --install`). It's tested on macOS and should work on Linux. Windows is untested.

```bash
git clone https://github.com/gambinoisamaster/marginalia-reader ~/.claude/skills/marginalia
```

Then type `/marginalia` in Claude Code. The first time, it creates your journal in `~/Documents/Marginalia` and asks what you're reading.

To update later:

```bash
git -C ~/.claude/skills/marginalia pull
```

**Optional: no permission prompts.** The skill pre-approves the journal folder and its helper script during the turn you invoke it. To make that permanent, so logging your answers never asks either, add these rules to `~/.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Read(~/Documents/Marginalia/**)",
      "Edit(~/Documents/Marginalia/**)",
      "Read(~/.claude/skills/marginalia/**)",
      "Bash(python3 ~/.claude/skills/marginalia/scripts/journal.py *)"
    ]
  }
}
```

## Things you can say

| Say | What happens |
|---|---|
| `/marginalia` plus pages, or "I read ch. 5–7" | A session: three questions, a response, and it's logged |
| "warm me up for *Middlemarch*" | Before reading: where you left off, a quick recall, something to watch for |
| "rerun" | Review only, for days with no new reading |
| "light" / "deep" | One question, or a longer conversation |
| "weekly" / "monthly" | A recap, review questions, and next week's lineup / what went well and what got in the way |
| "long session" | A free afternoon, in chunks with breaks |
| "start the Harvard Classics plan" | Fifteen minutes a day of the great books |
| "finished *Middlemarch*" | A capstone: what was it about, and what of it? |
| "where am I?" | Your shelf at a glance |

## Your journal is yours

Everything lives in plain Markdown files in `~/Documents/Marginalia` (or wherever `MARGINALIA_HOME` points), in a folder you own. You can read it in any text editor, or open the folder in [Obsidian](https://obsidian.md) for a notebook view. Back it up like any other folder, or make it a private git repository.

It doesn't depend on Claude to stay readable. The helper script runs on its own, and this prints your due review questions with their answer keys:

```bash
python3 ~/.claude/skills/marginalia/scripts/journal.py due
```

**Privacy.** The journal never leaves your computer on its own. During a session, the pages you share and your answers are sent to Claude, like any other conversation.

**Copyright.** Share pages from books you own, for your own study. The journal keeps your answers and short summaries, and at most a line or two you chose to save, never the book's text.

## How it's built

| | |
|---|---|
| `SKILL.md` | The instructions Claude follows |
| `references/` | Question craft by kind of book, journal formats, weekly and monthly rituals |
| `scripts/journal.py` | Creates the journal, runs the spaced-review queue and the photo inbox, and pulls pages out of your PDFs (Python standard library only) |
| `scripts/pdftool.swift` | A tiny macOS PDF helper, built automatically the first time it's needed |
| `templates/journal/` | A new reader's starting journal |
| `plans/` | Reading plans |
| `tests/` | Run with `python3 -m unittest discover -s tests` |

## Contributing

Contributions are welcome, especially:
- corrections to the Harvard Classics plan (`plans/harvard-classics.md`) from anyone with the volumes at hand
- other public-domain reading plans
- question lenses for kinds of books not covered yet
- bug reports from real reading sessions

Open an issue or a pull request.

## Credits

- Mortimer J. Adler and Charles Van Doren, *How to Read a Book*
- *Fifteen Minutes a Day: The Reading Guide* to the Harvard Classics (P. F. Collier & Son; public domain)
- The research on retrieval practice and spacing, summarized well in Dunlosky et al., "Improving Students' Learning With Effective Learning Techniques," *Psychological Science in the Public Interest* (2013)

## License

[MIT](LICENSE)
