# Journal formats

The journal belongs to the reader. Someday it will be the record of everything they read and what they thought about it, so keep it plain, consistent Markdown that's pleasant to scroll.

## profile.md

The reader, in their own words: what they read for, how they like sessions, and anything to keep in mind. They write it; you read it every session. Edit it only when they ask, or when you're filling it in together with them.

## shelf.md

A **Lineup** section on top, then one section per book:

    ## Anna Karenina — Leo Tolstoy
    - **File:** books/anna-karenina.md
    - **Type:** novel
    - **Edition:** Pevear & Volokhonsky (Penguin)
    - **Status:** reading
    - **Read through:** Part 2, ch. 7
    - **Last session:** 2026-10-03
    - **Lens for next time:** <one specific, spoiler-free thing to notice>

- `?` means unknown. Fill it in from the first pages they send or what they mention. Ask only for a translation's edition.
- **Read through** is the spoiler line: the last chapter (or page) they've finished. For a stop mid-chapter, write `Part 2, ch. 7 (to p. 142, mid-chapter)`. Record an approximate position as given (`about halfway (exact chapter ?)`) and treat it conservatively until the first session pins it down. For essay collections, it names the latest essay (`I:8 "Of idleness"`). The book file's *argument so far* lists every essay read, and that list, not the numbering, is what counts as known.
- Status is `reading`, `paused`, or `finished 2026-11-20`.
- A reading plan's entry has **Next entry:** (e.g. `Jan 6`) instead of **Read through:**. Its lens comes from the next entry's hook in the plan.
- When the first book is added, remove the "No books yet" placeholder line.

## books/<slug>.md

    # <Title> — <Author>

    ## About this book
    - **Type:** …
    - **Edition:** …
    - **Lenses that fit:** …
    - **Shelf connections:** …
    - **Watch-outs:** …

    ## Previously on…
    <A synopsis of everything read so far, ~250 words at most. Rewrite it each
    session instead of appending, and compress older material. For non-fiction
    the heading is "The argument so far". It's built only from what they've read,
    so it's spoiler-safe.>

    ## People so far
    - **Name** (other names they go by) — who they are, as of where the reader is
    <Non-fiction uses "## Key ideas so far": term or idea, one line each.>

    ## Sessions

    ### 2026-10-03 · Part 2, ch. 1–7 (pp. 120–142)
    **In brief:** <3–5 sentences in your own words>

    1. **Q:** <question>
       **A:** <their answer, verbatim; *(open)* until they answer>
       → <one line: what you said back>
    2. …
    3. …

    **Also:** <optional: anything else they said worth keeping, verbatim>

    **Margin note:** <optional: the one note you added, in a line>

    **Rerun:** #14 (montaigne-essays) — got · "<their answer, verbatim>"  ·  or  ·  none due

    **Lens for next time:** <same as on the shelf>

- Sessions go at the bottom, oldest first. Keep the blank lines between the bold lines so they don't run together.
- Without photos, the header says so: `### 2026-10-03 · Part 1, ch. 1–12 (no photos)`.
- The stub written before the questions go out holds **In brief**, the questions with answers marked *(open)*, `**Rerun:** #14 offered` if one was asked, and the provisional lens. Questions they never answer stay *(open)*, with no → line. A stub that's never answered stands as a complete session.
- The People and Ideas lists describe things as of where the reader is. Avoid "so far only mentioned," "not yet seen," and similar wording that implies more is coming.

For long files, read from the top through `## Sessions`, then only the last two or three sessions.

## Reading plans

A plan has two files:
- `plans/<slug>.md`: the sequence itself, one block per entry, grouped by month (or week, or part):

      ### Jan 6 · Warned by Hector's Ghost
      Virgil, *Aeneid* — Vol. 13, pp. 109–127
      Hook: <the teaser, in your own words>
      Note: <the guide's anniversary note, if any>

- `books/<slug>.md`: the log. If the reader owns the texts as PDFs, its *About* section names them, so plan days need no photos:

      - **Your copies:** `~/Ebooks/Harvard Classics/` · Vol. N is `NNN_Harvard_Classics.pdf` (e.g. `038_…` for Vol. 38)

  Like a book file, except it keeps **Readings so far** in place of *Previously on…* and *People so far*, one line per entry, followed by the session log:

      - **Jan 25** · Burns, "To a Mouse" · read 2026-10-03 — <their takeaway, in their words where possible>

## .pages/

Temporary page extracts from `journal.py pages`, replaced on every run. `offsets.json` remembers each PDF's page offset. Safe to delete.

## commonplace.md

    ### <Book> — <where>
    > <the line, kept short>

    <their note on why, if they gave one> — 2026-10-03

Finished books get a section holding their capstone paragraph.

## writing.md

    ### 2026-10-03 · <exercise name> (after <book>, ch. 3)
    <the prompt, one line>

    <their writing, verbatim>

## reflections.md

    ## Week of 2026-10-05
    - **Read:** <books and spans, from the logs>
    - **Sessions:** 6 · **Reruns:** 9
    - **Best moment:** <a line from one of their answers>
    - **Cross-book question:** <Q> — <their answer>
    - **Next week's lineup:** <changes, or "same">

    ## October 2026
    - **Celebrate:** …
    - **What got in the way:** … → **One tweak:** …
    - **Reward:** …
    - **Next month:** …
