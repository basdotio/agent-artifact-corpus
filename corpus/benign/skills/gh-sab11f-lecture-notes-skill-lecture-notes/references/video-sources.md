# Video sources — mathematics only, one channel

Video boxes exist for one reason: students of Slovenian mathematics courses overwhelmingly learn from **Andrej P. Škraba** (`youtube.com/@andrej-p-skraba`, 2 500+ free videos). So the rule is narrow on purpose:

- The lecture is a **mathematics** course (any level — logic, analysis, linear algebra, statistics, discrete maths count; physics, CS, economics do not, even when they use maths) → look up his videos per section and add a `::: video` box where there is a match.
- Any other subject → **no video boxes at all**. Don't substitute another channel and don't ask the student for one.

Only videos that cover **that section's** concepts; a section with no match gets no box (don't pad with loosely related ones). Printed notes need typeable links: `youtu.be/<id>`, never the full watch URL. The build makes them clickable in the PDF.

```
::: video
- Implikacija — `youtu.be/UdvXiGRerZ4` (5:32)
- Vrstni red računanja – naloga 1 — `youtu.be/gVnzSwpuJCc` (8:31)
:::
```

## How to find them

The catalog is **astra.si**, organised by topic: `https://astra.si/<topic>/` with topics `logika-in-mnozice`, `naravna-in-cela-stevila`, `deljenje`, `racionalna-stevila`, `realna-stevila`, `potence-in-koreni`, `logaritmi`, `kompleksna-stevila`, `funkcije`, `polinomi`, `zaporedja`, `limite`, `odvod`, `integral`, `trigonometrija`, `stoznice`, `geometrija-v-ravnini`, `geometrija-v-prostoru`, `algebra`, `aritmetika`.

1. Fetch the topic page(s) that match the lecture (WebFetch; ask for an exhaustive list of title, duration, URL grouped by subsection). YouTube's own channel page is JS-rendered and youtube.com is usually blocked from the sandbox — don't try it, and don't try yt-dlp.
2. Pick the titles that match each section of the notes. Concept videos ("Kaj je …", "Pravila za …") first, then his numbered exercise videos ("… naloga 1–8") as a range.
3. Fetch each chosen page and read the embed ID (`youtube.com/embed/<id>`). Batch 10–15 fetches per turn.
4. Put the mapping section → videos in the chat before building, so the student sees it.

Coverage note: astra.si follows the gimnazija curriculum. University-only topics (complete induction, inf/sup, modus ponens, divisibility proofs, ε-δ) are not there — the section simply gets no box.

## Depth follows familiarity

Ask once, before writing: *"Which of these sections are new to you?"* (show the planned section list). For sections the student marks as new: more `idea` boxes, a second worked example, 1–2 extra tasks beyond the slides' own. For sections they know: slides' content and exercises only, no extras. This keeps the workbook from growing where it is not needed.
