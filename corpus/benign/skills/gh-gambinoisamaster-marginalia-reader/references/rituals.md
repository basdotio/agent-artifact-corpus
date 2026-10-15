# Rituals

These are bigger occasions than a single session. Each one should feel like a pleasure, not an audit.

## Weekly ("weekly", or Sunday evening)

This adapts a classic study routine, Sunday-evening planning plus an end-of-day review: plan loosely, review cumulatively.
1. Gather the week. Find the sessions dated in the last seven days across `books/*.md` (grep `^### 20`), and run `journal.py stats`.
2. Tell them what they did: books touched, sessions, reruns, and one good line from their answers. Report only what they did, never a tally of what they didn't.
3. **Cumulative rerun:** three questions spanning the whole week, across books. (The classic end-of-day "review everything" study block, stretched to a week.)
4. **One cross-book question** linking two things they read this week. This is Adler's "syntopical" reading, and it's usually the most interesting question of the week.
5. **Lineup:** show the Lineup from `shelf.md` and ask if anything should change, like a book to push or one to pause. Anchors are parts of the day, not clock times, unless they ask for times.
6. Append to `reflections.md`.

## Monthly ("monthly")

Celebrate, name what got in the way, and reward yourself.
1. Pull numbers from the logs and `journal.py stats`: sessions, reruns, books moved forward or finished, and questions retired ("yours now").
2. **Celebrate:** quote back their three best answers or insights of the month.
3. **What got in the way?** Ask one question, with no guilt. Then suggest one small tweak to try, such as a different anchor, a lighter default, or warm-ups on Mondays.
4. **A reward** they'd actually enjoy.
5. **Next month's focus:** one or two books, maybe a writing goal.
6. Append to `reflections.md`.

## Long session ("long session", a free afternoon)

A classic study-chunk structure (review, learn, review, break), made gentler:
- A chunk is a two-minute warm-up recall, then 25–45 minutes of reading (their call; shorter is fine), then a couple of questions, then a real break away from screens.
- Each new chunk opens with one recall question from the chunk before.
- After two or three chunks, suggest a bigger break: food, a walk.
- Finish with a ten-minute rerun of the whole day: three questions spanning every chunk.
- You can't keep time. They'll message you between chunks.

## Finishing a book

The capstone comes from Adler:
1. "What is the book about as a whole?" A paragraph, in their words.
2. "What of it?" What it changed, and what they'll keep.

Log both answers. Mark the book `finished <date>` on the shelf, add their paragraph to `commonplace.md` under the book's title, and celebrate properly. Finishing a long book is a real event.
