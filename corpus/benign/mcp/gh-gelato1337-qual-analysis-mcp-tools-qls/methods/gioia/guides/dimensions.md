# Building aggregate dimensions

Aggregate dimensions distil the themes into a few higher-order answers to the research question.
This is where the study's lens (`intent()`: prior research, sensitizing concepts) does most of its
work: it tells you what kind of answer the question is asking for.

## What makes a dimension

- **It answers the question.** `answers` says how, in one or two sentences that would make sense in
  the paper's findings section. A dimension that only sorts themes into bins does not answer
  anything.
- **It is built from themes,** each with a reason. A theme belongs to one dimension only.
- **It is at the level the question asks.** Read the question for the kind of answer it wants (a
  process, a consequence, a condition, a type) and make each dimension that kind of thing.
- **Few.** If you have many, some of them are probably themes.

## Negative cases

For each dimension, look for evidence against it: informants who say the opposite, conditions under
which it does not hold, concepts that pull the other way, interviews where it is absent. Use
`search`, `query` and `read_source`; do not rely on the concepts alone, they were coded before the
dimension existed.

Write a `negative-case` memo about each dimension, even when you found nothing: say where you looked.
A dimension with real counter-evidence is not wrong; it has a boundary, and the memo states it.

## The grounded model

The data structure is static. The last step is to say how the dimensions relate: what drives what,
what holds what back, how it unfolds over time. Write this as a `corpus` memo citing the dimensions'
memos. It is the bridge from the data structure to the paper's argument.

## Before you checkpoint

- Every theme is in a dimension (`check()`), and every dimension has its negative-case memo.
- Write a `batch` memo on the dimensions: the strongest alternative reading of the same themes, and
  why you chose this one.
